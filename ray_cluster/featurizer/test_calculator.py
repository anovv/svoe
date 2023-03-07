import time

import ray
from ray import workflow

import calculator as C
from featurizer.features.data.data_source_definition import DataSourceDefinition
from featurizer.features.data.l2_book_delats.l2_book_deltas import L2BookDeltasData
from featurizer.features.data.trades.trades import TradesData
from featurizer.features.definitions.ohlcv.ohlcv_feature_definition import OHLCVFeatureDefinition
from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.features.feature_tree.feature_tree import construct_feature_tree

import portion as P
import unittest
import dask
import pandas as pd
from typing import Type
from anytree import RenderTree
from ray_cluster.testing_utils import mock_meta, mock_feature, mock_trades_data_and_meta, mock_l2_book_delta_data_and_meta


class TestFeatureCalculator(unittest.TestCase):

    def test_get_ranges_overlaps(self):
        grouped_range = {}
        ranges_a = P.IntervalDict()
        ranges_a[P.closed(1, 4)] = [mock_meta(1, 2), mock_meta(2.1, 5)]
        ranges_a[P.closed(4.1, 8)] = [mock_meta(5, 5.5), mock_meta(6, 7)]
        ranges_a[P.closed(9, 15)] = [mock_meta(9, 15)]
        grouped_range[mock_feature(1)] = ranges_a

        ranges_b = P.IntervalDict()
        ranges_b[P.closed(2, 5)] = [mock_meta(2, 3), mock_meta(3.1, 6)]
        ranges_b[P.closed(6, 7)] = [mock_meta(6, 7)]
        ranges_b[P.closed(9, 20)] = [mock_meta(9, 15), mock_meta(15.1, 18), mock_meta(18.1, 22)]
        grouped_range[mock_feature(2)] = ranges_b

        expected = P.IntervalDict()
        expected[P.closed(2, 4)] = {
            mock_feature(1): [{'start_ts': 1, 'end_ts': 2}, {'start_ts': 2.1, 'end_ts': 5}],
            mock_feature(2): [{'start_ts': 2, 'end_ts': 3}, {'start_ts': 3.1, 'end_ts': 6}]
        }
        expected[P.closed(4.1, 5)] = {
            mock_feature(1): [{'start_ts': 5, 'end_ts': 5.5}, {'start_ts': 6, 'end_ts': 7}],
            mock_feature(2): [{'start_ts': 2, 'end_ts': 3}, {'start_ts': 3.1, 'end_ts': 6}]
        }
        expected[P.closed(6, 7)] = {
            mock_feature(1): [{'start_ts': 5, 'end_ts': 5.5}, {'start_ts': 6, 'end_ts': 7}],
            mock_feature(2): [{'start_ts': 6, 'end_ts': 7}]
        }
        expected[P.closed(9, 15)] = {
            mock_feature(1): [{'start_ts': 9, 'end_ts': 15}],
            mock_feature(2): [{'start_ts': 9, 'end_ts': 15}, {'start_ts': 15.1, 'end_ts': 18},
                                             {'start_ts': 18.1, 'end_ts': 22}]
        }

        overlaps = C.get_ranges_overlaps(grouped_range)
        self.assertEqual(overlaps, expected)

    # TODO customize dask graph visualization
    # https://stackoverflow.com/questions/58394758/adding-labels-to-a-dask-graph
    # https://stackoverflow.com/questions/67680325/annotations-for-custom-graphs-in-dask
    def test_featurization(self, feature_def: Type[FeatureDefinition], data_def: Type[DataSourceDefinition]):
        # mock consecutive l2 delta blocks
        if data_def == L2BookDeltasData:
            block_range, block_range_meta = mock_l2_book_delta_data_and_meta()
        elif data_def == TradesData:
            block_range, block_range_meta = mock_trades_data_and_meta()
        else:
            raise ValueError(f'Unsupported data_def for mocking: {data_def}')

        # build feature tree
        # TODO populate these
        data_params = {}
        feature_params = {}
        feature = construct_feature_tree(feature_def, data_params, feature_params)
        print(RenderTree(feature))
        # calculate in offline/distributed way
        task_graph = C.build_feature_task_graph(feature, block_range_meta)
        print(task_graph)
        # dask.visualize(*task_graph)
        # res_blocks = dask.compute(task_graph)
        # offline_res = pd.concat(*res_blocks)
        offline_res = C.execute_task_graph(task_graph, feature)

        print(offline_res)

        # calculate online
        stream_graph = C.build_stream_graph(feature)
        stream = stream_graph[feature]
        sources = {data: stream_graph[data] for data in block_range_meta.keys()}
        merged_events = C.merge_feature_blocks(block_range)
        online_res = C.run_stream(merged_events, sources, stream)
        print(online_res)

        # TODO we may have 1ts duplicate entry (due to snapshot_ts based block partition of l2_delta data source)
        # assert_frame_equal(offline_res, online_res)


@ray.remote
def t1():
    print('Started t1')
    time.sleep(1)
    print('Finished t1')
    return ['t1']


@ray.remote
def t2():
    print('Started t2')
    time.sleep(1)
    print('Finished t2')
    return ['t2']


# @ray.remote
# def t3(data):
#     print('Started t3')
#     time.sleep(1)
#     print('Finished t3')
#     return data['t1'] + data['t2']

@ray.remote
def t3(t1, t2):
    print('Started t3')
    time.sleep(1)
    print('Finished t3')
    return t1 + t2


def test_dep_tasks():
    with ray.init(address='auto'):
        _t1 = t1.bind()
        _t2 = t2.bind()
        # data = {'t1': _t1, 't2': _t2}
        _t3 = t3.bind(_t1, _t2)

        r = workflow.run_async(_t3)

        print(ray.get(r))

if __name__ == '__main__':
    # unittest.main()
    t = TestFeatureCalculator()
    t.test_featurization(OHLCVFeatureDefinition, TradesData)
    # test_dep_tasks()