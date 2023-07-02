import ray
import toolz
from portion import closed

import calculator as C
import utils.streamz.stream_utils
from featurizer.actors.cache_actor import create_cache_actor
from featurizer.calculator.executor import execute_graph
from featurizer.calculator.tasks import merge_blocks
from featurizer.storage.featurizer_storage import FeaturizerStorage, data_key
from featurizer.data_definitions.l2_book_incremental.cryptotick.cryptotick_l2_book_incremental import CryptotickL2BookIncrementalData
from featurizer.features.definitions.spread.relative_bid_ask_spread_fd.relative_bid_ask_spread_fd import RelativeBidAskSpreadFD
from featurizer.features.definitions.tvi.trade_volume_imb_fd.trade_volume_imb_fd import TradeVolumeImbFD
from featurizer.features.definitions.volatility.volatility_stddev_fd.volatility_stddev_fd import VolatilityStddevFD

from featurizer.sql.data_catalog.models import DataCatalog
from featurizer.features.definitions.l2_book.l2_snapshot_fd.l2_snapshot_fd import L2SnapshotFD
from featurizer.features.definitions.mid_price.mid_price_fd.mid_price_fd import MidPriceFD
from featurizer.features.feature_tree.feature_tree import construct_feature_tree, Feature

import unittest
import pandas as pd
from typing import List
from featurizer.featurizer_utils.testing_utils import mock_feature, mock_ts_df_remote
from utils.pandas.df_utils import concat, load_df, sort_dfs, plot_multi
from featurizer.blocks.blocks import merge_asof_multi


class TestFeatureCalculator(unittest.TestCase):

    def test_point_in_time_join(self):
        label_feature = mock_feature(1)
        dag = {
            label_feature: {
                closed(0, 21.01): {
                    closed(0, 5.01): mock_ts_df_remote.bind([4], 'a', ['a0']),
                    closed(5.02, 11.01): mock_ts_df_remote.bind([7, 10], 'a', ['a1', 'a2']),
                    closed(11.02, 15.01): mock_ts_df_remote.bind([14], 'a', ['a3']),
                    closed(15.02, 18.01): mock_ts_df_remote.bind([16], 'a', ['a4']),
                    closed(18.02, 21.01): mock_ts_df_remote.bind([20], 'a', ['a5']),
                }
            },
            mock_feature(2): {
                closed(0, 21.01): {
                    closed(0, 9.01): mock_ts_df_remote.bind([2, 5, 6, 8], 'b', ['b0', 'b1', 'b2', 'b3']),
                    closed(9.02, 17.01): mock_ts_df_remote.bind([11, 12], 'b', ['b4', 'b5']),
                    closed(17.02, 21.01): mock_ts_df_remote.bind([18], 'b', ['b6'])
                }
            },
            mock_feature(3): {
                closed(0, 21.01): {
                    closed(0, 4.01): mock_ts_df_remote.bind([1, 3], 'c', ['c0', 'c1']),
                    closed(4.02, 21.01): mock_ts_df_remote.bind([7, 10, 19], 'c', ['c2', 'c3', 'c4']),
                }
            },
        }

        # distributed
        nodes = C.point_in_time_join_dag(dag, list(dag.keys()), label_feature)
        with ray.init(address='auto'):
            # execute dag
            nodes_flattened = []
            for range_interval in nodes:
                nodes_flattened.extend(list(nodes[range_interval].values()))
            res = ray.get([node.execute() for node in nodes_flattened])
            res_ray = concat(res)
            print(res_ray)

        # sequential
        with ray.init(address='auto'):
            dfs = []
            for feature in dag:
                nodes_flattened = []
                # TODO is this correct for different/many range_intervals?
                for range_interval in dag[feature]:
                    nodes_flattened.extend(list(dag[feature][range_interval].values()))
                nodes_res_dfs = ray.get([node.execute() for node in nodes_flattened])
                dfs.append(concat(nodes_res_dfs))
            res_seq = merge_asof_multi(dfs)
            print(res_seq)

        assert res_ray.equals(res_seq)
        # TODO add tests for different ranges per feature

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
        storage = FeaturizerStorage()
        feature_params1 = {0: {'dep_schema': 'cryptotick', 'sampling': '1s'}}
        feature_params2 = {1: {'dep_schema': 'cryptotick', 'sampling': '1s'}}
        feature_params3 = {2: {'dep_schema': 'cryptotick', 'sampling': '1s'}}
        feature_params4 = {1: {'dep_schema': 'cryptotick', 'sampling': '1s'}}
        data_params = [
            {DataCatalog.exchange.name: 'BINANCE',
            DataCatalog.data_type.name: 'l2_book',
            DataCatalog.instrument_type.name: 'spot',
            DataCatalog.symbol.name: 'BTC-USDT'}
        ]
        feature_l2_snap = construct_feature_tree(L2SnapshotFD, data_params, feature_params1)
        feature_mid_price = construct_feature_tree(MidPriceFD, data_params, feature_params2)
        feature_volatility = construct_feature_tree(VolatilityStddevFD, data_params, feature_params3)
        feature_spread = construct_feature_tree(RelativeBidAskSpreadFD, data_params, feature_params4)
        features = [feature_l2_snap, feature_mid_price, feature_volatility, feature_spread]
        # features = [feature_mid_price]
        data_deps = set()
        for feature in features:
            for d in feature.get_data_deps():
                data_deps.add(d)
        data_keys = [data_key(d.params) for d in data_deps]
        start_date = '2023-02-01'
        end_date = '2023-02-01'
        ranges_meta_per_data_key = storage.get_data_meta(data_keys, start_date=start_date, end_date=end_date)
        data_ranges_meta = {data: ranges_meta_per_data_key[data_key(data.params)] for data in data_deps}

        stored_features_meta = storage.get_features_meta(features, start_date=start_date, end_date=end_date)

        cache = {}
        features_to_store = []
        task_graph = C.build_feature_set_task_graph(features, data_ranges_meta, cache, features_to_store, stored_features_meta)
        label_feature = feature_mid_price
        joined_task_graph = C.point_in_time_join_dag(task_graph, features, label_feature)
        with ray.init(address='auto', ignore_reinit_error=True):
            create_cache_actor(cache)
            refs = execute_graph(joined_task_graph)
            df = concat(ray.get(refs))

            # TODO first value (or two) is weird outlier for some reason, why?
            df = df.tail(-1)

        plot_multi(['mid_price', 'volatility', 'spread'], df)

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

    def test_tvi(self):

        # df = load_df('s3://svoe-cataloged-data/trades/BINANCE/spot/BTC-USDT/cryptotick/100.0mb/2023-02-01/1675209965-4ea8eeea78da2f99f312377c643e6b491579f852.parquet.gz')
        # print(df.head())
        # raise

        storage = FeaturizerStorage()
        feature_params1 = {0: {'window': '1m', 'sampling': '1s'}}
        feature_params2 = {1: {'dep_schema': 'cryptotick', 'sampling': '1s'}}
        feature_params3 = {2: {'dep_schema': 'cryptotick', 'sampling': '1s'}}
        data_params1 = [
            {DataCatalog.exchange.name: 'BINANCE',
             DataCatalog.data_type.name: 'trades',
             DataCatalog.instrument_type.name: 'spot',
             DataCatalog.symbol.name: 'BTC-USDT'}
        ]
        data_params2 = [
            {DataCatalog.exchange.name: 'BINANCE',
             DataCatalog.data_type.name: 'l2_book',
             DataCatalog.instrument_type.name: 'spot',
             DataCatalog.symbol.name: 'BTC-USDT'}
        ]
        feature_mid_price = construct_feature_tree(MidPriceFD, data_params2, feature_params2)
        feature_volatility = construct_feature_tree(VolatilityStddevFD, data_params2, feature_params3)
        feature_tvi = construct_feature_tree(TradeVolumeImbFD, data_params1, feature_params1)
        # print(RenderTree(feature_tvi))
        # features = [feature_mid_price, feature_tvi, feature_volatility]
        features = [feature_mid_price, feature_tvi]
        data_deps = set()
        for feature in features:
            for d in feature.get_data_deps():
                data_deps.add(d)
        data_keys = [data_key(d.params) for d in data_deps]
        print(data_keys)
        start_date = '2023-02-01'
        end_date = '2023-02-01'
        ranges_meta_per_data_key = storage.get_data_meta(data_keys, start_date=start_date, end_date=end_date)
        data_ranges_meta = {data: ranges_meta_per_data_key[data_key(data.params)] for data in data_deps}

        stored_features_meta = storage.get_features_meta(features, start_date=start_date, end_date=end_date)

        cache = {}
        features_to_store = [feature_tvi]
        task_graph = C.build_feature_set_task_graph(features, data_ranges_meta, cache, features_to_store,
                                                    stored_features_meta)

        label_feature = feature_mid_price
        joined_task_graph = C.point_in_time_join_dag(task_graph, features, label_feature)
        with ray.init(address='auto', ignore_reinit_error=True):
            create_cache_actor(cache)  # assign to unused var so it stays in Ray's scope
            refs = execute_graph(joined_task_graph)
            df = concat(ray.get(refs))

            # TODO first two values are weird outliers for some reason, why?
            df = df.tail(-2)

        plot_multi(['mid_price', 'tvi'], df)

    def test_lookahead_shift(self):
        lookahead = '3s'

        def _mock_df(ts: List[float], vals: List[float], col_name: str):
            return pd.DataFrame({'timestamp': ts, col_name: vals})

        @ray.remote
        def mock_df(ts: List[float], vals: List[float], col_name: str):
            return _mock_df(ts, vals, col_name)

        data = [[1, 2, 3, 5], [8, 9, 20, 21], [22, 23, 28], [31, 32, 33, 34, 40], [41, 42, 46], [47, 48]]


        expected_res = [
            _mock_df(data[0], [3, 5, 5, 8], 'label_vals'),
            _mock_df(data[1], [9, 9, 23, 23], 'label_vals'),
            _mock_df(data[2], [23, 23, 31], 'label_vals'),
            _mock_df(data[3], [34, 34, 34, 34, 42], 'label_vals'),
            _mock_df([41, 42], [42, 42], 'label_vals')
        ]

        input_dag = {}
        range_interval = closed(data[0][0], data[-1][-1])
        nodes = {}
        for ts in data:
            interval = closed(ts[0], ts[-1])
            node = mock_df.bind(ts, ts, 'vals')
            nodes[interval] = node

        input_dag[range_interval] = nodes

        lookahead_graph = C.build_lookahead_graph(input_dag, lookahead)

        with ray.init(address='auto', ignore_reinit_error=True):
            refs = execute_graph(lookahead_graph)
            res = ray.get(refs)

            print(len(res))
            print(len(expected_res))
            print(res)
            print(expected_res)
            assert len(res) == len(expected_res)
            for i in range(len(res)):
                assert res[i].reset_index(drop=True).equals(expected_res[i].reset_index(drop=True))

    def test_feature_label_set(self):

        storage = FeaturizerStorage()

        feature_params1 = {1: {'dep_schema': 'cryptotick', 'sampling': '1s'}}
        feature_params2 = {2: {'dep_schema': 'cryptotick', 'sampling': '1s'}}
        data_params = [
            {DataCatalog.exchange.name: 'BINANCE',
             DataCatalog.data_type.name: 'l2_book',
             DataCatalog.instrument_type.name: 'spot',
             DataCatalog.symbol.name: 'BTC-USDT'}
        ]

        feature_mid_price = construct_feature_tree(MidPriceFD, data_params, feature_params1)
        feature_volatility = construct_feature_tree(VolatilityStddevFD, data_params, feature_params2)

        features = [feature_mid_price, feature_volatility]
        data_deps = set()
        for feature in features:
            for d in feature.get_data_deps():
                data_deps.add(d)
        data_keys = [data_key(d.params) for d in data_deps]
        print(data_keys)
        start_date = '2023-02-01'
        end_date = '2023-02-01'
        ranges_meta_per_data_key = storage.get_data_meta(data_keys, start_date=start_date, end_date=end_date)
        data_ranges_meta = {data: ranges_meta_per_data_key[data_key(data.params)] for data in data_deps}

        # stored_features_meta = api.get_features_meta(features, start_date=start_date, end_date=end_date)

        cache = {}
        label_feature = feature_mid_price
        dag = C.build_feature_label_set_task_graph(
            features=features,
            label=label_feature,
            label_lookahead='4s',
            data_ranges_meta=data_ranges_meta,
            obj_ref_cache={}
        )

        with ray.init(address='auto', ignore_reinit_error=True):
            create_cache_actor(cache)  # assign to unused var, so it stays in Ray's scope
            refs = execute_graph(dag)
            df = concat(ray.get(refs))
            print(df.head())
            print(df.tail())
            # for name in ['mid_price', 'label_mid_price', 'volatility']:
            #     df.plot('timestamp', name, label=name)
            #
            # plt.show()

    def test_remote_tvi(self):
        storage = FeaturizerStorage()
        feature_params1 = {0: {'window': '1m', 'sampling': '1s'}}
        data_params1 = [
            {DataCatalog.exchange.name: 'BINANCE',
             DataCatalog.data_type.name: 'trades',
             DataCatalog.instrument_type.name: 'spot',
             DataCatalog.symbol.name: 'BTC-USDT'}
        ]
        feature_tvi = construct_feature_tree('tvi.trade_volume_imb_fd', data_params1, feature_params1)
        # print(RenderTree(feature_tvi))
        # features = [feature_mid_price, feature_tvi, feature_volatility]
        features = [feature_tvi]
        data_deps = set()
        for feature in features:
            for d in feature.get_data_deps():
                data_deps.add(d)
        data_keys = [data_key(d.params) for d in data_deps]
        print(data_keys)
        start_date = '2023-02-01'
        end_date = '2023-02-01'
        ranges_meta_per_data_key = storage.get_data_meta(data_keys, start_date=start_date, end_date=end_date)
        data_ranges_meta = {data: ranges_meta_per_data_key[data_key(data.params)] for data in data_deps}

        stored_features_meta = storage.get_features_meta(features, start_date=start_date, end_date=end_date)

        cache = {}
        # features_to_store = [feature_tvi]
        features_to_store = []
        task_graph = C.build_feature_set_task_graph(features, data_ranges_meta, cache, features_to_store,
                                                    stored_features_meta)
        print(task_graph)


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
    # t.test_cryptotick_midprice_feature_offline()
    # t.test_tvi()
    # t.test_feature_label_set_cryptotick()
    # t.test_lookahead_shift()
    # t.test_feature_label_set()
    t.test_remote_tvi()
