import yaml
from cryptofeed.symbols import gen_symbols
from cryptofeed.defines import BINANCE

from ccxt.binance import binance

CONFIG_PATH = 'cryptostore_config.yaml'
AWS_CREDS_PATH = 'aws_creds.yaml'
PARQUETE_PATH = '/Users/anov/IdeaProjects/svoe/parquet'

def get_binance_pairs():
    # TOP pairs by volume, only USDT quote
    b = binance()
    items = list(b.fetch_tickers().items())
    res = list(filter(lambda item: ((item[1]['symbol']).split('/'))[1] == 'USDT', items))

    # sort by USDT volume
    sorted(res, key=lambda item: item[1]['quoteVolume'])
    pairs = list(map(lambda item: item[1]['info']['symbol'], res))

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

def build_cryptostore_config():
    aws_creds = read_aws_creds()
    binance_pairs = get_binance_pairs()[:10]
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
            # path = PARQUETE_PATH,
            S3 = dict(
                key_id = aws_creds[0],
                secret = aws_creds[1],
                bucket = aws_creds[2],
                prefix = 'parquet'
            ),
        ),
        storage_interval = 60,
        exchanges = dict(
            BINANCE = dict(
                retries = -1,
                l2_book = dict(
                    symbols = binance_pairs,
                ),
                ticker = binance_pairs,
                trades = binance_pairs,
            )
        )
    )

    with open(CONFIG_PATH, 'w+') as outfile:
        yaml.dump(data, outfile, default_flow_style=False)

    return CONFIG_PATH