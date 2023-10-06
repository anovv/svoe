from typing import Annotated

import typer

from common.const import DEFAULT_LOCAL_RAY_ADDRESS
from trainer.trainer_manager import TrainerConfig, TrainerManager

TRAINER_CLI_NAME = 'trainer'
trainer_app = typer.Typer()


@trainer_app.command()
def run(config_path: str, ray_address: Annotated[str, typer.Argument(default=DEFAULT_LOCAL_RAY_ADDRESS)] = DEFAULT_LOCAL_RAY_ADDRESS):
    config = TrainerConfig.load_config(config_path)
    trainer_manager = TrainerManager(config=config, ray_address=ray_address)

    # TODO pass trainer_run_id or experiment name?
    # TODO pass tags
    trainer_manager.run(trainer_run_id='sample-run-id', tags={})
