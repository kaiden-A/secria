"""Secria command-line interface.

Phase 0 ships the Typer shell. Phase 6 adds login/device flow, the .env
workflow, and service-token commands. Keep all output hygiene rules from the
plan: values are never printed unless the command is explicitly `get` or
`--reveal`.
"""

import typer
from rich.console import Console

from . import __version__

app = typer.Typer(
    name="secria",
    help="Secria secrets manager CLI: push, pull, diff, and run with secrets.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


@app.callback()
def main() -> None:
    """Secria secrets manager CLI."""


@app.command()
def version() -> None:
    """Print the CLI version."""
    console.print(f"secria [bold]{__version__}[/bold]")
