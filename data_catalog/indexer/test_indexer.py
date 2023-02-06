import unittest
from data_catalog.indexer import indexer
from utils.s3.s3_utils import inventory

class TestDataCatalogIndexer(unittest.TestCase):

    def test(self):
        inv = inventory()
        print(inv[0])

if __name__ == '__main__':
    t = TestDataCatalogIndexer()
    t.test()