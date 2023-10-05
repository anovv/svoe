import os
from typing import Annotated, Optional

import typer

from featurizer.config import FeaturizerConfig
from featurizer.runner import Featurizer

DEFAULT_RAY_ADDRESS = 'ray://127.0.0.1:10001' # TODO read env var
FEATURIZER_CLI_NAME = 'featurizer'
NUM_CPUS = os.cpu_count()

featurizer_app = typer.Typer()

@featurizer_app.command()
def run(config: str, parallelism: Annotated[Optional[int], typer.Argument(default=NUM_CPUS)] = None, ray_address: Annotated[Optional[str], typer.Argument(default=DEFAULT_RAY_ADDRESS)] = None):
    featurizer_config = FeaturizerConfig.load_config(path=config)
    if parallelism is None:
        parallelism = NUM_CPUS
    if ray_address is None:
        ray_address = DEFAULT_RAY_ADDRESS
    Featurizer.run(featurizer_config, ray_address=ray_address, parallelism=parallelism)

