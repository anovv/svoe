from cryptofeed.defines import TICKER, TRADES, L2_BOOK, L3_BOOK, LIQUIDATIONS, OPEN_INTEREST, FUNDING, FUTURES, FX, \
    OPTION, PERPETUAL, SPOT, CALL, PUT, CURRENCY
from cryptofeed.symbols import Symbols, Symbol
from cryptofeed.exchanges import EXCHANGE_MAP
from jinja2 import Template
import yaml
import json
from hashlib import sha1

MASTER_CONFIG = yaml.safe_load(open('master-config.yaml', 'r'))


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
    exchange_symbols = EXCHANGE_MAP[exchange].symbols()
    for symbol in symbols:
        if symbol.normalized not in exchange_symbols:
            raise ValueError(f'Symbol {symbol.normalized} does not exist in exchange {exchange}')

    # validate channels
    channels = exchange_config['channels']
    for channel in channels:
        # this will throw if channel does not exist
        EXCHANGE_MAP[exchange].std_channel_to_exchange(channel)

    symbol_pod_mapping = _distributeSymbols(exchange, symbols, symbol_distribution_strategy)
    data_feed_config_pod_mapping = []
    for pod_id in symbol_pod_mapping:
        data_feed_config_pod_mapping.append(
            (pod_id, _build_data_feed_config(exchange, exchange_config, symbol_pod_mapping[pod_id], channels))
        )

    pod_configs = []
    # hashify pod configs:
    for (pod_id, config) in data_feed_config_pod_mapping:
        # TODO figure out which fields of config are hash-sensitive
        hash_pod_config = _hash(config)
        hash_short = _hash_short(hash_pod_config)
        name = ('data-feed-' + exchange + '-' + instrument_type + '-' + hash_short).lower() # TODO unique name, handle same hash pods
        config['svoe']['instrument_type'] = instrument_type # TODO instrument_extra (strike/expiration/etc)
        config['svoe']['version'] = hash_pod_config # version is long
        config['svoe']['hash_short'] = hash_short
        config['prometheus']['multiproc_dir'] = config['prometheus']['multiproc_dir_prefix'] + '_' + hash_short
        config['svoe']['data_feed_image_version'] = exchange_config['dataFeedImageVersion']
        config['svoe']['cluster_id'] = exchange_config['clusterId']

        labels = {
            'svoe.service': 'data-feed',
            'svoe.version': hash_pod_config,
            'svoe.hash-short': hash_short,
            'svoe.instrument-type': instrument_type, # TODO instrument_extra (strike/expiration/etc)
            'svoe.exchange': exchange,
            'svoe.name': name,
            'svoe.cluster-id': exchange_config['clusterId'],
            'svoe.data-feed-image-version': exchange_config['dataFeedImageVersion']
        }

        for s in symbol_pod_mapping[pod_id]:
            labels['svoe.base.' + s.base] = True
            labels['svoe.quote.' + s.quote] = True
            labels['svoe.symbol.' + s.normalized] = True

        for channel in channels:
            labels['svoe.channel.' + channel] = True

        pod_configs.append({
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
            'data_feed_health_path': config['health_check']['path'],
            'data_feed_health_port': config['health_check']['port'],
            'data_feed_config': yaml.dump(config, default_flow_style=False),
            'data_feed_resources': _get_resources(exchange, instrument_type, symbols),
            'cluster_id': exchange_config['clusterId'],
            'labels': labels,
        })

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


def _distributeSymbols(exchange, symbols, strategy):
    dist = {}
    if strategy == 'ONE_TO_ONE':
        for index, symbol in enumerate(symbols):
            dist[index] = [symbol]
    elif strategy == 'ONE_THREE_FIVE':
        # TODO
        raise ValueError(f'Unsupported pod distribution strategy for {exchange}')
    else:
        raise ValueError(f'Unsupported pod distribution strategy for {exchange}')

    return dist


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


def _get_resources(exchange, instrument_type, symbols):
    # TODO pull Thanos data/make manual config
    # TODO set resources for redis/redis-exporter sidecars
    return {
        'requests': {
            'cpu': '25m',
            'memory': '200Mi'
        },
        'limits': {
            'cpu': '50m',
            'memory': '400Mi'
        }
    }

gen_helm_values()
print('Done.')
