import typer

from cli.featurizer_cli import featurizer_app, FEATURIZER_CLI_NAME
from cli.trainer_cli import trainer_app, TRAINER_CLI_NAME
from cli.backtester_cli import backtester_app, BACKTESTER_CLI_NAME

app = typer.Typer(pretty_exceptions_enable=False)
app.add_typer(featurizer_app, name=FEATURIZER_CLI_NAME)
app.add_typer(trainer_app, name=TRAINER_CLI_NAME)
app.add_typer(backtester_app, name=BACKTESTER_CLI_NAME)

if __name__ == '__main__':
    app()
