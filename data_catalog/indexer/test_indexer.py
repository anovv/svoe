import unittest
from data_catalog.indexer import indexer
from utils.s3.s3_utils import inventory


class TestDataCatalogIndexer(unittest.TestCase):

    def test_parse_s3_keys(self):
        # TODO add multiproc
        exchange_symbol_unique_pairs = set()
        for _ in range(20):
            batch = next(indexer.generate_input_items())
            for i in batch:
                exchange_symbol_unique_pairs.add((i['exchange'], i['symbol']))
        print(exchange_symbol_unique_pairs)

if __name__ == '__main__':
    t = TestDataCatalogIndexer()
    t.test_parse_s3_keys()