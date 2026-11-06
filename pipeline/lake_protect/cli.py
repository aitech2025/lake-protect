"""`lp` command line. Heavy geospatial imports stay inside each command."""
import typer

app = typer.Typer(help="Lake Protect pipeline commands.", no_args_is_help=True)


@app.callback()
def main() -> None:
    """Lake Protect pipeline commands."""


@app.command()
def version() -> None:
    """Print the pipeline version."""
    from lake_protect import __version__

    typer.echo(__version__)


if __name__ == "__main__":
    app()
