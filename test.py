# import sys
# sys.path.append('/Users/anov/IdeaProjects/cryptofeed')
# sys.path.append('/Users/anov/IdeaProjects/cryptostore')

from data_feed.data_feed_service import DataFeedService
from data_feed.config_builder import ConfigBuilder

def test():

    cb = ConfigBuilder()
    print(cb.kuber_config_map())
    # DataFeedService.run()
    # read_s3()
    # ConfigBuilder.get_bitmex_pairs()

if __name__ == '__main__':
    test()
