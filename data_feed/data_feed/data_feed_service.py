from cryptostore import Cryptostore

class DataFeedService(object):

    @staticmethod
    def run() -> None:

        # TODO specify path to config
        cs = Cryptostore(config='')
        try:
            cs.run()
        except KeyboardInterrupt:
            pass
