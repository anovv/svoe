import unittest

from data_catalog.api.api import Api


class TestDataCatalogApi(unittest.TestCase):

    def test_get_meta(self):
        api = Api()
        l2_data = api.get_meta('BINANCE', 'l2_book', 'spot', 'BTC-USDT')
        print(l2_data)
        # trades_data = api.get_meta

if __name__ == '__main__':
    t = TestDataCatalogApi()
    t.test_get_meta()