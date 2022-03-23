from os import environ
if environ.get('ENV') == 'DEV':
    print('DEV ENV')
    import pyximport
    pyximport.install()

from cryptostore import Cryptostore

# TODO this path should be synced with Helm values
DATA_FEED_CONFIG_PATH = '/etc/svoe/data_feed/configs/data-feed-config.yaml'

class DataFeedService(object):

    @staticmethod
    def run() -> None:
        cs = Cryptostore(config=DATA_FEED_CONFIG_PATH)
        try:
            cs.run()
        except KeyboardInterrupt:
            pass
