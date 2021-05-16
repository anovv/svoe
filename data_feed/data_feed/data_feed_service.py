from cryptostore import Cryptostore

# TODO this path should be synced with cryptostore_config_builder consts
DATA_FEED_CONFIG_PATH = '/etc/svoe/data_feed/configs/data-feed-config.yaml'

class DataFeedService(object):

    @staticmethod
    def run() -> None:

        cs = Cryptostore(config=DATA_FEED_CONFIG_PATH)
        try:
            cs.run()
        except KeyboardInterrupt:
            pass
