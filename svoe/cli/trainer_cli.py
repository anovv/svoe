from typing import Annotated, Optional

import typer
from ray.air import Checkpoint
from ray.train.xgboost import XGBoostPredictor

from svoe.common.const import DEFAULT_LOCAL_RAY_ADDRESS
from svoe.common.pandas.df_utils import plot_multi
from svoe.trainer.svoe_mlflow_client import SvoeMLFlowClient
from svoe.trainer.trainer_manager import TrainerConfig, TrainerManager

TRAINER_CLI_NAME = 'trainer'
trainer_app = typer.Typer()
mlflow_client = SvoeMLFlowClient() # TODO configure tracking uri


@trainer_app.command()
def run(config_path: str, ray_address: Annotated[str, typer.Argument(default=DEFAULT_LOCAL_RAY_ADDRESS)] = DEFAULT_LOCAL_RAY_ADDRESS):
    config = TrainerConfig.load_config(config_path)
    trainer_manager = TrainerManager(config=config, ray_address=ray_address)

    # TODO pass trainer_run_id or experiment name?
    # TODO pass tags
    trainer_manager.run(trainer_run_id='sample-run-id', tags={})


@trainer_app.command()
def best_model(
    metric_name: str,
    experiment_name: Annotated[Optional[str], typer.Argument(default=None)] = None,
    mode: Annotated[str, typer.Argument('min')] = 'min'
):
    uri = mlflow_client.get_best_checkpoint_uri(metric_name=metric_name, experiment_name=experiment_name, mode=mode)
    print(uri)


@trainer_app.command()
def predictions(
    model_uri: str,
    same_fig: Annotated[Optional[bool], typer.Argument(default=False)] = False
):
    checkpoint = Checkpoint.from_uri(model_uri)
    ds = TrainerManager.generate_predictions_dataset(checkpoint, XGBoostPredictor, 4)
    df = ds.to_pandas()
    plot_multi(df=df, same_fig=same_fig)
