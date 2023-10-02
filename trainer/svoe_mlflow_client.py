from typing import Optional

from mlflow import MlflowClient
from mlflow.entities import Experiment, Run
from ray.air import Checkpoint

LOCAL_TRACKING_URI = 'http://127.0.0.1:5000'
REMOTE_TRACKING_URI = 'http://mlflow.mlflow.svc:5000'
ARTIFACTS_BUCKET = 'svoe-mlflow' # TODO env var this?


# wrapper around ml flow tracking api
class SvoeMLFlowClient:

    def __init__(self, tracking_uri: str = LOCAL_TRACKING_URI):
        self.mlflow_client = MlflowClient(tracking_uri=tracking_uri)

    def checkpoint_uri_from_run_id(self, run_id: str) -> str:
        run = self.mlflow_client.get_run(run_id)
        artifact_uri = run.info.artifact_uri
        if 'mlflow-artifacts:/' in artifact_uri:
            # remote store
            s = artifact_uri.removeprefix('mlflow-artifacts:/')
            checkpoint_uri = f's3://{ARTIFACTS_BUCKET}/{s}/checkpoint_000010'
        else:
            # local store
            checkpoint_uri = f'{artifact_uri}/checkpoint_000010'
        return checkpoint_uri

    def get_last_experiment(self) -> Experiment:
        experiments = self.mlflow_client.search_experiments(order_by=['creation_time'])
        return experiments[-1]

    def get_experiment_by_name(self, experiment_name: str) -> Experiment:
        filter_string = f'name={experiment_name}'
        experiments = self.mlflow_client.search_experiments(filter_string=filter_string)
        if len(experiments) != 1:
            raise ValueError(f'Found {len(experiments)} experiments for name {experiment_name}, should be 1')

        return experiments[0]

    def get_best_run_for_experiment(self, experiment: Experiment, metric_name: str, mode: str = 'min') -> Run:
        runs = self.mlflow_client.search_runs(experiment_ids=[experiment.experiment_id])
        if mode == 'min':
            best_run = min(runs, key=lambda run: run.data.metrics[metric_name])
        elif mode == 'max':
            best_run = max(runs, key=lambda run: run.data.metrics[metric_name])
        else:
            raise ValueError(f'Unknown mode: {mode}')
        return best_run

    def get_best_checkpoint_uri(self, metric_name: str, experiment_name: Optional[str] = None, mode: str = 'min') -> str:
        if experiment_name is None:
            experiment = self.get_last_experiment()
        else:
            experiment = self.get_experiment_by_name(experiment_name)

        run = self.get_best_run_for_experiment(experiment=experiment, metric_name=metric_name, mode=mode)
        return self.checkpoint_uri_from_run_id(run.info.run_id)

    def get_best_checkpoint(self, metric_name: str, experiment_name: Optional[str] = None, mode: str = 'min') -> Checkpoint:
        best_checkpoint_uri = self.get_best_checkpoint_uri(metric_name=metric_name, experiment_name=experiment_name, mode=mode)
        return Checkpoint.from_uri(best_checkpoint_uri)
