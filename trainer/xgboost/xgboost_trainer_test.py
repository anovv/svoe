import time
import unittest

import pandas as pd
import ray
import toolz
from matplotlib import pyplot as plt
from ray.air import ScalingConfig
from ray.train.batch_predictor import BatchPredictor
from ray.train.xgboost import XGBoostTrainer, XGBoostPredictor

from featurizer.actors.cache_actor import get_cache_actor
from featurizer.features.feature_tree.feature_tree import construct_feature_tree
from featurizer.runner import Featurizer
from utils.pandas.df_utils import sort_dfs, concat, get_cached_df, cache_df_if_needed

from sklearn.metrics import r2_score


class TestXGBoostTrainer(unittest.TestCase):

    # TODO for hp tuning https://docs.ray.io/en/latest/ray-air/examples/analyze_tuning_results.html
    def test_xgboost(self):
        config_path = '/Users/anov/IdeaProjects/svoe/featurizer/test_configs/feature-label-set.yaml'
        # Featurizer.run(config_path)

        with ray.init(address='auto', ignore_reinit_error=True):
            refs = Featurizer.get_result_refs()
            # TODO first two values are weird outliers for some reason, why?
            # df = df.tail(-2)
            # df_with_timestamp = df.copy(deep=True)
            # df = df.drop(columns=['timestamp'])
            # train, valid, test = 0.5, 0.2, 0.3 # weights
            # train_df = df.iloc[:int(train*len(df))]
            # valid_df = df.iloc[int(train*len(df)): int((train+valid)*len(df))]
            # test_df_with_labels = df.iloc[int((train+valid)*len(df)):]
            # test_df = test_df_with_labels[['volatility', 'spread']]
            #
            # train_dataset = ray.data.from_pandas(train_df)
            # valid_dataset = ray.data.from_pandas(valid_df)
            # test_dataset = ray.data.from_pandas(test_df)


            ds = ray.data.from_pandas_refs(refs)
            ds = ds.drop_columns(cols=['timestamp', 'receipt_timestamp'])
            train_ds, valid_ds, test_ds = ds.split_proportionately([0.5, 0.2])
            params = {
                'tree_method': 'approx',
                'objective': 'reg:linear',
                'eval_metric': ['logloss', 'error'],
            }

            label_column = 'label_mid_price' # TODO get dynamically

            # print(train_ds.take_all())
            # print(valid_ds.take_all())
            # print(test_ds.take_all())
            # raise

            num_workers = 10
            trainer = XGBoostTrainer(
                scaling_config=ScalingConfig(num_workers=num_workers, use_gpu=False),
                label_column=label_column,
                params=params,
                # TODO re what valid is used for
                # https://www.kaggle.com/questions-and-answers/61835
                datasets={'train': train_ds, 'valid': valid_ds},
                # preprocessor=preprocessor, # TODO scale features?
                num_boost_round=5000,
            )
            result = trainer.fit()
            print(result.metrics)

            predictor = XGBoostPredictor.from_checkpoint(result.checkpoint)
            t = time.time()
            predicted_one = predictor.predict(pd.DataFrame(test_ds.take(1)).drop(columns=[label_column]))
            # predicted_one = predictor.predict(test_ds.limit(1))
            print(f'Predict one in {time.time() - t}s')

            batch_predictor = BatchPredictor.from_checkpoint(
                result.checkpoint, XGBoostPredictor
            )
            t = time.time()
            predicted_labels = batch_predictor.predict(test_ds.drop_columns(cols=[label_column]))
            print(f'Predict in {time.time() - t}s')

            predicted = list(map(lambda e: e['predictions'], predicted_labels.take_all()))
            # actual = test_df_with_labels['mid_price'].values.tolist()
            # test_df_with_labels['predicted_mid_price'] = predicted
            # test_df_with_labels['timestamp'] = df_with_timestamp['timestamp']
            # r2 = r2_score(actual, predicted)
            # print(r2)

            # fig, axes = plt.subplots(nrows=1, ncols=1)
            # test_df_with_labels.plot(x='timestamp', y=['mid_price', 'predicted_mid_price'])
            # plt.show()
            # predicted_labels.show()

            # shap_values = batch_predictor.predict(test_dataset, pred_contribs=True)
            # print(f'SHAP VALUES')
            # shap_values.show()


if __name__ == '__main__':
    # unittest.main()
    t = TestXGBoostTrainer()
    t.test_xgboost()