import time
import unittest

from featurizer.data_definitions.common.ticker.cryptofeed.cryptofeed_ticker import CryptofeedTickerData
from featurizer.data_definitions.common.trades.cryptofeed.cryptofeed_trades import CryptofeedTradesData
from featurizer.data_definitions.data_definition import Event
from featurizer.feature_stream.event_emitter.cryptofeed_event_emitter import CryptofeedEventEmitter
from featurizer.features.feature_tree.feature_tree import Feature


class TestCryptofeedEventEmitter(unittest.TestCase):

    def test(self):
        emitter = CryptofeedEventEmitter.instance()

        ticker_events = []
        trades_events = []

        def ticker_cb(event: Event):
            ticker_events.append(event)

        def trades_cb(event: Event):
            trades_events.append(event)

        ticker_data_source = Feature(children=[], data_definition=CryptofeedTickerData, params={
            'exchange': 'BINANCE',
            'symbol': 'BTC-USDT',
        })
        trades_data_source = Feature(children=[], data_definition=CryptofeedTradesData, params={
            'exchange': 'BINANCE',
            'symbol': 'BTC-USDT',
        })
        emitter.register_callback(ticker_data_source, ticker_cb)
        emitter.register_callback(trades_data_source, trades_cb)

        # TODO pass if no connection. try except?
        emitter.start()
        time.sleep(10)
        emitter.stop()
        assert len(ticker_events) != 0
        CryptofeedTickerData.validate_schema(ticker_events[0])
        assert len(trades_events) != 0
        CryptofeedTradesData.validate_schema(trades_events[0])



if __name__ == '__main__':
    t = TestCryptofeedEventEmitter()
    t.test()

