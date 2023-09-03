from typing import Optional, Dict, Any

from pydantic import BaseModel
from ray.air import ScalingConfig, RunConfig
from ray.air.integrations.mlflow import MLflowLoggerCallback
from ray.train.base_trainer import BaseTrainer
from ray.train.xgboost import XGBoostTrainer

from featurizer.runner import Featurizer


class XGBoostParams(BaseModel):
    num_boost_rounds: int
    params: Dict[str, Any]


class TunerConfig(BaseModel):
    param_space: Dict
    num_samples: Optional[int] = 1
    metric: str
    mode: str
    max_concurrent_trials: Optional[int] = 1
    time_budget_s: int
    search_alg: Optional[str] = None
    scheduler: Optional[str] = None


class TrainerConfig(BaseModel):
    user_id: str
    xgboost_params: Optional[XGBoostParams]
    num_workers: int
    tuner_config: Optional[TunerConfig]


class TrainerManager:

    def __init__(self, config: TrainerConfig, ray_address: str):
        self.requires_tuner = TrainerManager._validate_config(config)
        self.trainer_config = config
        # TODO verify config here ?
        self.ray_address = ray_address
        pass

    @classmethod
    def _validate_config(cls, config: TrainerConfig) -> bool:
        required_params = ['xgboost_params', 'pytorch_params']
        config_args_keys = list(config.__dict__.keys())
        intersect = list(set(required_params).intersection(set(config_args_keys)))
        if len(intersect) != 1:
            raise ValueError(f'Tuner config should have exactly one of {required_params} fields')

        requires_tuner = config.tuner_config is not None
        return requires_tuner

    def build_trainer(self) -> BaseTrainer:
        if self.trainer_config.xgboost_params is not None:
            return self._build_xgboost_trainer()
        else:
            raise ValueError('Unknown trainer type')

    def _build_xgboost_trainer(self) -> XGBoostTrainer:
        ds = Featurizer.get_dataset()

        # TODO get proportion from config
        train_ds, valid_ds, test_ds = ds.split_proportionately([0.5, 0.2])

        xgboost_datasets = {
            'train': train_ds.drop_columns(cols=['timestamp', 'receipt_timestamp']),
            'valid': valid_ds.drop_columns(cols=['timestamp', 'receipt_timestamp'])
        }
        label_column = '' #TODO infer from Featurizers metadata
        trainer = XGBoostTrainer(
            scaling_config=ScalingConfig(num_workers=self.trainer_config.num_workers, use_gpu=False),
            label_column=label_column,
            params=self.trainer_config.xgboost_params.params,
            run_config=RunConfig(
                name='test-run-1', # TODO proper name
                verbose=1,
                callbacks=[MLflowLoggerCallback(
                    tracking_uri='http://mlflow.mlflow.svc:5000',
                    experiment_name='test-experiment-2',
                    tags={'test-tag-key': 'test-tag-value'},
                    save_artifact=True)]
            ),
            # TODO re what valid is used for
            # https://www.kaggle.com/questions-and-answers/61835
            datasets=xgboost_datasets,
            # preprocessor=preprocessor, # XGBoost does not need feature scaling
            num_boost_round=self.trainer_config.xgboost_params.num_boost_rounds,
        )
        return trainer


    def run(self):
        pass

