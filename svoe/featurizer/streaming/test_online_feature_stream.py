import time
import unittest
from threading import Thread, Event

import yaml
from cryptofeed import FeedHandler
from cryptofeed.defines import TICKER, L2_BOOK, TRADES
from cryptofeed.exchanges import Binance
from order_book import OrderBook
from streamz import Stream

from svoe.featurizer.config import FeaturizerConfig
from svoe.featurizer.streaming.block_writer.block_writer import BlockWriter
from svoe.featurizer.streaming.block_writer.memory_based_compactor import MemoryBasedCompactor
from svoe.featurizer.streaming.event_emitter.cryptofeed_event_emitter import CryptofeedEventEmitter
from svoe.featurizer.streaming.feature_stream_graph import FeatureStreamGraph
from svoe.featurizer.features.feature_tree.feature_tree import Feature


class TestOnlineFeatureStream(unittest.TestCase):
    def test_cryptofeed(self):
        # print(Bybit.symbols())
        # raise
        fh = FeedHandler(config={'uvloop': True, 'log': {'disabled': True}})
        async def ob_cb(obj, receipt_timestamp):
            ob: OrderBook = obj
            print(list(ob.to_dict().keys()))
            print(receipt_timestamp, ob.to_dict()['delta'])
            # print(receipt_timestamp, ob.to_dict()['book'])
            # print(receipt_timestamp, ob.to_dict()['book']['ask'])
            # print(receipt_timestamp, ob.to_dict()['book']['bid'])
            raise

        async def trades_cb(obj, receipt_timestamp):
            d = obj.to_dict()
            side = d['side']
            print(receipt_timestamp, 'trade', f'side: {side}')

        async def ticker_cb(obj, receipt_timestamp):
            d = obj.to_dict()
            bid = d['bid']
            print(receipt_timestamp, 'ticker', f'bid: {bid}')

        input = Stream()
        events = []
        def ppprint(e):
            print(e)

        def store(e):
            events.append(e)

        input.sink(ppprint)
        input.sink(store)

        async def streamz_cb(obj, receipt_timestamp):
            input.emit(obj, asynchronous=True)

        cbs = {TICKER: ticker_cb, TRADES: trades_cb, L2_BOOK: ob_cb}
        # fh.add_feed(Bybit(symbols=['BTC-USDT-PERP'], channels=[L2_BOOK], callbacks=book_cb))
        # fh.add_feed(Bybit(symbols=['BTC-USDT-PERP'], channels=[TRADES], callbacks=trades_cb))
        fh.add_feed(Binance(symbols=['BTC-USDT'], channels=[TICKER, TRADES], callbacks=cbs))
        # fh.add_feed(Binance(symbols=['BTC-USDT'], channels=[TRADES], callbacks=trades_cb))
        # fh.add_feed(BinanceFutures(symbols=['BTC-USDT-PERP'], channels=[TRADES], callbacks=trades_cb))
        # fh.add_feed(Binance(symbols=['BTC-USDT'], channels=[L2_BOOK], callbacks=book_cb))
        def stop_after():
            time.sleep(7)
            print(len(events))
            print(events[:10])
            fh.stop()
        Thread(target=stop_after).start()
        fh.run()

    def test_streaming(self):
        dct = yaml.safe_load('''
        feature_configs:
          - feature_definition: volatility.volatility_stddev_fd
            params:
              data_source:
                - exchange: BINANCE
                  instrument_type: spot
                  symbol: BTC-USDT
              feature:
                1:
                  dep_schema: ticker
                  sampling: 1s
          - feature_definition: price.mid_price_fd
            params:
              data_source:
                - exchange: BINANCE
                  instrument_type: spot
                  symbol: BTC-USDT
              feature:
                0:
                  dep_schema: ticker
                  sampling: 1s
        ''')
        config = FeaturizerConfig(**dct)
        feature_stream_graph = FeatureStreamGraph(features_or_config=config)
        outs = feature_stream_graph.get_outs()
        block_writer = BlockWriter(
            default_compactor=MemoryBasedCompactor({'in_memory_size_kb': 10})
        )
        for f in outs:
            def callback(feature: Feature, event: Event):
                block_writer.append_event(feature, event)

            feature_stream_graph.set_callback(f, callback)

        ins = feature_stream_graph.get_ins()
        emitter = CryptofeedEventEmitter.instance()
        for f in ins:
            def emitter_callback(feature: Feature, event: Event):
                # TODO set async=True?
                feature_stream_graph.get_stream(feature).emit(event, asynchronous=False)

            emitter.register_callback(f, emitter_callback)
        block_writer.start()
        emitter.start()
        time.sleep(240)
        emitter.stop()
        block_writer.stop()
        print('Done')

if __name__ == '__main__':
    # unittest.main()
    t = TestOnlineFeatureStream()
    t.test_streaming()
