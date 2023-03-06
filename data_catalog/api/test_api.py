import sys
import unittest

from data_catalog.api.api import Api


class TestDataCatalogApi(unittest.TestCase):

    def test_get_meta(self):
        api = Api()
        l2_data_ranges = api.get_meta('BINANCE', 'l2_book', 'spot', 'BTC-USDT')
        l2_data_intervals_df = api.ranges_to_intervals_df(l2_data_ranges)
        print(l2_data_intervals_df)
        # api.plot_ranges(l2_data_ranges)
        print(l2_data_ranges[8])
        print(float(l2_data_ranges[8][0]['end_ts']) - float(l2_data_ranges[8][0]['start_ts']))
        # print(len(l2_data))
        # trades_data = api.get_meta

    def test_make_range(self):
        api = Api()
        l = [{'start_ts': 1, 'end_ts': 1.1}, {'start_ts': 2.4, 'end_ts': 2.5}, {'start_ts': 3.6, 'end_ts': 7}]
        res = api._make_ranges(l)
        assert res == [[{'start_ts': 1, 'end_ts': 1.1}], [{'start_ts': 2.4, 'end_ts': 2.5}], [{'start_ts': 3.6, 'end_ts': 7}]]

if __name__ == '__main__':
    t = TestDataCatalogApi()
    t.test_get_meta()