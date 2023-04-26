import shutil
import time

import ciso8601
import numpy as np
import ray
from bokeh.io import show
from bokeh.models import ColumnDataSource, Range1d, LinearAxis
from bokeh.plotting import figure
from portion import Interval, closed
from ray.util.dask import enable_dask_on_ray
import matplotlib.pyplot as plt

import calculator as C
from data_catalog.api.api import Api
from featurizer.features.data.data_source_definition import DataSourceDefinition
from featurizer.features.data.l2_book_incremental.cryptofeed.cryptofeed_l2_book_incremental import CryptofeedL2BookIncrementalData
from featurizer.features.data.l2_book_incremental.cryptotick.cryptotick_l2_book_incremental import CryptotickL2BookIncrementalData
from featurizer.features.data.l2_book_incremental.cryptotick.utils import preprocess_l2_inc_df, \
    process_cryptotick_timestamps
from featurizer.features.data.trades.trades import TradesData
from featurizer.features.definitions.l2_snapshot.l2_snapshot_fd import L2SnapshotFD
from featurizer.features.definitions.mid_price.mid_price_fd import MidPriceFD
from featurizer.features.definitions.volatility.volatility_stddev_fd import VolatilityStddevFD
from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.features.feature_tree.feature_tree import construct_feature_tree, Feature

import portion as P
import unittest
import pandas as pd
from typing import Type, List
from anytree import RenderTree
from ray_cluster.testing_utils import mock_meta, mock_feature, mock_trades_data_and_meta, mock_l2_book_delta_data_and_meta, mock_ts_df, mock_ts_df_remote
from utils.pandas.df_utils import concat, load_df, get_size_kb, gen_split_df_by_mem, cache_df_if_needed, get_cached_df


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
        if data_def == CryptofeedL2BookIncrementalData:
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
        nodes = C.point_in_time_join_dag(dag, list(dag.keys()), label_feature)
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
        feature_mid_price = construct_feature_tree(MidPriceFD, data_params, feature_params)
        feature_volatility = construct_feature_tree(VolatilityStddevFD, data_params, feature_params)
        flset = C.build_feature_label_set_task_graph([feature_mid_price, feature_volatility], block_range_meta, feature_mid_price)
        res = None

        # @dask.delayed
        # def ref_to_df(ref: List[ObjectRef]) -> pd.DataFrame:
        #     return ref[0]

        # with ray.init(address='auto', runtime_env={'pip': ['pyarrow==6.0.1']}):
        with ray.init(address='auto'):
            # execute dag
            refs = [node.execute() for node in flset]
            ray.wait(refs, num_returns=len(refs))
            dataset = ray.data.from_pandas_refs(refs)
            with enable_dask_on_ray():
                # ddf = dd.from_delayed([ref_to_df([ref]) for ref in refs])
                ddf = dataset.to_dask()
                res = ddf.sample(frac=0.5).compute()
            print(res)

    def test_cryptotick_df_split(self):
        path = 's3://svoe-junk/27606-BITSTAMP_SPOT_BTC_EUR.csv.gz'
        date_str = '20230201'
        print('Started loading')
        df = load_df(path, extension='csv')
        print('Finished loading, started processing')
        df = preprocess_l2_inc_df(df, date_str)
        print('Finished loading, started preprocessing')

        split_size_kb = 100 * 1024
        split_gen = gen_split_df_by_mem(df, split_size_kb)
        splits = []
        i = 0
        for split in split_gen:
            print(f'Split {i}')
            splits.append(split)
            if i > 0:
                assert splits[i - 1].iloc[-1]['timestamp'] != splits[i].iloc[0]['timestamp']
            i += 1

        print(len(splits))
        print(f'Avg split size {np.mean([get_size_kb(split) for split in splits])}kb')

        assert concat(splits).equals(df)

    # TODO util this
    def test_cryptofeed_df_split(self):
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

            for i in range(1, len(splits)):
                assert splits[i - 1].iloc[-1]['timestamp'] != splits[i].iloc[0]['timestamp']

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

            for i in range(1, len(splits)):
                assert splits[i - 1].iloc[-1]['timestamp'] != splits[i].iloc[0]['timestamp']

            concated = concat(splits)
            assert concated.equals(trades_df)

        print(f'Avg Trades split size:{np.mean(trades_split_sizes)}')

    # TODO assertions
    def test_cryptotick_l2_snap_feature_online(self):
        data_params = {}
        feature_params = [{'dep_schema': 'cryptotick'}]
        feature = construct_feature_tree(L2SnapshotFD, data_params, feature_params)
        stream_graph = C.build_stream_graph(feature)
        stream = stream_graph[feature]
        data = Feature([], 0, CryptotickL2BookIncrementalData, data_params)
        sources = {data: stream_graph[data]}
        path = 's3://svoe-cataloged-data/l2_book/BINANCE/spot/BTC-USDT/2023-02-01/cryptotick/100.0mb/1675216068-40f26fdc1fafb2c056fc77f76609049ce0a47944.parquet.gz'
        df = load_df(path)
        merged_events = C.merge_blocks({data: [df]})
        online_res = C.run_stream(merged_events, sources, stream)
        print(online_res)
        print(online_res['asks'].iloc[1000])
        print(len(online_res['asks'].iloc[1000]))
        print(online_res['bids'].iloc[1000])
        print(len(online_res['bids'].iloc[1000]))


    def test_cryptotick_l2_snap_feature_offline(self):
        api = Api()
        l2_data_ranges_meta = api.get_meta('BINANCE', 'l2_book', 'spot', 'BTC-USDT')[0]

        data_def = Feature([], 0, CryptotickL2BookIncrementalData, {})

        feature_params = [{'dep_schema': 'cryptotick'}]
        feature = construct_feature_tree(L2SnapshotFD, {}, feature_params)
        print(RenderTree(feature))
        task_graph = C.build_feature_task_graph({}, feature, {data_def: l2_data_ranges_meta})
        print(task_graph)
        root_nodes = list(task_graph[feature].values())
        res_blocks = C.execute_graph_nodes(root_nodes)
        print(res_blocks)

    def test_cryptotick_midprice_feature_offline(self):
        api = Api()
        l2_data_ranges_meta = api.get_meta('BINANCE', 'l2_book', 'spot', 'BTC-USDT')[0][:10]

        data_def = Feature([], 0, CryptotickL2BookIncrementalData, {})

        feature_params = {1: {'dep_schema': 'cryptotick'}}
        feature = construct_feature_tree(MidPriceFD, {}, feature_params)
        print(RenderTree(feature))
        task_graph = C.build_feature_task_graph({}, feature, {data_def: l2_data_ranges_meta})
        print(task_graph)
        root_nodes = list(task_graph[feature].values())
        res_blocks = C.execute_graph_nodes(root_nodes)
        res = concat(res_blocks)
        res = res.reset_index(drop=True)

        # cache_df_if_needed(res, 'test-1-df')
        # res = get_cached_df('test-1-df')

        # TODO why is this not sorted?
        res = res.sort_values(by=['timestamp'], ignore_index=True)

        fig, axes = plt.subplots(nrows=2, ncols=1)
        res.plot(x='timestamp', y='mid_price', ax=axes[0])

        # compare to cryptotick quotes
        mdf = load_df('s3://svoe-cryptotick-data/quotes/20230201/BINANCE_SPOT_BTC_USDT.csv.gz', extension='csv')

        def _to_ts(s):
            return ciso8601.parse_datetime(f'{s}Z').timestamp()

        mdf['timestamp'] = mdf['time_exchange'].map(lambda x: _to_ts(x))
        mdf['receipt_timestamp'] = mdf['time_coinapi'].map(lambda x: _to_ts(x))

        # for some reason raw cryptotick dates are not sorted
        # don't use inplace=True as it harms perf https://sourcery.ai/blog/pandas-inplace/
        mdf = mdf.sort_values(by=['timestamp'], ignore_index=True)

        mdf = mdf.drop(columns=['time_exchange', 'time_coinapi'])

        last_ts = res.iloc[len(res) - 1]['timestamp']
        first_ts = res.iloc[0]['timestamp']

        mdf = mdf[(mdf['timestamp'] <= last_ts) & (mdf['timestamp'] >= first_ts)]
        mdf['mid_price'] = (mdf['ask_px'] + mdf['bid_px'])/2

        print(len(res), len(mdf))
        mdf.plot(x='timestamp', y='mid_price', ax=axes[1])

        plt.show()

    def test_l2_cryptotick_data(self):
        path = 's3://svoe-cataloged-data/l2_book/BINANCE/spot/BTC-USDT/2023-02-01/cryptotick/100.0mb/1675216068-40f26fdc1fafb2c056fc77f76609049ce0a47944.parquet.gz'
        df = load_df(path)
        print(df)


    def test_feature_label_set_cryptotick(self):
        api = Api()
        l2_data_ranges_meta = api.get_meta('BINANCE', 'l2_book', 'spot', 'BTC-USDT')[0][:10]

        # data_def = Feature([], 0, CryptotickL2BookIncrementalData, {})
        # feature_mid_price = construct_feature_tree(MidPriceFD, {}, {1: {'dep_schema': 'cryptotick'}})
        # feature_volatility = construct_feature_tree(VolatilityStddevFD, {}, {2: {'dep_schema': 'cryptotick'}})
        # flset = C.build_feature_label_set_task_graph([feature_mid_price, feature_volatility], {data_def: l2_data_ranges_meta}, feature_mid_price)
        # res = C.execute_graph_nodes(flset)

        # cache_df_if_needed(concat(res), 'test-2-df')
        res = get_cached_df('test-2-df')

        # TODO why is this not ts sorted? Some values are out of order
        res = res.sort_values(by=['timestamp'], ignore_index=True)

        print(res)
        fig, axes = plt.subplots(nrows=2, ncols=1)
        res.plot(x='timestamp', y='mid_price', ax=axes[0])
        res.plot(x='timestamp', y='volatility', ax=axes[1])
        # plt.show()
        with ray.init(address='auto'):
            # execute dag
            refs = [node.execute() for node in flset]
            ray.wait(refs, num_returns=len(refs))
            dataset = ray.data.from_pandas_refs(refs)
            with enable_dask_on_ray():
                # ddf = dd.from_delayed([ref_to_df([ref]) for ref in refs])
                ddf = dataset.to_dask()
                res = ddf.sample(frac=0.5).compute()
            print(res)



if __name__ == '__main__':
    # unittest.main()
    t = TestFeatureCalculator()
    # t.test_featurization(L2BookSnapshotFeatureDefinition, L2BookDeltasData)
    # t.test_featurization(OHLCVFeatureDefinition, TradesData)
    # t.test_point_in_time_join()
    # t.test_merge_asof()
    # t.test_feature_label_set()
    # t.test_cryptofeed_df_split()
    # t.test_cryptotick_df_split()
    # t.test_cryptotick_l2_snap_feature_online()
    # t.test_cryptotick_l2_snap_feature_offline()
    # t.test_l2_cryptotick_data()
    # t.test_cryptotick_midprice_feature_offline()
    t.test_feature_label_set_cryptotick()


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