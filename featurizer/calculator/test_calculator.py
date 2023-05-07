import shutil
import time

import numpy as np
import ray
from portion import closed
from ray.util.dask import enable_dask_on_ray
import matplotlib.pyplot as plt

import calculator as C
import utils.streamz.stream_utils
from featurizer.calculator.tasks import merge_blocks
from featurizer.data_catalog.api.api import Api, data_key
from featurizer.data_definitions.data_source_definition import DataSourceDefinition
from featurizer.data_definitions.l2_book_incremental.cryptofeed.cryptofeed_l2_book_incremental import CryptofeedL2BookIncrementalData
from featurizer.data_definitions.l2_book_incremental.cryptotick.cryptotick_l2_book_incremental import CryptotickL2BookIncrementalData
from featurizer.data_definitions.trades.trades import TradesData

from featurizer.data_catalog.common.sql.models import DataCatalog
from featurizer.features.definitions.l2_snapshot.l2_snapshot_fd import L2SnapshotFD
from featurizer.features.definitions.mid_price.mid_price_fd import MidPriceFD
from featurizer.features.definitions.volatility.volatility_stddev_fd import VolatilityStddevFD
from featurizer.features.definitions.feature_definition import FeatureDefinition
from featurizer.features.feature_tree.feature_tree import construct_feature_tree, Feature

import unittest
import pandas as pd
from typing import Type
from anytree import RenderTree
from featurizer.utils.testing_utils import mock_feature, mock_trades_data_and_meta, mock_l2_book_delta_data_and_meta, mock_ts_df, mock_ts_df_remote
from utils.pandas.df_utils import concat, load_df, get_size_kb, gen_split_df_by_mem, get_cached_df


class TestFeatureCalculator(unittest.TestCase):

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

    # TODO assertions
    def test_cryptotick_l2_snap_feature_online(self):
        data_params = {}
        feature_params = [{'dep_schema': 'cryptotick'}]
        feature = construct_feature_tree(L2SnapshotFD, data_params, feature_params)
        stream_graph = feature.build_stream_graph()
        stream = stream_graph[feature]
        data = Feature([], 0, CryptotickL2BookIncrementalData, data_params)
        sources = {data: stream_graph[data]}
        path = 's3://svoe-cataloged-data/l2_book/BINANCE/spot/BTC-USDT/2023-02-01/cryptotick/100.0mb/1675216068-40f26fdc1fafb2c056fc77f76609049ce0a47944.parquet.gz'
        df = load_df(path)
        merged_events = merge_blocks({data: [df]})
        online_res = utils.streamz.stream_utils.run_named_events_stream(merged_events, sources, stream)
        print(online_res)
        print(online_res['asks'].iloc[1000])
        print(len(online_res['asks'].iloc[1000]))
        print(online_res['bids'].iloc[1000])
        print(len(online_res['bids'].iloc[1000]))


    def test_cryptotick_midprice_feature_offline(self):
        api = Api()
        # l2_data_ranges_meta = api.get_meta('BINANCE', 'l2_book', 'spot', 'BTC-USDT')[0][:10]

        # data_def = Feature([], 0, CryptotickL2BookIncrementalData, {})

        feature_params = {1: {'dep_schema': 'cryptotick'}}
        data_params = {
            0: {DataCatalog.exchange.name: 'BINANCE',
                DataCatalog.data_type.name: 'l2_book',
                DataCatalog.instrument_type.name: 'spot',
                DataCatalog.symbol.name: 'BTC-USDT'}}
        # feature_params1 = {1: {'dep_schema': 'cryptotick', 'sampling': '1s'}}
        feature = construct_feature_tree(MidPriceFD, data_params, feature_params)
        data_deps = feature.get_data_deps()
        data_keys = [data_key(d.params) for d in data_deps]
        ranges_meta = api.get_meta_from_data_keys(data_keys, start_date='2023-02-01', end_date='2023-02-01')
        # ranges_meta = api.get_meta_from_data_keys(data_keys, None, None)
        data_ranges_meta = {}
        for interval in ranges_meta:
            range_meta = ranges_meta[interval]
            data_ranges_meta[interval] = {data: range_meta[data_key(data.params)] for data in data_deps}

        results = []
        i = 0
        for interval in data_ranges_meta:
            task_graph = C.build_feature_task_graph({}, feature, data_ranges_meta[interval])
            root_nodes = list(task_graph[feature].values())
            i += 1
            print(f'Executing interval {i}/{len(data_ranges_meta)} {interval}')
            res_blocks = C.execute_graph_nodes(root_nodes)
            results.append(res_blocks)

        print(results)


        # TODO why is this not sorted?
        # res = res.sort_values(by=['timestamp'], ignore_index=True)

        # fig, axes = plt.subplots(nrows=4, ncols=1)
        # res.plot(x='timestamp', y='mid_price', ax=axes[0])
        # res.plot(x='timestamp', y='mid_price')

        # compare to cryptotick quotes
        # mdf = load_df('s3://svoe-cryptotick-data/quotes/20230201/BINANCE_SPOT_BTC_USDT.csv.gz', extension='csv')
        #
        # def _to_ts(s):
        #     return ciso8601.parse_datetime(f'{s}Z').timestamp()
        #
        # mdf['timestamp'] = mdf['time_exchange'].map(lambda x: _to_ts(x))
        # mdf['receipt_timestamp'] = mdf['time_coinapi'].map(lambda x: _to_ts(x))
        #
        # # for some reason raw cryptotick dates are not sorted
        # # don't use inplace=True as it harms perf https://sourcery.ai/blog/pandas-inplace/
        # mdf = mdf.sort_values(by=['timestamp'], ignore_index=True)
        #
        # mdf = mdf.drop(columns=['time_exchange', 'time_coinapi'])
        #
        # last_ts = res.iloc[len(res) - 1]['timestamp']
        # first_ts = res.iloc[0]['timestamp']
        #
        # mdf = mdf[(mdf['timestamp'] <= last_ts) & (mdf['timestamp'] >= first_ts)]
        # mdf['mid_price'] = (mdf['ask_px'] + mdf['bid_px'])/2
        #
        # print(len(res), len(mdf))
        # mdf.plot(x='timestamp', y='mid_price', ax=axes[1])
        #
        # plt.show()


    # def test_feature_label_set(self):
    #     block_range, block_range_meta = mock_l2_book_delta_data_and_meta()
    #     data_params = {}
    #     feature_params = {}
    #     feature_mid_price = construct_feature_tree(MidPriceFD, data_params, feature_params)
    #     feature_volatility = construct_feature_tree(VolatilityStddevFD, data_params, feature_params)
    #     flset = C.build_feature_label_set_task_graph([feature_mid_price, feature_volatility], block_range_meta, feature_mid_price)
    #     # TODO execute

    # TODO deprecate this
    def test_featurization_DEPRECATED(self, feature_def: Type[FeatureDefinition], data_def: Type[DataSourceDefinition]):
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
        # res_blocks = C.execute_task_graph(task_graph, feature)
        res_blocks = [] # TODO execute
        offline_res = pd.concat(res_blocks)
        print(offline_res)

        # calculate online
        stream_graph = feature.build_stream_graph()
        stream = stream_graph[feature]
        sources = {data: stream_graph[data] for data in block_range_meta.keys()}
        merged_events = merge_blocks(block_range)
        online_res = utils.streamz.stream_utils.run_named_events_stream(merged_events, sources, stream)
        print(online_res)

        # TODO we may have 1ts duplicate entry (due to snapshot_ts based block partition of l2_delta data source)
        # assert_frame_equal(offline_res, online_res)


if __name__ == '__main__':
    # unittest.main()
    t = TestFeatureCalculator()
    # t.test_featurization(L2BookSnapshotFeatureDefinition, L2BookDeltasData)
    # t.test_featurization(OHLCVFeatureDefinition, TradesData)
    # t.test_point_in_time_join()
    # t.test_merge_asof()
    # t.test_feature_label_set()
    # t.test_cryptotick_l2_snap_feature_online()
    # t.test_cryptotick_l2_snap_feature_offline()
    # t.test_l2_cryptotick_data()
    t.test_cryptotick_midprice_feature_offline()
    # t.test_feature_label_set_cryptotick()


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