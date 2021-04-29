from data_feed.config_builder import ConfigBuilder
from cryptostore import Cryptostore

class DataFeedService(object):

    @staticmethod
    def run() -> None:

        cb = ConfigBuilder()
        cryptostore_config_path = cb.cryptostore_single_config()
        cs = Cryptostore(config=cryptostore_config_path)
        try:
            cs.run()
        except KeyboardInterrupt:
            pass
