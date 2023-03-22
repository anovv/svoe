import glob
import os
import shutil
import time

import dask
import numpy as np
import ray
from bokeh.io import show
from bokeh.models import ColumnDataSource, Range1d, LinearAxis
from bokeh.plotting import figure
from portion import Interval, closed
from ray import workflow
from ray.types import ObjectRef
from ray.util.dask import enable_dask_on_ray

import calculator as C
from featurizer.features.data.data_source_definition import DataSourceDefinition
from featurizer.features.data.l2_book_delats.l2_book_deltas import L2BookDeltasData
from featurizer.features.data.trades.trades import TradesData
from featurizer.features.definitions.ohlcv.ohlcv_feature_definition import OHLCVFeatureDefinition
from featurizer.features.definitions.l2_book_snapshot.l2_book_snapshot_feature_definition import L2BookSnapshotFeatureDefinition
from featurizer.features.definitions.mid_price.mid_price_feature_definition import MidPriceFeatureDefinition
from featurizer.features.definitions.volatility.volatility_stddev_feature_definition import VolatilityStddevFeatureDefinition
from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.features.feature_tree.feature_tree import construct_feature_tree

import portion as P
import unittest
import dask.dataframe as dd
import pandas as pd
from typing import Type, List
from anytree import RenderTree
from ray_cluster.testing_utils import mock_meta, mock_feature, mock_trades_data_and_meta, mock_l2_book_delta_data_and_meta, mock_ts_df, mock_ts_df_remote
from utils.pandas.df_utils import concat, load_df, get_size_kb, gen_split_df_by_mem


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

    def test_merge_asof(self):
        # dfs = [
        #     mock_ts_df([4, 7, 9], 'a'),
        #     mock_ts_df([2, 5, 6, 8], 'b'),
        #     mock_ts_df([1, 3, 6, 10], 'c'),
        # ]
        dfs = [
            mock_ts_df([4, 7, 9, 14, 16, 20], 'a'),
            mock_ts_df([2, 5, 6, 8, 10, 11, 12, 18], 'b'),
            mock_ts_df([1, 3, 7, 10, 19], 'c'),
        ]
        res = C.merge_asof_multi(dfs)
        print(res)

    def test_point_in_time_join(self):
        label_feature = mock_feature(1)
        dag = {
            label_feature: {
                closed(0, 5.01): mock_ts_df_remote.bind([4], 'a', ['a0']),
                closed(5.02, 11.01): mock_ts_df_remote.bind([7, 10], 'a', ['a1', 'a2']),
                closed(11.02, 15.01): mock_ts_df_remote.bind([14], 'a', ['a3']),
                closed(15.02, 18.01): mock_ts_df_remote.bind([16], 'a', ['a4']),
                closed(18.02, 21.01): mock_ts_df_remote.bind([20], 'a', ['a5']),
            },
            mock_feature(2): {
                closed(0, 9.01): mock_ts_df_remote.bind([2, 5, 6, 8], 'b', ['b0', 'b1', 'b2', 'b3']),
                closed(9.02, 17.01): mock_ts_df_remote.bind([11, 12], 'b', ['b4', 'b5']),
                closed(17.02, 21.01): mock_ts_df_remote.bind([18], 'b', ['b6'])
            },
            mock_feature(3): {
                closed(0, 4.01): mock_ts_df_remote.bind([1, 3], 'c', ['c0', 'c1']),
                closed(4.02, 21.01): mock_ts_df_remote.bind([7, 10, 19], 'c', ['c2', 'c3', 'c4']),
            },
        }

        # purge workflows storage
        path = '/tmp/ray/workflows_data/workflows/'
        try:
            shutil.rmtree(path)
        except:
            pass

        # distributed
        nodes = C.point_in_time_join(dag, list(dag.keys()), label_feature)
        with ray.init(address='auto'):
            # execute dag
            nodes_res_dfs = ray.get([ray.workflow.run_async(dag=node, workflow_id=f'{time.time_ns()}') for node in nodes])
            res_ray = concat(nodes_res_dfs)
            print(res_ray)

        # sequential
        with ray.init(address='auto'):
            dfs = []
            for feature in dag:
                nodes_res_dfs = ray.get([ray.workflow.run_async(node) for node in list(dag[feature].values())])
                dfs.append(concat(nodes_res_dfs))
            res_seq = C.merge_asof_multi(dfs)
            print(res_seq)

        # TODO assert
        print(res_ray.equals(res_seq))

    def test_feature_label_set(self):
        block_range, block_range_meta = mock_l2_book_delta_data_and_meta()
        data_params = {}
        feature_params = {}
        feature_mid_price = construct_feature_tree(MidPriceFeatureDefinition, data_params, feature_params)
        feature_volatility = construct_feature_tree(VolatilityStddevFeatureDefinition, data_params, feature_params)
        flset = C.build_feature_label_set_task_graph([feature_mid_price, feature_volatility], block_range_meta, feature_mid_price)
        res = None

        # @dask.delayed
        # def ref_to_df(ref: List[ObjectRef]) -> pd.DataFrame:
        #     return ref[0]

        # with ray.init(address='auto', runtime_env={'pip': ['pyarrow==6.0.1']}):
        with ray.init(address='auto'):
            # execute dag
            refs = [ray.workflow.run_async(dag=node, workflow_id=f'{time.time_ns()}') for node in flset]
            # nodes_res_dfs = ray.get(refs)
            # res = concat(nodes_res_dfs)
            ray.wait(refs, num_returns=len(refs))
            dataset = ray.data.from_pandas_refs(refs)
            with enable_dask_on_ray():
                # ddf = dd.from_delayed([ref_to_df([ref]) for ref in refs])
                ddf = dataset.to_dask()
                res = ddf.sample(frac=0.5).compute()
            print(res)

        # res.plot(x='timestamp', y=['mid_price', 'volatility'])

        source = ColumnDataSource(res)
        p = figure(x_axis_type="datetime", plot_width=800, plot_height=350)
        p.line('timestamp', 'mid_price', source=source)
        p.y_range = Range1d(start=19000, end=20000)
        p.extra_y_ranges = {'volatility': Range1d(start=0, end=10)}
        p.add_layout(LinearAxis(y_range_name='volatility'), 'right')
        p.line('timestamp', 'volatility', source=source, y_range_name='volatility')

        # output_file("ts.html")
        show(p)

    def test_cryptotick(self):
        df = load_df('s3://svoe-cryptotick-data/limitbook_full/20230201/BINANCE_SPOT_BTC_USDT.csv.gz', extension='csv')
        print(get_size_kb(df))

    # TODO util this
    def test_df_split(self):
        l2_data, _ = mock_l2_book_delta_data_and_meta()
        l2_dfs = list(l2_data.values())[0]

        trades_data, _ = mock_trades_data_and_meta()
        trades_dfs = list(trades_data.values())[0]

        l2_split_size_kb = 300
        l2_split_sizes = []
        for l2_df in l2_dfs:
            l2_split_gen = gen_split_df_by_mem(l2_df, l2_split_size_kb)
            splits = []
            for split_df in l2_split_gen:
                l2_split_sizes.append(get_size_kb(split_df))
                splits.append(split_df)
            concated = concat(splits)
            assert concated.equals(l2_df)
        print(f'Avg L2 split size:{np.mean(l2_split_sizes)}')

        trades_split_size_kb = 10
        trades_split_sizes = []
        for trades_df in trades_dfs:
            trades_split_gen = gen_split_df_by_mem(trades_df, trades_split_size_kb)
            splits = []
            for split_df in trades_split_gen:
                trades_split_sizes.append(get_size_kb(split_df))
                splits.append(split_df)
            concated = concat(splits)
            assert concated.equals(trades_df)

        print(f'Avg Trades split size:{np.mean(trades_split_sizes)}')


if __name__ == '__main__':
    # unittest.main()
    t = TestFeatureCalculator()
    # t.test_featurization(L2BookSnapshotFeatureDefinition, L2BookDeltasData)
    # t.test_featurization(OHLCVFeatureDefinition, TradesData)
    # t.test_point_in_time_join()
    # t.test_merge_asof()
    # t.test_feature_label_set()
    # t.test_cryptotick()
    t.test_df_split()

    # TODO figure out if we need to use lookahead_shift as a label
    # TODO (since all the features are autoregressive and already imply past values,
    # TODO we may use just current values as labels?)
    # def test_look_ahead_merge(self):
    #     look_ahead = 3
    #     a = [1, 2, 3, 5, 8, 9, 20, 21, 22, 23, 28, 31, 32, 33, 34, 40, 41, 42, 46]
    #
    #     b = [3, 5, 5, 8, 9, 9, 23, 23, 23, 23, 31, 34, 34, 34, 34, 42, 42, 42, 46]
    #
    #     df = pd.DataFrame(a, columns=['ts'])
    #     df['ahead_timestamp'] = df['timestamp'] + look_ahead
    #     shifted = pd.merge_asof(df, df, left_on='ahead_timestamp', right_on='ts', direction='backward')
    #     print(shifted)
    #
    # def test_look_ahead_merge_multi(self):
    #     a = [[1, 2, 3, 5], [8, 9, 20, 21], [22, 23, 28], [31, 32, 33, 34, 40], [41, 42, 46], [47, 48]]
    #     metas = [{'start_ts': l[0], 'end_ts': l[-1]} for l in a]
    #     look_ahead = 3
    #
    #     groups = []
    #
    #     # groups
    #     for i in range(len(metas)):
    #         meta = metas[i]
    #         group = [meta]
    #         end = meta['end_ts'] + look_ahead
    #         for j in range(i + 1, len(metas)):
    #             if metas[j]['end_ts'] <= end or (metas[j]['start_ts'] <= end <= metas[j]['end_ts']):
    #                 group.append(metas[j])
    #             else:
    #                 break
    #         groups.append(group)
    #
    #     res_metas = []
    #     results = []
    #     for i in range(len(metas)):
    #         meta = metas[i]
    #         group = groups[i]
    #         start = meta['start_ts'] + look_ahead
    #         if start > group[-1]['end_ts']:
    #             # no data in lookahead window for this block
    #             continue
    #
    #         # TODO overlap with groups end?
    #         end = meta['end_ts'] + look_ahead
    #
    #         # TODO
    #         def concat(group):
    #             return
    #
    #         # TODO
    #         def sub_df(*args):
    #             return
    #
    #         # TODO
    #         def to_res(*args):
    #             return
    #
    #         # TODO
    #         dfs = []
    #
    #         df = dfs[i]
    #         df['ahead_ts'] = df['ts'] + look_ahead
    #         grouped = concat(group)
    #         shifted = pd.merge_asof(df, grouped, left_on='ahead_timestamp', right_on='ts', direction='backward')
    #         result = sub_df(to_res(shifted), start, end)
    #
    #         # TODO overlap with groups end?
    #         res_meta = {'start_ts': start, 'end_ts': end}
    #
    #         # todo put this in task graph
    #         results.append(result)
    #         res_metas.append(res_meta)