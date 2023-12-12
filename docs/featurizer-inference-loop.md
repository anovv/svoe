# Real-time model inference with Inference Loop

Featurizer utilizes **[Ray Serve](https://docs.ray.io/en/latest/serve/index.html)** to help
users do real-time inference and provides an ```InferenceLoop``` abstraction to do asynchronous
inference on streaming data.

This allows to bypass a typical MLOps approach of creating Docker containers and FastAPI services and all the burden of maintaining relevant infrastructure.


# InferenceLoop

[```InferenceLoop```](https://github.com/anovv/svoe/blob/main/backtester/inference/inference_loop.py) is a class providing a mechanism
for continuous model polling and latest request result storage for downstream processing. 
In a nutshell it is a separate actor/process that continuously sends requests to a model and outputs last results. 
When used in offline mode, users can provide ```Clock``` instance to synchronize time between
Featurizer event processing pipelines and inference.

Some notable benefits of this approach:

- No need to maintain model containerization pipelines, FastAPI services and model registries. Deploy with simple Python API or yaml
- Integration with MLFlow
- Asynchronous inference allows for real-time processing without blocking on model-related calculations 
- Scalable inference using adjustable ```num_replicas```, indicating number of inference workers
- Decouples event processing and inference
- Use of special hardware (i.e. GPUs)



# Inference Configuration

When running an ```InferenceLoop``` in different scenarios (real-time Featurizer pipeline or Backtester),
users can configure certain options

- ```deployment_name``` - optional Ray Serve Deployment name
- ```model_uri``` - path to model's artifacts as stored in MLFlow artifact storage
- ```predictor_class_name``` - Ray Serve predictor type (ex. ```XGBoostPredictor```)
- ```num_replicas``` - number of Inference Actors to be used for this loop. Requests to workers are evenly
distributed (i.e. round-robin) via http-proxy actor

=== "InferenceConfig"
    ```
    class InferenceConfig(BaseModel):
        deployment_name: Optional[str]
        model_uri: str
        predictor_class_name: str
        num_replicas: int
    ```
=== "YAML"
    ```
    ...
    inference_config:
      model_uri: <your-best-model-uri>
      predictor_class_name: 'XGBoostPredictor'
      num_replicas: <number-of-predictor-replicas>
    ...
    ```
