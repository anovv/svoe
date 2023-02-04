import unittest

import dask
import ray

from featurizer.features.definitions.ohlcv.ohlcv_feature_definition import OHLCVFeatureDefinition
from ray_cluster.featurizer import calculator as C
from ray.util.dask import ray_dask_get

from featurizer.features.definitions.mid_price.mid_price_feature_definition import MidPriceFeatureDefinition
from featurizer.features.feature_tree.feature_tree import construct_feature_tree
from ray_cluster import cluster_utils
from ray_cluster.testing_utils import mock_l2_book_delta_data_and_meta


class TestDaskOnRay(unittest.TestCase):


    def test_featurization(self):
        block_range, block_range_meta = mock_l2_book_delta_data_and_meta()
        data_params = {}
        feature_params = {}
        feature = construct_feature_tree(MidPriceFeatureDefinition, data_params, feature_params)
        task_graph = C.build_feature_task_graph(feature, block_range_meta)
        cluster_utils.connect()
        res = dask.compute(task_graph, scheduler=ray_dask_get)
        ray.shutdown()
        print(res)

if __name__ == '__main__':
    # unittest.main()
    t = TestDaskOnRay()
    t.test_featurization()