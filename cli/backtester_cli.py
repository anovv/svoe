import time
from typing import Annotated, Optional

import typer

from backtester.runner import BacktesterConfig, Backtester
from backtester.viz.visualizer import Visualizer
from common.const import DEFAULT_LOCAL_RAY_ADDRESS
from trainer.trainer_manager import TrainerConfig, TrainerManager

BACKTESTER_CLI_NAME = 'backtester'
backtester_app = typer.Typer()


@backtester_app.command()
def run(
    config_path: str,
    ray_address: Annotated[str, typer.Argument(default=DEFAULT_LOCAL_RAY_ADDRESS)] = DEFAULT_LOCAL_RAY_ADDRESS,
    run_locally: Annotated[Optional[bool], typer.Argument(default=False)] = False,
    num_workers: Annotated[Optional[int], typer.Argument(default=1)] = 1
):
    config = BacktesterConfig.load_config(config_path)
    backtester = Backtester.from_config(config)
    start = time.time()
    if run_locally:
        result = backtester.run_locally()
    else:
        result = backtester.run_remotely(ray_address=ray_address, num_workers=num_workers)
    print(f'Finished run in {time.time() - start}s')
    viz = Visualizer(result)
    viz.visualize(instruments=config.tradable_instruments)

