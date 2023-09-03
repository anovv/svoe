from mlflow import MlflowClient
from mlflow.artifacts import download_artifacts
from ray.air import Checkpoint
from ray.train.xgboost import XGBoostPredictor

TRACKING_URI = 'http://localhost:64920'
ARTIFACTS_BUCKET = 'svoe-mlflow'

def get_experiment(experiment_id: str):
    client = MlflowClient(tracking_uri=TRACKING_URI)
    return client.get_experiment(experiment_id)


def get_run(run_id: str):
    client = MlflowClient(tracking_uri=TRACKING_URI)
    return client.get_run(run_id)

# def download_artifacts()

def load_checkpoint(run_id: str) -> Checkpoint:
    client = MlflowClient(tracking_uri=TRACKING_URI)
    run = client.get_run(run_id)
    artifact_uri = run.info.artifact_uri
    s = artifact_uri.removeprefix('mlflow-artifacts:/')
    checkpoint_uri = f's3://{ARTIFACTS_BUCKET}/{s}/checkpoint_000010'
    return Checkpoint.from_uri(checkpoint_uri)



if __name__ == '__main__':
    # print(get_experiment('2'))
    # run = get_run('ff662e4471dc49fa98bc047367492d50')
    # print(run)
    c = load_checkpoint('ff662e4471dc49fa98bc047367492d50')
    predictor = XGBoostPredictor.from_checkpoint(c)
