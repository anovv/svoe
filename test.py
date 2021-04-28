# import sys
# sys.path.append('/Users/anov/IdeaProjects/cryptofeed')
# sys.path.append('/Users/anov/IdeaProjects/cryptostore')

from data_feed.data_feed_service import DataFeedService
from data_feed.config_builder import ConfigBuilder
from cryptofeed.standards import BINANCE, COINBASE, KRAKEN, HUOBI

def test():

    exchanges = [BINANCE, COINBASE, KRAKEN, HUOBI]
    cb = ConfigBuilder(exchanges)
    print(cb.pairs_to_kuber_pods())
    # DataFeedService.run()
    # read_s3()
    # ConfigBuilder.get_bitmex_pairs()

if __name__ == '__main__':
    test()
