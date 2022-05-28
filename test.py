# TODO move to PYTHONPATH
import sys
sys.path.append('/Users/anov/IdeaProjects/cryptofeed')
sys.path.append('/Users/anov/IdeaProjects/cryptostore')
# sys.path.append('/dask_cluster/')

from data_feed.data_feed_service import DataFeedService

def test_datafeed():
    DataFeedService.run()

# To rebuild Cython https://stackoverflow.com/questions/34928001/distutils-ignores-changes-to-setup-py-when-building-an-extension
# python setup.py clean --all
# python setup.py develop
if __name__ == '__main__':
    test_datafeed()