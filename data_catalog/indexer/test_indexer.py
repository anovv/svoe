import unittest
from data_catalog.indexer import indexer

class TestDataCatalogIndexer(unittest.TestCase):

    def test(self):
        BUCKET_NAME = 'svoe.test.1'
        files = indexer.list_files(BUCKET_NAME)
        # print(len(files[0]['Contents']))


if __name__ == '__main__':
    t = TestDataCatalogIndexer()
    t.test()