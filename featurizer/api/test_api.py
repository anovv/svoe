import unittest

from featurizer.api.api import Api
from featurizer.features.definitions.tvi.trade_volume_imb_fd import TradeVolumeImbFD
from featurizer.features.feature_tree.feature_tree import construct_feature_tree
from featurizer.sql.data_catalog.models import DataCatalog


class TestDataCatalogApi(unittest.TestCase):

    def test_get_meta(self):
        api = Api()
        l2_data_ranges = api._get_data_meta(['BINANCE'], ['l2_book'], ['spot'], ['BTC-USDT'])
        k = list(l2_data_ranges.keys())[0]
        print(l2_data_ranges[k])

    def test_delete_feature(self):
        feature_params1 = {0: {'window': '1m', 'sampling': '1s'}}
        data_params1 = [
            {DataCatalog.exchange.name: 'BINANCE',
             DataCatalog.data_type.name: 'trades',
             DataCatalog.instrument_type.name: 'spot',
             DataCatalog.symbol.name: 'BTC-USDT'}
        ]
        feature_tvi = construct_feature_tree(TradeVolumeImbFD, data_params1, feature_params1)
        api = Api()
        api.delete_features([feature_tvi])

    def test_store_feature_def(self):
        # TODO
        pass




if __name__ == '__main__':
    t = TestDataCatalogApi()
    t.test_delete_feature()