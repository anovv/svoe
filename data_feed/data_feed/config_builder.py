import yaml
from pathlib import Path
from typing import Any
from cryptofeed.symbols import gen_symbols
from cryptofeed.defines import BINANCE, COINBASE, KRAKEN, HUOBI, DERIBIT, BITMEX

MEDIUM = 'kafka' # 'redis' or 'kafka'

CONFIG_PATH = str(Path(__file__).parent / 'configs/cryptostore_config.yaml')
AWS_CREDENTIALS_PATH = str(Path(__file__).parent / 'configs/aws_credentials.yaml')

class ConfigBuilder(object):

    def __init__(self, exchange_list: list[str]):
        self.exchange_list = exchange_list
        self.supported_exchanges_with_pairs = {
            # pair_gen, max_depth_l2, max_num_of_pairs, include_ticker
            BINANCE : [self._get_binance_pairs, 100, 1, True], #max_depth 5000 # https://github.com/bmoscon/cryptostore/issues/156 set limit to num pairs to avoid rate limit?
            COINBASE: [self._get_coinbase_pairs, 100, 1, True],
            KRAKEN: [self._get_kraken_pairs, 100, 1, True], #max_depth 1000
            HUOBI: [self._get_huobi_pairs, 100, 1, False],
            # 'BITMEX' : BITMEX,
            # 'DERIBIT' : DERIBIT
        }

    def build_cryptostore_config(self) -> str:
        aws_credentials = self._read_aws_credentials()
        data = dict(
            cache=MEDIUM,
            # https://stackoverflow.com/questions/52996028/accessing-local-kafka-from-within-services-deployed-in-local-docker-for-mac-inc
            kafka=dict(
                # ip='host.docker.internal', # for Docker on Mac use host.docker.internal:19092
                # port=19092,
                ip='127.0.0.1',
                port=9092,
                start_flush=True,
            ),
            redis=dict(
                ip='127.0.0.1',
                port=6379,
                socket=None,
                del_after_read=True,
                retention_time=None,
                start_flush=True,
            ),
            storage=['parquet'],
            storage_retries=5,
            storage_retry_wait=30,
            parquet=dict(
                del_file=True,
                append_counter=0,
                file_format=['exchange', 'symbol', 'data_type', 'timestamp'],
                compression=dict(
                    codec='BROTLI',
                    level=6,
                ),
                prefix_date=True,
                S3=dict(
                    key_id=aws_credentials[0],
                    secret=aws_credentials[1],
                    bucket=aws_credentials[2],
                    prefix='parquet'
                ),
                # path=TEMP_FILES_PATH,
            ),
            storage_interval=90,
            exchanges=self._get_exchanges_config()
        )

        with open(CONFIG_PATH, 'w+') as outfile:
            yaml.dump(data, outfile, default_flow_style=False)

        return CONFIG_PATH

    def _get_exchanges_config(self) -> dict[str, Any]:
        config = dict()
        for exchange in self.exchange_list:
            if exchange not in self.supported_exchanges_with_pairs:
                raise Exception('Exchange {} is not supported'.format(exchange))

            # pairs
            pairs = self.supported_exchanges_with_pairs[exchange][0]()
            max_num_of_pairs = self.supported_exchanges_with_pairs[exchange][2]
            if 0 < max_num_of_pairs < len(pairs):
                pairs = pairs[:max_num_of_pairs]

            # book
            l2_book = dict(
                symbols=pairs,
                book_delta=True,
            )
            max_depth = self.supported_exchanges_with_pairs[exchange][1]
            if max_depth > 0:
                l2_book['max_depth'] = max_depth

            config[exchange] = dict(
                retries=-1,
                l2_book=l2_book,
                trades=pairs,
            )

            include_ticker = self.supported_exchanges_with_pairs[exchange][3]

            if include_ticker:
                config[exchange]['ticker'] = pairs

        return config

    @staticmethod
    def _get_kraken_pairs() -> list[str]:
        symbols = gen_symbols(KRAKEN)

        # USD quote only
        return list(filter(lambda item: item.split('-')[1] == 'USD', list(symbols.keys())))

    @staticmethod
    def _get_coinbase_pairs() -> list[str]:
        symbols = gen_symbols(COINBASE)

        # USD quote only
        return list(filter(lambda item: item.split('-')[1] == 'USD', list(symbols.keys())))

        # from ccxt
        # c = coinbase()
        # markets = c.fetch_markets()
        # usd_only = list(filter(lambda item: item['symbol'].split('/')[1] == 'USD', markets))
        # usd_only_symbols = list(map(lambda item: item['symbol'], usd_only))

        # return usd_only_symbols

    @staticmethod
    def _get_binance_pairs() -> list[str]:
        symbols = gen_symbols(BINANCE)

        # USD quote only
        return list(filter(lambda item: item.split('-')[1] == 'USDT', list(symbols.keys())))

    @staticmethod
    def _get_huobi_pairs() -> list[str]:
        symbols = gen_symbols(HUOBI)

        # USD quote only
        return list(filter(lambda item: item.split('-')[1] == 'USDT', list(symbols.keys())))

    @staticmethod
    def get_deribit_pairs():
        symbols = gen_symbols(DERIBIT)
        print(symbols)


    @staticmethod
    def get_bitmex_pairs():
        symbols = gen_symbols(BITMEX)
        print(symbols)

    @staticmethod
    def _read_aws_credentials() -> list[str]:
        with open(AWS_CREDENTIALS_PATH) as file:
            data = yaml.load(file, Loader=yaml.FullLoader)

        return [data['key_id'], data['secret'], data['bucket']]
