# import sys
# sys.path.append('/Users/anov/IdeaProjects/cryptofeed')
# sys.path.append('/Users/anov/IdeaProjects/cryptostore')

from data_feed.data_feed_service import DataFeedService

def test():
    DataFeedService.run()
    # read_s3()
    # ConfigBuilder.get_bitmex_pairs()

if __name__ == '__main__':
    test()
