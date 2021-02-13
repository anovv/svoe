import yaml
from cryptofeed.symbols import gen_symbols
from cryptofeed.defines import BINANCE, COINBASE, HUOBI, BITFINEX, KRAKEN

from ccxt.binance import binance
from ccxt.coinbase import coinbase
from ccxt.huobipro import huobipro
from ccxt.kraken import kraken
from ccxt.bitfinex import bitfinex

CONFIG_PATH = 'cryptostore_config.yaml'
AWS_CREDS_PATH = 'aws_creds.yaml'
PARQUETE_PATH = '/Users/anov/IdeaProjects/svoe/parquet'

def build_exchanges_config(exchange_list):
    supported_exchanges_with_pairs = {
        'BINANCE': [BINANCE, get_binance_pairs],
        'COINBASE' : [COINBASE, get_coinbase_pairs],
        # 'HUOBI' : HUOBI,
        # 'BITFINEX' : BITFINEX,
        # 'KRAKEN' : KRAKEN,
    }

    config = dict()
    for exchange in exchange_list:
        if exchange not in supported_exchanges_with_pairs:
            raise Exception('Exchange {} is not supported'.format(exchange))
        pairs = supported_exchanges_with_pairs[exchange][1]()
        config[supported_exchanges_with_pairs[exchange][0]] = dict(
            retries = -1,
            l2_book = dict(
                symbols = pairs,
            ),
            ticker = pairs,
            trades = pairs,
        )

    return config

def get_coinbase_pairs():
    c = coinbase()
    markets = c.fetch_markets()
    # USD quote only
    usd_only_map = list(filter(lambda item: item['quote'] == 'USD', markets))
    usd_only = list(map(lambda item: item['id'], usd_only_map))

    # find those supported by Cryptostore/Cryptofeed
    cryptostore_pairs_map = gen_symbols(COINBASE)
    cryptostore_pairs = list(cryptostore_pairs_map.values())
    intersect = set(usd_only) & set(cryptostore_pairs)

    # get Cryptostore keys for pairs
    return list(filter(lambda key: cryptostore_pairs_map[key] in intersect, list(cryptostore_pairs_map.keys())))

def get_binance_pairs():
    # TOP pairs by volume, only USDT quote
    b = binance()
    tickers = list(b.fetch_tickers().items())
    usdt_only = list(filter(lambda item: ((item[1]['symbol']).split('/'))[1] == 'USDT', tickers))

    # sort by USDT volume
    sorted(usdt_only, key=lambda item: item[1]['quoteVolume'])
    pairs = list(map(lambda item: item[1]['info']['symbol'], usdt_only))

    # find those supported by Cryptostore/Cryptofeed
    cryptostore_pairs_map = gen_symbols(BINANCE)
    cryptostore_pairs = list(cryptostore_pairs_map.values())
    intersect = set(pairs) & set(cryptostore_pairs)

    # get Cryptostore keys for pairs
    return list(filter(lambda key: cryptostore_pairs_map[key] in intersect, list(cryptostore_pairs_map.keys())))

def read_aws_creds():
    with open(AWS_CREDS_PATH) as file:
        data = yaml.load(file, Loader=yaml.FullLoader)

    return [data['key_id'], data['secret'], data['bucket']]

def build_cryptostore_config(exchange_list):
    aws_creds = read_aws_creds()
    data = dict(
        cache = 'kafka',
        kafka = dict(
            ip = '127.0.0.1',
            port = 9092,
            start_flush = True,
        ),
        storage = ['parquet'],
        storage_retries = 5,
        storage_retry_wait = 30,
        parquet = dict(
            del_file = True,
            append_counter = 0,
            file_format = ['exchange', 'symbol', 'data_type', 'timestamp'],
            compression = dict(
                codec = 'BROTLI',
                level = 6,
            ),
            prefix_date = True,
            S3 = dict(
                key_id = aws_creds[0],
                secret = aws_creds[1],
                bucket = aws_creds[2],
                prefix = 'parquet'
            ),
        ),
        storage_interval = 60,
        exchanges = build_exchanges_config(exchange_list)
    )

    with open(CONFIG_PATH, 'w+') as outfile:
        yaml.dump(data, outfile, default_flow_style=False)

    return CONFIG_PATH