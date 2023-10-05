import typer

from cli.featurizer_cli import featurizer_app, FEATURIZER_CLI_NAME

app = typer.Typer()
app.add_typer(featurizer_app, name=FEATURIZER_CLI_NAME)

if __name__ == '__main__':
    app()
