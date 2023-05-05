import unittest

from featurizer.data_catalog.api.api import Api


class TestDataCatalogApi(unittest.TestCase):

    def test_get_meta(self):
        api = Api()
        l2_data_ranges = api.get_meta(['BINANCE'], ['l2_book'], ['spot'], ['BTC-USDT'])
        k = list(l2_data_ranges.keys())[0]
        print(l2_data_ranges[k].keys())

if __name__ == '__main__':
    t = TestDataCatalogApi()
    t.test_get_meta()