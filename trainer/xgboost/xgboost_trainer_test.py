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

            train_ds, valid_ds, test_ds = ray.data.from_pandas_refs(refs).split_proportionately([0.5, 0.2])
            params = {
                'tree_method': 'approx',
                'objective': 'reg:linear',
                'eval_metric': ['logloss', 'error'],
            }

            label_column = 'label_mid_price' # TODO get dynamically
            num_workers = 10
            trainer = XGBoostTrainer(
                scaling_config=ScalingConfig(num_workers=num_workers, use_gpu=False),
                label_column=label_column,
                params=params,
                # TODO re what valid is used for
                # https://www.kaggle.com/questions-and-answers/61835
                datasets={
                    'train': train_ds.drop_columns(cols=['timestamp', 'receipt_timestamp']),
                    'valid': valid_ds.drop_columns(cols=['timestamp', 'receipt_timestamp'])
                },
                # preprocessor=preprocessor, # TODO scale features? XGBoost does not need scaling
                num_boost_round=100,
            )
            result = trainer.fit()
            print(result.metrics)

            # predictor = XGBoostPredictor.from_checkpoint(result.checkpoint)
            # t = time.time()
            # predicted_one = predictor.predict(pd.DataFrame(test_ds.take(1)).drop(columns=[label_column]))
            # print(f'Predict one in {time.time() - t}s')

            batch_predictor = BatchPredictor.from_checkpoint(
                result.checkpoint, XGBoostPredictor
            )
            t = time.time()
            predicted_labels = batch_predictor.predict(
                test_ds.drop_columns(cols=[label_column, 'timestamp', 'receipt_timestamp'])
            )

            print(f'Predict in {time.time() - t}s')

            p = test_ds.zip(predicted_labels).to_pandas()
            p = p.tail(-2)
            p = p.head(10)
            p.plot(x='timestamp', y=['mid_price', 'label_mid_price', 'predictions'])
            plt.show()
            # print(predicted_labels)
            # print(test_ds)
            # actual = test_ds.take_all()
            # print(actual)
            #
            # predicted = list(map(lambda e: e['predictions'], predicted_labels.take_all()))
            # print(predicted)
            # actual['predicted'] = predicted
            #
            # print(actual)

            # print(predicted)
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