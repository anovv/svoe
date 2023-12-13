import yaml
import json
import subprocess
import ccxt
import os
import numpy as np

from cryptofeed.defines import TICKER, TRADES, L2_BOOK, L3_BOOK, LIQUIDATIONS, OPEN_INTEREST, FUNDING, FUTURES, FX, \
    OPTION, PERPETUAL, SPOT, CALL, PUT, CURRENCY
from cryptofeed.symbols import Symbols, Symbol
from cryptofeed.exchanges import EXCHANGE_MAP
from jinja2 import Template
from hashlib import sha1
from functools import cmp_to_key

MASTER_CONFIG = yaml.safe_load(open('master-config.yaml', 'r'))
BUILD_INFO_LOOKUP = {}
RESOURCE_ESTIMATION_FOLDER = '../../../../../data_feed/perf/resources-estimation-out'
RESOURCE_INDEX_PATH = 'resource-index.json'

HEALTH_THRESHOLD_PER_CHANNEL = {
    TICKER: 0.5,
    L2_BOOK: 0.5,
    TRADES: 0.5,
    OPEN_INTEREST: 0,
    LIQUIDATIONS: 0,
    FUNDING: 0,
}
RESOURCE_INDEX = None
SUMMARY = {}

def gen_helm_values():
    pod_configs = []
    for exchange in MASTER_CONFIG['exchangeConfigSets']:
        for exchange_config in MASTER_CONFIG['exchangeConfigSets'][exchange]:
            pod_configs.extend(build_pod_configs(exchange, exchange_config))

    cluster_pod_configs_mapping = {}
    for pod_config in pod_configs:
        cluster_id = pod_config['cluster_id']
        if cluster_id in cluster_pod_configs_mapping:
            cluster_pod_configs_mapping[cluster_id].append(pod_config)
        else:
            cluster_pod_configs_mapping[cluster_id] = [pod_config]

    values = Template(open('pod-configs-template.yaml', 'r').read()).render(
        cluster_pod_configs_mapping=cluster_pod_configs_mapping
    )
    with open('../values.yaml.gotmpl', 'w+') as outfile:
        outfile.write(values)


def build_pod_configs(exchange, exchange_config):
    # TODO az distribution + az changes to config/hash
    # TODO handle instrument_extra (strike_price, option_type, expiry_date params)
    # TODO handle duplicates (Symbol equal method)
    # TODO add explicit symbol excludes

    launch_on_deploy = 'launchOnDeploy' in exchange_config and exchange_config['launchOnDeploy']
    instrument_type = exchange_config['instrumentType']
    symbol_distribution_strategy = exchange_config['symbolPodDistributionStrategy']

    bases = _read_symbol_set(exchange_config, 'bases')
    quotes = _read_symbol_set(exchange_config, 'quotes')
    explicit_symbols = exchange_config['symbols']

    exclude_bases = _read_excludes(exchange_config, 'bases')
    exclude_quotes = _read_excludes(exchange_config, 'quotes')

    symbols = []
    for explicit_symbol in explicit_symbols:
        symbols.append(Symbol(explicit_symbol['base'], explicit_symbol['quote'], instrument_type))
    for quote in quotes:
        for base in bases:
            symbols.append(Symbol(base, quote, instrument_type))

    # filter excludes
    for exclude_base in exclude_bases:
        for symbol in symbols:
            if symbol.base == exclude_base:
                symbols.remove(symbol)
                print(f'Skipping {symbol.normalized} for {exchange} {instrument_type} due to {exclude_base} exclude base...')

    for exclude_quote in exclude_quotes:
        for symbol in symbols:
            if symbol.quote == exclude_quote:
                symbols.remove(symbol)
                print(f'Skipping {symbol.normalized} for {exchange} {instrument_type} due to {exclude_quote} exclude quote...')

    # validate symbol exists
    has_non_existent_symbols = False
    exchange_symbols = EXCHANGE_MAP[exchange].symbols()
    for symbol in symbols:
        if symbol.normalized not in exchange_symbols:
            has_non_existent_symbols = True
            print(f'Symbol {symbol.normalized} does not exist in exchange {exchange}')

    if has_non_existent_symbols:
        raise ValueError(f'Exchange {exchange} has non existent symbols')

    # validate channels
    has_non_existent_channels = False
    channels = exchange_config['channels']
    for channel in channels:
        # this will throw if channel does not exist
        try:
            EXCHANGE_MAP[exchange].std_channel_to_exchange(channel)
        except:
            has_non_existent_channels = True
            print(f'Channel {channel} does not exist for {exchange}')

    if has_non_existent_channels:
        raise ValueError(f'Exchange {exchange} has non existent channels')

    symbol_pod_mapping = _distribute_symbols(exchange, symbols, symbol_distribution_strategy)
    data_feed_config_pod_mapping = []
    for pod_id in symbol_pod_mapping:
        data_feed_config_pod_mapping.append(
            (pod_id, _build_data_feed_config(exchange, exchange_config, symbol_pod_mapping[pod_id], channels))
        )

    pod_configs = []
    # hashify pod configs:
    for (pod_id, config) in data_feed_config_pod_mapping:
        # hash sensitive fields
        config['svoe']['instrument_type'] = instrument_type # TODO instrument_extra (strike/expiration/etc)
        config['svoe']['data_feed_image_version'] = exchange_config['dataFeedImageVersion']
        config['svoe']['cluster_id'] = exchange_config['clusterId']
        config['svoe']['symbol_distribution'] = symbol_distribution_strategy
        config['build_info'] = _get_build_info(exchange_config['dataFeedImageVersion'])

        hash_pod_config = _hash(config)
        hash_short = _hash_short(hash_pod_config)

        config['svoe']['version'] = hash_pod_config  # version is long
        config['svoe']['hash_short'] = hash_short
        config['prometheus']['multiproc_dir'] = config['prometheus']['multiproc_dir_prefix'] + '_' + hash_short

        name = ('data-feed-' + exchange + '-' + instrument_type + '-' + hash_short).lower() # TODO unique name, handle same hash pods
        name = name.replace('_', '-')

        # config maps to data_feed_config in pod_config

        labels = {
            'svoe.service': 'data-feed',
            'svoe.version': hash_pod_config,
            'svoe.hash-short': hash_short,
            'svoe.instrument-type': instrument_type, # TODO instrument_extra (strike/expiration/etc)
            'svoe.exchange': exchange,
            'svoe.name': name,
            'svoe.cluster-id': exchange_config['clusterId'],
            'svoe.data-feed-image-version': exchange_config['dataFeedImageVersion'],
            'svoe.payload-hash': config['payload_hash'],
            'svoe.symbol-distribution': symbol_distribution_strategy,
        }

        for s in symbol_pod_mapping[pod_id]:
            labels['svoe.base.' + s.base] = True
            labels['svoe.quote.' + s.quote] = True
            labels['svoe.symbol.' + s.normalized] = True

        for channel in channels:
            labels['svoe.channel.' + channel] = True

        # quote label strings
        for k in labels:
            if isinstance(labels[k], str):
                labels[k] = f'"{labels[k]}"'

        pod_config = {
            'name': name,
            'exchange': exchange,
            'instrument_type': instrument_type, # TODO instrument_extra (strike/expiration/etc)
            'symbols': list(map(
                lambda s:
                    {'base': s.base,
                     'quote': s.quote,
                     'symbol': s.normalized},
                symbol_pod_mapping[pod_id]
            )),
            'data_feed_image_version': exchange_config['dataFeedImageVersion'],
            # TODO remove duplication and read directly from config to helm
            'redis_port': config['redis']['port'],
            'prometheus_metrics_port': config['prometheus']['port'],
            'prometheus_multiproc_dir': config['prometheus']['multiproc_dir'],
            'data_feed_health_path': config['health_check']['path'],
            'data_feed_health_port': config['health_check']['port'],
            'data_feed_config': yaml.dump(config, default_flow_style=False),
            'cluster_id': exchange_config['clusterId'],
            'labels': labels,
            'launch_on_deploy': launch_on_deploy
        }

        RESOURCE_SPEC_SUMMARY_KEY = 'resource_spec_counter'
        if RESOURCE_SPEC_SUMMARY_KEY not in SUMMARY:
            SUMMARY[RESOURCE_SPEC_SUMMARY_KEY] = {}
        if exchange not in SUMMARY[RESOURCE_SPEC_SUMMARY_KEY]:
            SUMMARY[RESOURCE_SPEC_SUMMARY_KEY][exchange] = {}
        if instrument_type not in SUMMARY[RESOURCE_SPEC_SUMMARY_KEY][exchange]: # TODO instrument extra?
            SUMMARY[RESOURCE_SPEC_SUMMARY_KEY][exchange][instrument_type] = {}
        if symbol_distribution_strategy not in SUMMARY[RESOURCE_SPEC_SUMMARY_KEY][exchange][instrument_type]:
            SUMMARY[RESOURCE_SPEC_SUMMARY_KEY][exchange][instrument_type][symbol_distribution_strategy] = \
                {'skipped_payloads_count': 0,
                 # 'skipped_payloads': [],
                 # 'set_payloads': [],
                 'set_payloads_count': 0,
                 'total_count': len(symbol_pod_mapping)}

        # TODO set resources for sidecars (redis, redis-exporter)
        payload_hash = config['payload_hash']
        if payload_hash in RESOURCE_INDEX:
            resource_spec = RESOURCE_INDEX[payload_hash]['resource_spec']
            pod_config['data_feed_resources'] = {}
            if 'data-feed-container' in resource_spec:
                pod_config['data_feed_resources']['data-feed-container'] = resource_spec['data-feed-container']
            if 'redis' in resource_spec:
                pod_config['data_feed_resources']['redis'] = resource_spec['redis']
            if 'redis-exporter' in resource_spec:
                pod_config['data_feed_resources']['redis-exporter'] = resource_spec['redis-exporter']

            pod_config['labels']['svoe.has-resources'] = True
            SUMMARY[RESOURCE_SPEC_SUMMARY_KEY][exchange][instrument_type][symbol_distribution_strategy]['set_payloads_count'] += 1
            # SUMMARY[RESOURCE_SPEC_SUMMARY_KEY][exchange][instrument_type][symbol_distribution_strategy]['set_payloads'].append(
            #     {
            #         'payload_hash': payload_hash,
            #         'symbols': symbol_pod_mapping[pod_id],
            #     })
        else:
            pod_config['labels']['svoe.has-resources'] = False
            SUMMARY[RESOURCE_SPEC_SUMMARY_KEY][exchange][instrument_type][symbol_distribution_strategy]['skipped_payloads_count'] += 1
            # SUMMARY[RESOURCE_SPEC_SUMMARY_KEY][exchange][instrument_type][symbol_distribution_strategy]['skipped_payloads'].append(
            #     {
            #         'payload_hash': payload_hash,
            #         'symbols': symbol_pod_mapping[pod_id],
            #     })
        pod_configs.append(pod_config)

    # filter by requested number of pods
    if 'numPods' in exchange_config:
        num_pods = exchange_config['numPods']
        if num_pods > len(symbol_pod_mapping):
            raise ValueError(f'Number of requested pod {num_pods} is larger than expected {len(symbol_pod_mapping)} for {exchange} {instrument_type}')
        else:
            print(f'Generated {num_pods} pods for {exchange} {instrument_type}') # TODO print available symbols
        pod_configs = pod_configs[:num_pods]

    return pod_configs


def _build_data_feed_config(exchange, exchange_config, symbols, channels):
    config = yaml.safe_load(open('data-feed-config-template.yaml', 'r'))

    data_feed_config_overrides = exchange_config['dataFeedConfigOverrides']
    exchange_config_overrides = exchange_config['exchangeConfigOverrides']
    channels_config_overrides = exchange_config['channelsConfigOverrides']

    for k in data_feed_config_overrides:
        config[k] = data_feed_config_overrides[k]

    channels_config = _build_data_feed_channels_config(symbols, channels, channels_config_overrides)
    if 'exchanges' not in config:
        config['exchanges'] = {}
    config['exchanges'][exchange] = channels_config

    for k in exchange_config_overrides:
        config['exchanges'][exchange][k] = exchange_config_overrides[k]

    payload_config = _build_payload_config(exchange, symbols, channels)
    payload_hash = _hash_short(_hash(payload_config))
    config['payload_config'] = payload_config
    config['payload_hash'] = payload_hash

    return config


# TODO unify payload with channels_config/deprecate channels_config
def _build_payload_config(exchange, symbols, channels):
    # sort channels and symbols to keep hash consistent
    config = {exchange: {}}
    for channel in sorted(channels):
        config[exchange][channel] = sorted(list(map(lambda s: s.normalized, symbols)))
    return config


def _build_data_feed_channels_config(symbols, channels, overrides):
    # TODO validate result against template (make one) for testing purposes?
    config = {}
    for channel in channels:
        # special case
        if channel in [L2_BOOK, L3_BOOK]:
            config[channel] = {}
            config[channel]['symbols'] = list(map(lambda s: s.normalized, symbols))
        else:
            config[channel] = list(map(lambda s: s.normalized, symbols))

    # set channel overrides
    for channel in overrides:
        for k in overrides[channel]:
            config[channel][k] = overrides[channel][k]

    return config


def _distribute_symbols(exchange, symbols, strategy, reuse_index=True):
    dist = {}
    print(f'Using {strategy} symbol distribution strategy for {exchange}')

    if reuse_index:
        # tries to distribute symbols reusing already evaluated blocks to minimize hash inconsistency
        buckets = []
        while len(symbols) > 0:
            symbol = symbols[0]
            # find block with this symbol
            block_hash = None
            for payload_hash in RESOURCE_INDEX:
                if strategy in RESOURCE_INDEX[payload_hash]['symbol_distributions']:
                    _exchange = list(RESOURCE_INDEX[payload_hash]['payload_config'].keys())[0]
                    first_channel = list(RESOURCE_INDEX[payload_hash]['payload_config'][_exchange].keys())[0]
                    payload_symbols = RESOURCE_INDEX[payload_hash]['payload_config'][_exchange][first_channel]
                    if _exchange == exchange and symbol.normalized in payload_symbols:
                        block_hash = payload_hash
                        bucket = []
                        for s in payload_symbols:
                            to_remove = [i for i in range(len(symbols)) if symbols[i].normalized == s] # should be only one elem
                            for i in to_remove:
                                bucket.append(symbols[i])
                                del symbols[i]
                        buckets.append(bucket)
            if block_hash is None:
                break

        # append leftover symbols by splitting into buckets of 4
        bucket_size = 4
        leftovers = [symbols[i:i+bucket_size] for i in range(0, len(symbols), bucket_size)]
        buckets.extend(leftovers)
        for i in range(len(buckets)):
            dist[i] = buckets[i]

        print(f'{exchange} dist, reusing index: {dist}')
        return dist

    # TODO use consistent hashing
    # TODO _sort_by_binance_usdt_trading_vol changes order depending on outside factors, leads to rehashing and reevaluating
    # TODO all of it is most likely not needed or needed only for first init when index is not built
    if strategy == 'ONE_TO_ONE':
        # one symbol per pod
        sorted_symbols, _ = _sort_by_binance_usdt_trading_vol(symbols, reverse=True)
        for index, symbol in enumerate(sorted_symbols):
            dist[index] = [symbol]
    elif strategy == 'LARGEST_WITH_SMALLEST':
        # sorts symbols by trading volume and groups largest with smallest
        sorted_symbols, _ = _sort_by_binance_usdt_trading_vol(symbols, reverse=True)
        for i in range(len(sorted_symbols)):
            j = len(sorted_symbols) - i - 1
            if i < j:
                dist[i] = [sorted_symbols[i], sorted_symbols[j]]
            elif i == j:
                dist[i] = [sorted_symbols[i]]
            else:
                break
    elif strategy == 'EQUAL_BUCKETS':
        # greedily groups sorted by volume symbols into equal buckets of size no more than thresh
        sorted_symbols, volumes = _sort_by_binance_usdt_trading_vol(symbols, reverse=True)
        limit_per_bucket = 4
        # thresh = volumes[0] # max value
        a = np.array(volumes)
        thresh = np.mean(a) # use mean as threshold
        dist_sum_vols = {}
        index = 0
        i = 0
        while i < len(sorted_symbols):
            if index not in dist or (dist_sum_vols[index] < thresh and len(dist[index]) < limit_per_bucket):
                if index not in dist:
                    dist[index] = [sorted_symbols[i]]
                    dist_sum_vols[index] = volumes[i]
                else:
                    dist[index].append(sorted_symbols[i])
                    dist_sum_vols[index] += volumes[i]
                i += 1
            else:
                index += 1

        # print(dist_sum_vols)
    else:
        raise ValueError(f'Unsupported pod distribution strategy for {exchange}')

    print(f'{exchange} dist: {dist}')
    return dist


def _sort_by_binance_usdt_trading_vol(symbols, reverse=False):
    ccxt_symbols = list(map(lambda s: s.base + '/USDT', symbols))
    tickers = ccxt.binance().fetch_tickers(symbols=ccxt_symbols)

    # smallest to largest
    def compare(s1, s2):
        vol1 = int(float(tickers[s1.base + '/USDT']['info']['quoteVolume']))
        vol2 = int(float(tickers[s2.base + '/USDT']['info']['quoteVolume']))
        if vol1 < vol2:
            return -1
        elif vol1 > vol2:
            return 1
        else:
            return 0

    srtd = sorted(symbols, key=cmp_to_key(compare), reverse=reverse)
    volumes = list(map(lambda s: int(float(tickers[s.base + '/USDT']['info']['quoteVolume'])), srtd))

    return srtd, volumes


def _read_symbol_set(exchange_config, field):
    # bases and quotes can be either explicit list of symbols or a reference to symbolSet
    if isinstance(exchange_config['symbolSets'][field], list):
        return exchange_config['symbolSets'][field]
    else:
        return MASTER_CONFIG['symbolSets'][exchange_config['symbolSets'][field]]


def _read_excludes(exchange_config, field):
    # bases and quotes can be either explicit list of symbols or a reference to symbolSet
    if isinstance(exchange_config['excludes'][field], list):
        return exchange_config['excludes'][field]
    else:
        return MASTER_CONFIG['symbolSets'][exchange_config['excludes'][field]]


def _hash(config):
    return sha1(json.dumps(config, sort_keys=True).encode('utf8')).hexdigest()


def _hash_short(hash):
    return hash[:10]


def _build_resource_index(resource_estimation_dates):
    index = {}
    for date in resource_estimation_dates:
        file_path = RESOURCE_ESTIMATION_FOLDER + f'/{date}/resources-estimation.json'
        data = json.load(open(file_path))
        for key in data: # key should be pod name
            item = data[key]
            if 'metrics' not in item:
                continue
            payload_hash = item['payload_hash']
            payload_config = item['payload_config']
            symbol_distribution = item['symbol_distribution']
            unhealthy_channels = {}
            for channel in item['metrics']['df_health']:
                for symbol in item['metrics']['df_health'][channel]:
                    m = item['metrics']['df_health'][channel][symbol]
                    absent = m['absent'][0]
                    avg = m['avg'][0]
                    # mark unhealthy channels with reason
                    if avg is None:
                        unhealthy_channels[channel] = 'AVG_IS_NONE'
                    elif float(absent) > 0.5:
                        unhealthy_channels[channel] = f'ABSENT_THRESH({absent})'
                    elif float(avg) < HEALTH_THRESHOLD_PER_CHANNEL[channel]:
                        unhealthy_channels[channel] = f'AVG_THRESH({avg})'

            # in case of unhealthy channels we reuse healthy channels only to build resource spec
            if len(unhealthy_channels.keys()) != 0:
                exch = list(payload_config.keys())[0]
                for channel in unhealthy_channels:
                    del payload_config[exch][channel]
                # rehash
                payload_hash = _hash_short(_hash(payload_config))

            if payload_hash in index:
                if symbol_distribution not in index[payload_hash]['symbol_distributions']:
                    index[payload_hash]['symbol_distributions'].append(symbol_distribution)
                continue

            resource_spec = {}
            for type in ['metrics_server_cpu', 'metrics_server_mem']:
                for container in item['metrics'][type]:
                    for duration in ['run_duration', '600s']:
                        m = item['metrics'][type][container][duration]
                        absent = m['absent'][0]
                        if absent is None or float(absent) > 0.5:
                            continue
                        v_p95 = m['p95'][0]
                        v_avg = m['avg'][0]
                        if v_p95 is None or v_avg is None:
                            continue
                        if container not in resource_spec:
                            resource_spec[container] = {
                                'requests': {},
                                'limits': {}
                            }
                        REQUEST_UP = 0.1
                        LIMIT_UP = 0.5
                        if type == 'metrics_server_cpu':
                            # use avg for cpu because it spikes in the beginning
                            request = (float(v_avg) / (1000.0 * 1000.0)) * (1 + REQUEST_UP)
                            if 'cpu' in resource_spec[container]['requests']:
                                # already set
                                continue
                            # for cpu we set only requests
                            req_str = str(int(request)) + 'm'
                            resource_spec[container]['requests']['cpu'] = req_str
                        else:
                            request = (float(v_p95) / (1000.0)) * (1 + REQUEST_UP)
                            limit = request * (1 + LIMIT_UP)
                            if 'memory' in resource_spec[container]['requests']:
                                # already set
                                continue
                            req_str = str(int(request)) + 'Mi'
                            lim_str = str(int(limit)) + 'Mi'
                            resource_spec[container]['requests']['memory'] = req_str
                            resource_spec[container]['limits']['memory'] = lim_str

            index[payload_hash] = {
                'payload_config': payload_config,
                'resource_spec': resource_spec,
                'symbol_distributions': [symbol_distribution]
            }

            if len(unhealthy_channels.keys()) != 0:
                index[payload_hash]['skipped_channels'] = unhealthy_channels

        with open(RESOURCE_INDEX_PATH, 'w+') as outfile:
            json.dump(index, outfile, indent=4, sort_keys=True)

        return index


def _get_build_info(version):
    if version in BUILD_INFO_LOOKUP:
        return BUILD_INFO_LOOKUP[version]
    # TODO make sure it is synced with ../data_feed/ci/get_latest_labels.sh
    labels_output = subprocess.getoutput(f'cd ../../../../../data_feed/ci && ./get_latest_labels.sh {version}')
    labels = json.loads(str(labels_output))
    if not labels:
        raise Exception(f'No labels for Data Feed image version {version} to use for build_info')
    BUILD_INFO_LOOKUP[version] = labels
    return labels

RESOURCE_INDEX = _build_resource_index(['03-08-2022-17-05-14'])

gen_helm_values()

print('Summary\n' + str(SUMMARY['resource_spec_counter']))
print('Done.')
