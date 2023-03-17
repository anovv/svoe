import time

import ray
from ray import workflow

import calculator as C
from featurizer.features.data.data_source_definition import DataSourceDefinition
from featurizer.features.data.l2_book_delats.l2_book_deltas import L2BookDeltasData
from featurizer.features.data.trades.trades import TradesData
from featurizer.features.definitions.ohlcv.ohlcv_feature_definition import OHLCVFeatureDefinition
from featurizer.features.definitions.l2_book_snapshot.l2_book_snapshot_feature_definition import L2BookSnapshotFeatureDefinition
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

        overlaps = C.get_overlaps(grouped_range)
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
        task_graph = C.build_feature_task_graph({}, feature, block_range_meta)
        print(task_graph)
        # dask.visualize(*task_graph)
        # res_blocks = dask.compute(task_graph)
        res_blocks = C.execute_task_graph(task_graph, feature)
        offline_res = pd.concat(res_blocks)
        print(offline_res)

        # calculate online
        stream_graph = C.build_stream_graph(feature)
        stream = stream_graph[feature]
        sources = {data: stream_graph[data] for data in block_range_meta.keys()}
        merged_events = C.merge_blocks(block_range)
        online_res = C.run_stream(merged_events, sources, stream)
        print(online_res)

        # TODO we may have 1ts duplicate entry (due to snapshot_ts based block partition of l2_delta data source)
        # assert_frame_equal(offline_res, online_res)

    def test_look_ahead_merge(self):
        look_ahead = 3
        a = [1, 2, 3, 5, 8, 9, 20, 21, 22, 23, 28, 31, 32, 33, 34, 40, 41, 42, 46]

        b = [3, 5, 5, 8, 9, 9, 23, 23, 23, 23, 31, 34, 34, 34, 34, 42, 42, 42, 46]

        df = pd.DataFrame(a, columns=['ts'])
        df['ahead_timestamp'] = df['timestamp'] + look_ahead
        shifted = pd.merge_asof(df, df, left_on='ahead_timestamp', right_on='ts', direction='backward')
        print(shifted)

    def test_look_ahead_merge_multi(self):
        a = [[1, 2, 3, 5], [8, 9, 20, 21], [22, 23, 28], [31, 32, 33, 34, 40], [41, 42, 46], [47, 48]]
        metas = [{'start_ts': l[0], 'end_ts': l[-1]} for l in a]
        look_ahead = 3

        groups = []

        # groups
        for i in range(len(metas)):
            meta = metas[i]
            group = [meta]
            end = meta['end_ts'] + look_ahead
            for j in range(i + 1, len(metas)):
                if metas[j]['end_ts'] <= end or (metas[j]['start_ts'] <= end <= metas[j]['end_ts']):
                    group.append(metas[j])
                else:
                    break
            groups.append(group)

        res_metas = []
        results = []
        for i in range(len(metas)):
            meta = metas[i]
            group = groups[i]
            start = meta['start_ts'] + look_ahead
            if start > group[-1]['end_ts']:
                # no data in lookahead window for this block
                continue

            # TODO overlap with groups end?
            end = meta['end_ts'] + look_ahead

            # TODO
            def concat(group):
                return

            # TODO
            def sub_df(*args):
                return

            # TODO
            def to_res(*args):
                return

            # TODO
            dfs = []

            df = dfs[i]
            df['ahead_ts'] = df['ts'] + look_ahead
            grouped = concat(group)
            shifted = pd.merge_asof(df, grouped, left_on='ahead_timestamp', right_on='ts', direction='backward')
            result = sub_df(to_res(shifted), start, end)

            # TODO overlap with groups end?
            res_meta = {'start_ts': start, 'end_ts': end}

            # todo put this in task graph
            results.append(result)
            res_metas.append(res_meta)

    def _mock_ts_df(self, ts, df_name):
        vals = [f'{df_name}{i}' for i in range(len(ts))]
        df = pd.DataFrame(list(zip(ts, vals)), columns=['timestamp', df_name])
        df.set_index('timestamp')
        return df


    def test_merge_asof(self):

        dfs = [
            self._mock_ts_df([4, 7, 9], 'a'),
            self._mock_ts_df([2, 5, 6, 8], 'b'),
            self._mock_ts_df([1, 3, 6, 10], 'c'),
        ]
        # dfs = dfs * 100
        res = dfs[0]
        for i in range(1, len(dfs)):
            res = pd.merge_asof(res, dfs[i], on='timestamp', direction='backward')
            # res = pd.merge(res, dfs[i], how='outer', on='timestamp')
            res.set_index('timestamp')
        # res.fillna(method='ffill')
        print(res)

if __name__ == '__main__':
    # unittest.main()
    t = TestFeatureCalculator()
    # t.test_featurization(L2BookSnapshotFeatureDefinition, L2BookDeltasData)
    # t.test_featurization(OHLCVFeatureDefinition, TradesData)
    t.test_merge_asof()