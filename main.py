
import argparse

from cryptofeed.callback import TickerCallback, BookUpdateCallback, TradeCallback, BookCallback
from cryptofeed import FeedHandler
from cryptofeed.exchanges import Binance, Kraken
from cryptofeed.defines import TRADES, TICKER, L2_BOOK, L3_BOOK, BOOK_DELTA
from config_builder import build_cryptostore_config
from config_builder import get_binance_pairs, get_coinbase_pairs, get_kraken_pairs
from config_builder import read_aws_creds

from cryptostore import Cryptostore

from kafka_handler import handle_l2

async def trade(feed, pair, order_id, timestamp, side, amount, price, receipt_timestamp):
    print("Ts: {} Feed: {} Pair: {} ID: {} Side: {} Amount: {} Price: {} Rec Ts: {}".format(timestamp, feed, pair, order_id, side, amount, price, receipt_timestamp))

async def ticker(feed, pair, bid, ask, timestamp, receipt_timestamp):
    print("Ts: {} Feed: {} Pair: {} Bid: {} Ask: {} Rec Ts: {}".format(timestamp, feed, pair, bid, ask, receipt_timestamp))

async def book(feed, pair, book, timestamp, receipt_timestamp):
    print("Ts: {} Feed: {} Pair: {} Book: {} Rec Ts: {}".format(timestamp, feed, pair, book, receipt_timestamp))

async def book_update(feed, pair, delta, timestamp, receipt_timestamp):
    print("Ts: {} Feed: {} Pair: {} Delta: {} Rec Ts: {}".format(timestamp, feed, pair, delta, receipt_timestamp))

def read_parquet():
    import pyarrow.parquet as pq
    table = pq.read_table('parquet/trades.parquet')
    print(table.to_pandas())

def main():

    # f = FeedHandler()
    # symbols = get_kraken_pairs()
    # f.add_feed(Kraken(symbols=symbols, channels=[TRADES], callbacks={TRADES: TradeCallback(trade)}))
    # f.add_feed(Kraken(symbols=symbols, channels=[TICKER], callbacks={TICKER: TickerCallback(ticker)}))
    # f.add_feed(Kraken(symbols=['BTC-USD'], channels=[L2_BOOK], callbacks={L2_BOOK: BookCallback(book)}))
    # f.run()

    parser = argparse.ArgumentParser(description='SVOE')
    parser.add_argument('--ex', nargs='+', dest='exchanges')
    opts = parser.parse_args()
    exchanges = opts.exchanges
    # exchanges = ['KRAKEN']
    cryptostore_config_path = build_cryptostore_config(exchanges)
    cs = Cryptostore(config=cryptostore_config_path)
    try:
        cs.run()
    except KeyboardInterrupt:
        pass

    # handle_l2()

if __name__ == '__main__':
    main()
