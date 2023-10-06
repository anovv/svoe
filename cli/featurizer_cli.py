from typing import Annotated, Optional

import typer

from common.const import DEFAULT_LOCAL_RAY_ADDRESS, NUM_CPUS
from common.pandas.df_utils import plot_multi
from featurizer.config import FeaturizerConfig
from featurizer.runner import Featurizer

FEATURIZER_CLI_NAME = 'featurizer'
featurizer_app = typer.Typer()


@featurizer_app.command()
def run(config_path: str, parallelism: Annotated[Optional[int], typer.Argument(default=NUM_CPUS)] = NUM_CPUS, ray_address: Annotated[str, typer.Argument(default=DEFAULT_LOCAL_RAY_ADDRESS)] = DEFAULT_LOCAL_RAY_ADDRESS):
    featurizer_config = FeaturizerConfig.load_config(path=config_path)
    Featurizer.run(featurizer_config, ray_address=ray_address, parallelism=parallelism)


@featurizer_app.command()
def get_data(every_n: Annotated[Optional[int], typer.Argument(default=1)] = 1):
    df = Featurizer.get_materialized_data(pick_every_nth_row=every_n)
    print(df)


@featurizer_app.command()
def plot(every_n: Annotated[Optional[int], typer.Argument(default=1)] = 1):
    df = Featurizer.get_materialized_data(pick_every_nth_row=every_n)
    plot_multi(df=df)
