from data_feed.configs.data_feed.base_config_builder import BaseConfigBuilder
from cryptofeed.defines import TICKER, TRADES, L2_BOOK, L3_BOOK, LIQUIDATIONS, OPEN_INTEREST, FUNDING

from pathlib import Path
import yaml

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
            'cache': 'redis',
            'redis': {
                'ip': REDIS_IP,
                'port': REDIS_PORT,
                'socket': None,
                'del_after_read': True,
                'retention_time': None,
                'start_flush': START_FLUSH,
            },
            'storage': ['svoe'],
            'storage_retries': 3,
            'storage_retry_wait': 10,
            'write_on_stop': True,
            'num_write_threads': 100,
            'svoe': {
                's3_key_id': aws_credentials[0],
                's3_secret': aws_credentials[1],
                's3_bucket': aws_credentials[2],
                's3_prefix': 'data_lake',
                'glue_database': 'svoe_glue_db',  # TODO sync with Terraform
                'compression': 'gzip',
                'version': 'local',  # TODO add version logging
            },
            'storage_interval': 30,
            'health_check': {
                'port': 1234,
                'path': '/health'
            },
            'prometheus': {
                'port': 8000,
                'multiproc_dir': '/Users/anov/IdeaProjects/svoe/prometheus_multiproc_dir' # TODO this should be unique per config
            }
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
        # TODO per exchange per channel retry support e.g.
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
            if exchange not in config:
                # TODO per exchange per channel retry support e.g.
                # channel_timeouts:
                #   l2_book: 30
                #   trades: 120
                #   ticker: 120
                #   funding: -1
                config[exchange] = {'retries': -1}

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

        # TODO some exchanges don't have all channels supported,
        # e.g.
        # OKEX implementation has no liquidations channel support https://github.com/bmoscon/cryptofeed/issues/612
        # PHEMEX has no funding channel
        # BYBIT has not ticker

        channels = self.exchanges_config[exchange][instrument][2]

        # ticker
        if TICKER in channels:
            if TICKER in config[exchange]:
                l = config[exchange][TICKER].copy()
                l.extend(symbols)
                config[exchange][TICKER] = l
            else:
                config[exchange][TICKER] = symbols

        # l2 book
        max_depth_l2 = self.exchanges_config[exchange][instrument][1]
        if L2_BOOK in channels:
            if L2_BOOK in config[exchange]:
                l = config[exchange][L2_BOOK]['symbols'].copy()
                l.extend(symbols)
                config[exchange][L2_BOOK]['symbols'] = l
            else:
                l2_book = {
                    'symbols': symbols,
                    'book_delta': True,
                }
                if max_depth_l2 > 0:
                    l2_book['max_depth'] = max_depth_l2

                config[exchange][L2_BOOK] = l2_book

        # l3 book
        if L3_BOOK in channels:
            if L3_BOOK in config[exchange]:
                l = config[exchange][L3_BOOK]['symbols'].copy()
                l.extend(symbols)
                config[exchange][L3_BOOK]['symbols'] = l
            else:
                l3_book = {
                    'symbols': symbols,
                    'book_delta': True,
                }
                config[exchange][L3_BOOK] = l3_book

        # trades
        if TRADES in channels:
            if TRADES in config[exchange]:
                l = config[exchange][TRADES].copy()
                l.extend(symbols)
                config[exchange][TRADES] = l
            else:
                config[exchange][TRADES] = symbols

        # open interest
        if OPEN_INTEREST in channels:
            if OPEN_INTEREST in config[exchange]:
                l = config[exchange][OPEN_INTEREST].copy()
                l.extend(symbols)
                config[exchange][OPEN_INTEREST] = l
            else:
                config[exchange][OPEN_INTEREST] = symbols

        # funding
        if FUNDING in channels:
            if FUNDING in config[exchange]:
                l = config[exchange][FUNDING].copy()
                l.extend(symbols)
                config[exchange][FUNDING] = l
            else:
                config[exchange][FUNDING] = symbols

        # liquidations
        if LIQUIDATIONS in channels:
            if LIQUIDATIONS in config[exchange]:
                l = config[exchange][LIQUIDATIONS].copy()
                l.extend(symbols)
                config[exchange][LIQUIDATIONS] = l
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
