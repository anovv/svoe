from cryptofeed.callback import TradeCallback
from cryptofeed import FeedHandler
from cryptofeed.exchanges import Coinbase
from cryptofeed.defines import TRADES

async def trade(feed, pair, order_id, timestamp, side, amount, price, receipt_timestamp):
    print("Timestamp: {} Feed: {} Pair: {} ID: {} Side: {} Amount: {} Price: {}".format(timestamp, feed, pair, order_id, side, amount, price))


def main():
    f = FeedHandler()

    f.add_feed(Coinbase(pairs=['BTC-USD', 'ETH-USD'], channels=[TRADES], callbacks={TRADES: TradeCallback(trade)}))

    f.run()

if __name__ == '__main__':
    main()

