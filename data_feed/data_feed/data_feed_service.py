
from data_feed.config_builder import ConfigBuilder
from cryptostore import Cryptostore
from cryptofeed.standards import BINANCE, COINBASE, KRAKEN, HUOBI


class DataFeedService(object):

    @staticmethod
    def run() -> None:
        exchanges = [BINANCE, COINBASE, KRAKEN, HUOBI]

        cb = ConfigBuilder(exchanges)
        cryptostore_config_path = cb.build_cryptostore_config()
        cs = Cryptostore(config=cryptostore_config_path)
        try:
            cs.run()
        except KeyboardInterrupt:
            pass
