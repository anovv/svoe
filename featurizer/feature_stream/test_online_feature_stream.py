import time
import unittest
from threading import Thread

from cryptofeed import FeedHandler
from cryptofeed.defines import TICKER, L2_BOOK, TRADES
from cryptofeed.exchanges import Bybit, Binance, BinanceFutures
from order_book import OrderBook
from streamz import Stream


class TestOnlineFeatureStreamGenerator(unittest.TestCase):
    def test_gen(self):
        # print(Bybit.symbols())
        # raise
        fh = FeedHandler(config={'uvloop': True, 'log': {'disabled': True}})
        async def ob(obj, receipt_timestamp):
            ob: OrderBook = obj
            print(list(ob.to_dict().keys()))
            print(receipt_timestamp, ob.to_dict()['delta'])
            # print(receipt_timestamp, ob.to_dict()['book'])
            # print(receipt_timestamp, ob.to_dict()['book']['ask'])
            # print(receipt_timestamp, ob.to_dict()['book']['bid'])
            raise

        async def cb(obj, receipt_timestamp):
            print(receipt_timestamp, obj.to_dict())

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

        book_cb = {L2_BOOK: ob}
        ticker_cb = {TICKER: streamz_cb}
        trades_cb = {TRADES: cb}
        cbs = {TICKER: cb, TRADES: cb, L2_BOOK: ob}
        # fh.add_feed(Bybit(symbols=['BTC-USDT-PERP'], channels=[L2_BOOK], callbacks=book_cb))
        # fh.add_feed(Bybit(symbols=['BTC-USDT-PERP'], channels=[TRADES], callbacks=trades_cb))
        fh.add_feed(Binance(symbols=['BTC-USDT'], channels=[L2_BOOK], callbacks=cbs))
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

if __name__ == '__main__':
    # unittest.main()
    t = TestOnlineFeatureStreamGenerator()
    t.test_gen()
