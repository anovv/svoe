from cryptofeed.defines import TICKER, TRADES, L2_BOOK, L3_BOOK, LIQUIDATIONS, OPEN_INTEREST, FUNDING, FUTURES, FX, OPTION, PERPETUAL, SPOT, CALL, PUT, CURRENCY
from cryptofeed.symbols import Symbols, Symbol
from cryptofeed.exchanges import EXCHANGE_MAP
from jinja2 import Template
import yaml

MASTER_CONFIG = yaml.safe_load(open('master-config.yaml', 'r'))

def gen_helm_values():
    feed_configs = []
    for exchange in MASTER_CONFIG['exchangeConfigSets']:
        for exchange_config in MASTER_CONFIG['exchangeConfigSets'][exchange]:
            feed_configs.extend(build_feed_configs(exchange, exchange_config))

    return Template(open('feed-configs-template.yaml', 'r').read()).render(feed_configs=feed_configs)

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
                print(f'Skipping {base} in exclude...')
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
        pod_configs = []
        for pod_id in symbol_pod_mapping:
            pod_configs.append((pod_id, _build_cryptostore_config(exchange, exchange_config, symbol_pod_mapping[pod_id], channels)))

        feed_configs.append({
            'exchange': exchange,
            'instrument_type': instrument_type,
            'quote': quote,
            'base_tuples': base_tuples,
            'data_feed_image': exchange_config['dataFeedImage'],
            'pod_configs': pod_configs
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
    config['exchanges'] = {}
    config['exchanges'][exchange] = channels_config

    for k in exchangeConfigOverrides:
        config['exchanges'][exchange][k] = exchangeConfigOverrides[k]

    # TODO set prometheus.multiProcDir per config

    return yaml.dump(config, default_flow_style=False)

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
    else:
        raise ValueError('Unsupported pod distribution strategy')

    return dist

def _readSymbolSet(exchange_config, field):
    # bases and quotes can be either explicit list of symbols or a reference to symbolSet
    if isinstance(exchange_config[field], list):
        return exchange_config[field]
    else:
        return MASTER_CONFIG['symbolSets'][exchange_config[field]]

print(gen_helm_values())