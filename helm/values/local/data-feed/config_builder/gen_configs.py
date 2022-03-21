from cryptofeed.defines import TICKER, TRADES, L2_BOOK, L3_BOOK, LIQUIDATIONS, OPEN_INTEREST, FUNDING, FUTURES, FX, \
    OPTION, PERPETUAL, SPOT, CALL, PUT, CURRENCY
from cryptofeed.symbols import Symbols, Symbol
from cryptofeed.exchanges import EXCHANGE_MAP
from jinja2 import Template
import yaml
import json
from hashlib import sha1

MASTER_CONFIG = yaml.safe_load(open('master-config.yaml', 'r'))


# TODO az distribution + az changes to config/hash
# TODO validate no duplicate configurations
def gen_helm_values():
    feed_configs = []
    for exchange in MASTER_CONFIG['exchangeConfigSets']:
        for exchange_config in MASTER_CONFIG['exchangeConfigSets'][exchange]:
            feed_configs.extend(build_feed_configs(exchange, exchange_config))

    cluster_feed_configs_mapping = {}
    for feed_config in feed_configs:
        cluster_id = feed_config['cluster_id']
        if cluster_id in cluster_feed_configs_mapping:
            cluster_feed_configs_mapping[cluster_id].append(feed_config)
        else:
            cluster_feed_configs_mapping[cluster_id] = [feed_config]

    values = Template(open('feed-configs-template.yaml', 'r').read()).render(
        cluster_feed_configs_mapping=cluster_feed_configs_mapping
    )
    with open('../values.yaml.gotmpl', 'w+') as outfile:
        outfile.write(values)


def build_feed_configs(exchange, exchange_config):
    feed_configs = []
    instrument_type = exchange_config['instrumentType']
    symbol_distribution_strategy = exchange_config['symbolPodDistributionStrategy']

    bases = _readSymbolSet(exchange_config, 'bases')
    quotes = _readSymbolSet(exchange_config, 'quotes')
    exclude_bases = _readSymbolSet(exchange_config, 'excludeBases')

    # validate channels
    channels = exchange_config['channels']
    for channel in channels:
        # this will throw if channel does not exist
        EXCHANGE_MAP[exchange].std_channel_to_exchange(channel)

    for quote in quotes:
        symbols_for_quote = []
        base_tuples = []
        for base in bases:
            if base in exclude_bases:
                # TODO make excludes per quote
                print(f'Skipping {base} for {exchange} {instrument_type} in exclude...')
                continue
            # TODO handle options/futures
            symbol = Symbol(base, quote, instrument_type)
            # validate symbol exists
            exchange_symbols = EXCHANGE_MAP[exchange].symbols()
            if symbol.normalized not in exchange_symbols:
                raise ValueError(f'Symbol {symbol.normalized} does not exist in exchange {exchange}')
            symbols_for_quote.append(symbol.normalized)
            base_tuples.append((symbol.normalized, base))

        symbol_pod_mapping = _distributeSymbols(exchange, symbols_for_quote, symbol_distribution_strategy)
        pod_configs_raw = []
        for pod_id in symbol_pod_mapping:
            pod_configs_raw.append(
                (pod_id, _build_cryptostore_config(exchange, exchange_config, symbol_pod_mapping[pod_id], channels)))

        pod_configs = []
        # hashify pod configs:
        for p in pod_configs_raw:
            # TODO figure out which fields of config are hash-sensitive
            hash_pod_config = _hash(p[1])
            p[1]['svoe']['version'] = hash_pod_config
            p[1]['prometheus']['multiproc_dir'] = p[1]['prometheus']['multiproc_dir_prefix'] + '_' + _hash_short(hash_pod_config)
            p[1]['svoe']['data_feed_image'] = exchange_config['dataFeedImage']
            p[1]['svoe']['cluster_id'] = exchange_config['clusterId']
            pod_configs.append((p[0], yaml.dump(p[1], default_flow_style=False)))

        feed_configs.append({
            'exchange': exchange,
            'instrument_type': instrument_type,
            'quote': quote,
            'base_tuples': base_tuples,
            'data_feed_image': exchange_config['dataFeedImage'],
            'pod_configs': pod_configs,
            'cluster_id': exchange_config['clusterId']
        })

    return feed_configs


def _build_cryptostore_config(exchange, exchange_config, symbols, channels):
    config = yaml.safe_load(open('cryptostore-config-template.yaml', 'r'))

    cryptostoreConfigOverrides = exchange_config['cryptostoreConfigOverrides']
    exchangeConfigOverrides = exchange_config['exchangeConfigOverrides']
    channelsConfigOverrides = exchange_config['channelsConfigOverrides']

    for k in cryptostoreConfigOverrides:
        config[k] = cryptostoreConfigOverrides[k]

    channels_config = _build_cryptostore_channels_config(symbols, channels, channelsConfigOverrides)
    if 'exchanges' not in config:
        config['exchanges'] = {}
    config['exchanges'][exchange] = channels_config

    for k in exchangeConfigOverrides:
        config['exchanges'][exchange][k] = exchangeConfigOverrides[k]

    return config


def _build_cryptostore_channels_config(symbols, channels, overrides):
    # TODO validate result against template (make one) for testing purposes?
    config = {}
    for channel in channels:
        # special case
        if channel in [L2_BOOK, L3_BOOK]:
            config[channel] = {}
            config[channel]['symbols'] = symbols
        else:
            config[channel] = symbols

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
        raise ValueError('Unsupported pod distribution strategy')
    else:
        raise ValueError('Unsupported pod distribution strategy')

    return dist


def _readSymbolSet(exchange_config, field):
    # bases and quotes can be either explicit list of symbols or a reference to symbolSet
    if isinstance(exchange_config[field], list):
        return exchange_config[field]
    else:
        return MASTER_CONFIG['symbolSets'][exchange_config[field]]


def _hash(config):
    return sha1(json.dumps(config, sort_keys=True).encode('utf8')).hexdigest()


def _hash_short(hash):
    return hash[:6]


gen_helm_values()
print('Done')
