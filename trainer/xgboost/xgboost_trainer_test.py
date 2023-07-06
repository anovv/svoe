import time
import unittest
from typing import Dict, Any

import numpy as np
import ray
from matplotlib import pyplot as plt
from ray.air import ScalingConfig, RunConfig
from ray.train.batch_predictor import BatchPredictor
from ray.train.xgboost import XGBoostTrainer, XGBoostPredictor
from ray.tune import Tuner, TuneConfig

from featurizer.runner import Featurizer

from sklearn.metrics import mean_squared_error, mean_absolute_error

def _xgboost_trainer(label: str, datesets: Dict[str, Any]) -> XGBoostTrainer:
    num_workers = 1
    trainer = XGBoostTrainer(
        scaling_config=ScalingConfig(num_workers=num_workers, use_gpu=False),
        label_column=label,
        params={
            'tree_method': 'approx',
            'objective': 'reg:linear',
            'eval_metric': ['logloss', 'error'],
        },
        # TODO re what valid is used for
        # https://www.kaggle.com/questions-and-answers/61835
        datasets=datesets,
        # preprocessor=preprocessor, # XGBoost does not need feature scaling
        num_boost_round = 100,
    )
    return trainer


class TestXGBoostTrainer(unittest.TestCase):

    # TODO for hp tuning https://docs.ray.io/en/latest/ray-air/examples/analyze_tuning_results.html
    def test_xgboost(self):
        config_path = '/Users/anov/IdeaProjects/svoe/featurizer/test_configs/feature-label-set.yaml'
        # Featurizer.run(config_path)

        with ray.init(address='auto', ignore_reinit_error=True):
            refs = Featurizer.get_result_refs()

            train_ds, valid_ds, test_ds = ray.data.from_pandas_refs(refs).split_proportionately([0.5, 0.2])

            xgboost_datasets = {
                'train': train_ds.drop_columns(cols=['timestamp', 'receipt_timestamp']),
                'valid': valid_ds.drop_columns(cols=['timestamp', 'receipt_timestamp'])
            }

            label_column = 'label_mid_price' # TODO get dynamically
            trainer = _xgboost_trainer(label_column, xgboost_datasets)
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
            # TODO first two values are weird outliers for some reason, why?
            p = p.tail(-2)

            mse = mean_squared_error(p['label_mid_price'], p['predictions'])
            rmse = np.sqrt(mse)
            mae = mean_absolute_error(p['label_mid_price'], p['predictions'])
            print(f'MSE: {mse}, RMSE: {rmse}, MAE: {mae}')

            p = p.head(200)
            # p.plot(x='timestamp', y=['mid_price', 'label_mid_price', 'predictions'])
            p.plot(x='timestamp', y=['label_mid_price', 'predictions'])
            plt.show()

    def test_tuner(self):
        config_path = '/Users/anov/IdeaProjects/svoe/featurizer/test_configs/feature-label-set.yaml'
        # Featurizer.run(config_path)

        with ray.init(address='auto', ignore_reinit_error=True):
            refs = Featurizer.get_result_refs()

            train_ds, valid_ds, test_ds = ray.data.from_pandas_refs(refs).split_proportionately([0.5, 0.2])

            xgboost_datasets = {
                'train': train_ds.drop_columns(cols=['timestamp', 'receipt_timestamp']),
                'valid': valid_ds.drop_columns(cols=['timestamp', 'receipt_timestamp'])
            }

            label_column = 'label_mid_price' # TODO get dynamically
            trainer = _xgboost_trainer(label_column, xgboost_datasets)

            tuner = Tuner(
                trainer,
                run_config=RunConfig(verbose=1),
                param_space={
                    'params': {
                        'max_depth': ray.tune.randint(2, 8),
                        'min_child_weight': ray.tune.randint(1, 10),
                    },
                },
                tune_config=TuneConfig(num_samples=8, metric='train-logloss', mode='min'),
            )

            results = tuner.fit()
            best_result = results.get_best_result()
            print('Best result error rate', best_result.metrics['train-error'])
            df = results.get_dataframe()
            print(df)


if __name__ == '__main__':
    t = TestXGBoostTrainer()
    t.test_tuner()