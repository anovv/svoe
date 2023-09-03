from mlflow import MlflowClient
from ray.air import Checkpoint

LOCAL_TRACKING_URI = 'http://localhost:64920'
REMOTE_TRACKING_URI = 'http://mlflow.mlflow.svc:5000'
ARTIFACTS_BUCKET = 'svoe-mlflow' # TODO env var this?

# wrapper around ml flow tracking api
class SvoeMLFlowClient:

    def __init__(self, tracking_uri: str):
        self.client = MlflowClient(tracking_uri=tracking_uri)

    def get_trainer_runs(self, user_id: str, dag_run_id: str, task_name: str):
        pass

    def load_checkpoint(self, trainer_run_id: str) -> Checkpoint:
        run = self.client.get_run(trainer_run_id)
        artifact_uri = run.info.artifact_uri
        s = artifact_uri.removeprefix('mlflow-artifacts:/')
        checkpoint_uri = f's3://{ARTIFACTS_BUCKET}/{s}/checkpoint_000010'
        return Checkpoint.from_uri(checkpoint_uri)