import time
from typing import Type

import numpy as np
import requests
from ray import serve
from ray.air import Checkpoint
from ray.serve import PredictorDeployment
from ray.train.predictor import Predictor
from ray.train.xgboost import XGBoostPredictor

from trainer.svoe_mlflow_client import SvoeMLFlowClient


# TODO http options
def start_serve_deployment(
    predictor_class: Type[Predictor],
    checkpoint_uri: str,
    deployment_name: str = 'Deployment',
    num_replicas: int = 10
):
    checkpoint = Checkpoint.from_uri(checkpoint_uri)
    serve.start(
        detached=True,
        proxy_location='NoServer'
    )
    # TODO placement group
    deployment = PredictorDeployment.options(name=deployment_name, num_replicas=num_replicas)
    deployment.deploy(predictor_class, checkpoint)

    # serve.run(
    #     PredictorDeployment.options(name="RLDeployment").bind(RLPredictor, result.checkpoint)
    # )

# mlflow_client = SvoeMLFlowClient()
# uri = mlflow_client.get_best_checkpoint(metric_name='valid-logloss')
# uri = '/tmp/svoe/mlflow/mlruns/1/211408db196847e2befc331887450660/artifacts/checkpoint_000010'
# start_serve_deployment(
#     predictor_class=XGBoostPredictor,
#     checkpoint_uri=uri
# )