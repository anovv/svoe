from configs.data_feed.base_config_builder import BaseConfigBuilder
from cryptofeed.defines import TICKER, TRADES, L2_BOOK, L3_BOOK, LIQUIDATIONS, OPEN_INTEREST, FUNDING

from pathlib import Path
import yaml

MEDIUM = 'redis'

# https://stackoverflow.com/questions/52996028/accessing-local-kafka-from-within-services-deployed-in-local-docker-for-mac-inc
KAFKA_IP = '127.0.0.1'# ip='host.docker.internal', # for Docker on Mac use host.docker.internal:19092
KAFKA_PORT = 9092 # port=19092

REDIS_IP = '127.0.0.1'
REDIS_PORT = 6379

START_FLUSH = True

# TODO figure out production paths
AWS_CREDENTIALS_PATH = str(Path(__file__).parent / 'aws_credentials.yaml')

# TODO this should be in sync with data feed service
DATA_FEED_CONFIG_DIR = '/etc/svoe/data_feed/configs'
DATA_FEED_CONFIG_FILE_NAME = 'data-feed-config.yaml'


# Cryptostore specific configs
class CryptostoreConfigBuilder(BaseConfigBuilder):

    # DEBUG ONLY
    def gen_DEBUG(self) -> str:
        config = self._cryptostore_config_FULL_DEBUG()
        return self._dump_yaml_config(config, DATA_FEED_CONFIG_DIR + '/' + DATA_FEED_CONFIG_FILE_NAME)

    def _cryptostore_template(self):
        aws_credentials = self._read_aws_credentials()
        return {
            'cache': MEDIUM,
            'kafka': {
                'ip': KAFKA_IP,
                'port': KAFKA_PORT,
                'start_flush': START_FLUSH,
            },
            'redis': {
                'ip': REDIS_IP,
                'port': REDIS_PORT,
                'socket': None,
                'del_after_read': True,
                'retention_time': None,
                'start_flush': START_FLUSH,
            },
            'storage': ['parquet'],
            'storage_retries': 5,
            'storage_retry_wait': 30,
            'parquet': {
                'del_file': True,
                'append_counter': 0,
                'file_format': ['exchange', 'symbol', 'data_type', 'timestamp'],
                'compression': {
                    'codec': 'gzip',
                    'level': 5,
                },
                'prefix_date': True,
                # 'S3': {
                #     'key_id': aws_credentials[0],
                #     'secret': aws_credentials[1],
                #     'bucket': aws_credentials[2],
                #     'prefix': 'parquet',
                # },
                'SVOE': {
                    's3_key_id': aws_credentials[0],
                    's3_secret': aws_credentials[1],
                    's3_bucket': aws_credentials[2],
                    's3_prefix': 'data_lake',
                    'glue_database': 'svoe_glue_db', # TODO sync with Terraform
                    'version': 'local' # TODO add version logging
                }
                # path=TEMP_FILES_PATH,
            },
            'storage_interval': 30,
        }

    def _cryptostore_config(
        self,
        exchange: str,
        instrument: str,
        symbols: list[str],
    ) -> dict:
        config = self._cryptostore_template()
        config['exchanges'] = self._exchange_config(exchange, instrument, symbols)
        return config

    def _exchange_config(
        self,
        exchange: str,
        instrument: str,
        symbols: list[str],
    ) -> dict:
        config = {exchange: {}}
        config[exchange]['retries'] = -1
        self._populate_channels(
            config,
            exchange,
            instrument,
            symbols,
        )

        return config

    def _cryptostore_config_FULL_DEBUG(self) -> dict:
        config = self._cryptostore_template()
        config['exchanges'] = self._exchanges_config_FULL_DEBUG()
        return config

    def _exchanges_config_FULL_DEBUG(self) -> dict:
        config = {}
        for exchange in self.exchanges_config.keys():
            config[exchange] = {}
            # per exchange retries?
            config[exchange]['retries'] = -1

            for instrument in self.exchanges_config[exchange].keys():
                symbols = self.exchanges_config[exchange][instrument][0]
                self._populate_channels(
                    config,
                    exchange,
                    instrument,
                    symbols,
                )

        return config

    def _populate_channels(
        self,
        config: dict,
        exchange: str,
        instrument: str,
        symbols: list[str],
    ) -> None:
        channels = self.exchanges_config[exchange][instrument][2]

        # ticker # TODO ticker is not populated^ why?
        if TICKER in channels:
            if TICKER in config[exchange]:
                config[exchange][TICKER].extend(symbols)
            else:
                config[exchange][TICKER] = symbols

        # l2 book
        max_depth_l2 = self.exchanges_config[exchange][instrument][1]
        if L2_BOOK in channels:
            if L2_BOOK in config[exchange]:
                config[exchange][L2_BOOK]['symbols'].extend(symbols)
            else:
                l2_book = {
                    'symbols': symbols,
                    'book_delta': True,
                }
                if max_depth_l2 > 0:
                    l2_book['max_depth'] = max_depth_l2
                config[exchange] = {
                    L2_BOOK: l2_book,
                }

        # l3 book
        if L3_BOOK in channels:
            if L3_BOOK in config[exchange]:
                config[exchange][L3_BOOK]['symbols'].extend(symbols)
            else:
                l3_book = {
                    'symbols': symbols,
                    'book_delta': True,
                }
                config[exchange] = {
                    L3_BOOK: l3_book,
                }

        # trades
        if TRADES in channels:
            if TRADES in config[exchange]:
                config[exchange][TRADES].extend(symbols)
            else:
                config[exchange][TRADES] = symbols

        # open interest
        if OPEN_INTEREST in channels:
            if OPEN_INTEREST in config[exchange]:
                config[exchange][OPEN_INTEREST].extend(symbols)
            else:
                config[exchange][OPEN_INTEREST] = symbols

        # funding
        if FUNDING in channels:
            if FUNDING in config[exchange]:
                config[exchange][FUNDING].extend(symbols)
            else:
                config[exchange][FUNDING] = symbols

        # liquidations
        if LIQUIDATIONS in channels:
            if LIQUIDATIONS in config[exchange]:
                config[exchange][LIQUIDATIONS].extend(symbols)
            else:
                config[exchange][LIQUIDATIONS] = symbols

    @staticmethod
    def _read_aws_credentials() -> list[str]:
        with open(AWS_CREDENTIALS_PATH) as file:
            data = yaml.load(file, Loader = yaml.FullLoader)

        return [data['key_id'], data['secret'], data['bucket']]

    @staticmethod
    def _dump_yaml_config(config: dict, path: str) -> str:
        with open(path, 'w+') as outfile:
            yaml.dump(config, outfile, default_flow_style=False, default_style=None)

        return path
