import time
import unittest
import ray
import toolz
from matplotlib import pyplot as plt
from ray.air import ScalingConfig
from ray.train.batch_predictor import BatchPredictor
from ray.train.xgboost import XGBoostTrainer, XGBoostPredictor

import featurizer.calculator.calculator as C
from featurizer.actors.cache_actor import CacheActor, CACHE_ACTOR_NAME
from featurizer.api.api import Api, data_key
from featurizer.features.definitions.spread.relative_bid_ask_spread_fd import RelativeBidAskSpreadFD
from featurizer.features.definitions.volatility.volatility_stddev_fd import VolatilityStddevFD

from featurizer.sql.data_catalog.models import DataCatalog
from featurizer.features.definitions.l2_snapshot.l2_snapshot_fd import L2SnapshotFD
from featurizer.features.definitions.mid_price.mid_price_fd import MidPriceFD
from featurizer.features.feature_tree.feature_tree import construct_feature_tree
from utils.pandas.df_utils import sort_dfs, concat, get_cached_df, cache_df_if_needed

from sklearn.metrics import r2_score


class TestXGBoostTrainer(unittest.TestCase):

    def test_xgboost(self):

        api = Api()
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
        ranges_meta_per_data_key = api.get_data_meta(data_keys, start_date=start_date, end_date=end_date)
        data_ranges_meta = {data: ranges_meta_per_data_key[data_key(data.params)] for data in data_deps}

        stored_features_meta = api.get_features_meta(features, start_date=start_date, end_date=end_date)

        cache = {}
        features_to_store = []
        task_graph = C.build_feature_set_task_graph(features, data_ranges_meta, cache, features_to_store,
                                                    stored_features_meta)


        label_feature = feature_mid_price
        joined_task_graph = C.point_in_time_join_dag(task_graph, features, label_feature)
        res = []
        with ray.init(address='auto', ignore_reinit_error=True):
            local_cache_key = 'test_df_2'
            df = get_cached_df(local_cache_key)
            if df is None:
                c = CacheActor.options(name=CACHE_ACTOR_NAME).remote(cache) # assign to unused var so it stays in Ray's scope
                num_ranges = len(joined_task_graph)
                i = 0
                for range_interval in joined_task_graph:
                    nodes = []
                    for interval in joined_task_graph[range_interval]:
                        nodes.append((label_feature, joined_task_graph[range_interval][interval]))
                    print(f'Executing {i + 1}/{num_ranges} range: {range_interval}')
                    r = C.execute_graph_nodes(nodes)
                    dfs = toolz.first(r.values())
                    res.extend(dfs)
                    i += 1
                df = concat(sort_dfs(res))
                # TODO proper remove duplicate columns during merge
                df = df.loc[:, ~df.columns.duplicated()]
                df = df[['volatility', 'mid_price', 'spread', 'timestamp']]
                cache_df_if_needed(df, local_cache_key)
            else:
                print('Test df is cached')

            # TODO first two values are weird outliers for some reason, why?
            df = df.tail(-2)

            df_with_timestamp = df.copy(deep=True)
            df = df.drop(columns=['timestamp'])
            train, valid, test = 0.5, 0.2, 0.3 # weights
            train_df = df.iloc[:int(train*len(df))]
            valid_df = df.iloc[int(train*len(df)): int((train+valid)*len(df))]
            test_df_with_labels = df.iloc[int((train+valid)*len(df)):]
            test_df = test_df_with_labels[['volatility', 'spread']]

            # TODO pass objecs refs instead of copying data between client and cluster
            train_dataset = ray.data.from_pandas(train_df)
            valid_dataset = ray.data.from_pandas(valid_df)
            test_dataset = ray.data.from_pandas(test_df)

            params = {
                'tree_method': 'approx',
                'objective': 'reg:linear',
                'eval_metric': ['logloss', 'error'],
            }
            num_workers = 10
            trainer = XGBoostTrainer(
                scaling_config=ScalingConfig(num_workers=num_workers, use_gpu=False),
                label_column='mid_price',
                params=params,
                # TODO re what valid is used for
                # https://www.kaggle.com/questions-and-answers/61835
                datasets={'train': train_dataset, 'valid': valid_dataset},
                # preprocessor=preprocessor, # TODO scale features?
                num_boost_round=500,
            )
            result = trainer.fit()
            print(result.metrics)

            predictor = XGBoostPredictor.from_checkpoint(result.checkpoint)
            t = time.time()
            predicted_one = predictor.predict(test_df.head(1))
            print(f'Predict one in {time.time() - t}s')

            batch_predictor = BatchPredictor.from_checkpoint(
                result.checkpoint, XGBoostPredictor
            )
            t = time.time()
            predicted_labels = batch_predictor.predict(test_dataset)
            print(f'Predict in {time.time() - t}s')

            predicted = list(map(lambda e: e['predictions'], predicted_labels.take_all()))
            actual = test_df_with_labels['mid_price'].values.tolist()
            test_df_with_labels['predicted_mid_price'] = predicted
            test_df_with_labels['timestamp'] = df_with_timestamp['timestamp']
            r2 = r2_score(actual, predicted)
            print(r2)

            # fig, axes = plt.subplots(nrows=1, ncols=1)
            test_df_with_labels.plot(x='timestamp', y=['mid_price', 'predicted_mid_price'])
            plt.show()
            # predicted_labels.show()

            # shap_values = batch_predictor.predict(test_dataset, pred_contribs=True)
            # print(f'SHAP VALUES')
            # shap_values.show()


if __name__ == '__main__':
    # unittest.main()
    t = TestXGBoostTrainer()
    t.test_xgboost()