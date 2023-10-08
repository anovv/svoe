from typing import Type

from ray import serve
from ray.air import Checkpoint
from ray.serve import PredictorDeployment
from ray.serve.deployment import Deployment
from ray.train.predictor import Predictor

from simulation.inference.inference_loop import InferenceConfig


# TODO http options
# TODO placement group
def start_serve_predictor_deployment(
    inference_config: InferenceConfig,
) -> Deployment:
    checkpoint = Checkpoint.from_uri(inference_config.model_uri)
    serve.start(
        detached=True,
        proxy_location='NoServer'
    )
    deployment = PredictorDeployment.options(name=inference_config.deployment_name, num_replicas=inference_config.num_replicas)
    deployment.deploy(inference_config.predictor_class(), checkpoint)
    return deployment

# mlflow_client = SvoeMLFlowClient()
# uri = mlflow_client.get_best_checkpoint_uri(metric_name='valid-logloss')
# # uri = '/tmp/svoe/mlflow/mlruns/1/211408db196847e2befc331887450660/artifacts/checkpoint_000010'
# start_serve_predictor_deployment(
#     predictor_class=XGBoostPredictor,
#     checkpoint_uri=uri,
#     deployment_name='dep',
#     num_replicas=10
# )