import subprocess

import typer

from cli.featurizer_cli import featurizer_app, FEATURIZER_CLI_NAME
from cli.trainer_cli import trainer_app, TRAINER_CLI_NAME
from cli.backtester_cli import backtester_app, BACKTESTER_CLI_NAME

app = typer.Typer(pretty_exceptions_enable=False)
app.add_typer(featurizer_app, name=FEATURIZER_CLI_NAME)
app.add_typer(trainer_app, name=TRAINER_CLI_NAME)
app.add_typer(backtester_app, name=BACKTESTER_CLI_NAME)


@app.command()
def standalone():
    subprocess.run(['../scripts/init_db.sh'], shell=True)
    print('Finished initializing database')
    subprocess.run(['../scripts/start_mlflow_server.sh'], shell=True)
    print('Finished initializing mlflow')
    subprocess.run(['../scripts/start_ray_cluster.sh'], shell=True)
    print('Finished initializing Ray cluster')

if __name__ == '__main__':
    app()
