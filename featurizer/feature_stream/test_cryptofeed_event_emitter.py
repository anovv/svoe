import time
import unittest

from featurizer.data_definitions.common.ticker.cryptofeed.cryptofeed_ticker import CryptofeedTickerData
from featurizer.data_definitions.common.trades.cryptofeed.cryptofeed_trades import CryptofeedTradesData
from featurizer.data_definitions.data_definition import Event
from featurizer.feature_stream.cryptofeed_event_emitter import CryptofeedEventEmitter
from featurizer.features.feature_tree.feature_tree import Feature


class TestCryptofeedEventEmitter(unittest.TestCase):

    def test(self):
        emitter = CryptofeedEventEmitter.instance()
        def cb(event: Event):
            print(event)
        ticker_data_source = Feature(children=[], data_definition=CryptofeedTickerData, params={
            'exchange': 'BINANCE',
            'symbol': 'BTC-USDT',
        })
        trades_data_source = Feature(children=[], data_definition=CryptofeedTradesData, params={
            'exchange': 'BINANCE',
            'symbol': 'ETH-USDT',
        })
        emitter.register_callback(ticker_data_source, cb)
        emitter.register_callback(trades_data_source, cb)
        emitter.start()
        time.sleep(10)
        emitter.stop()


if __name__ == '__main__':
    t = TestCryptofeedEventEmitter()
    t.test()

