from typing import List, Any

from simulation.inference.inference import start_serve_predictor_deployment
from simulation.inference.inference_loop import InferenceConfig, InferenceLoop

inference_config = InferenceConfig(
    deployment_name='test-deployment',
    model_uri='file:///tmp/svoe/mlflow/mlruns/1/d6e5eccdfedf43f8acd966e4d6d331a4/artifacts/checkpoint_000010',
    predictor_class_name='XGBoostPredictor',
    num_replicas=1
)

def inference_input_values_provider() -> List[Any]:
    return [222]

start_serve_predictor_deployment(
    inference_config
)
inference_loop = InferenceLoop(inference_input_values_provider, inference_config)
print(inference_loop._make_request())
