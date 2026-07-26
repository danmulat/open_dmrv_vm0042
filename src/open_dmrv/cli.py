"""Command line interface."""

from __future__ import annotations

from pathlib import Path

import typer

from .pipeline import run_synthetic_pipeline

app = typer.Typer(help="Open digital MRV research tools", no_args_is_help=True)


@app.callback()
def main() -> None:
    """Open digital MRV research tools."""


@app.command()
def synthetic(
    output: Path = typer.Option(Path("outputs"), help="Output directory"),
    config: Path = typer.Option(Path("config.yml"), help="Configuration YAML"),
    seed: int = typer.Option(20260726, help="Random seed"),
) -> None:
    """Run the complete synthetic Ethiopian test pipeline."""
    paths = run_synthetic_pipeline(output, config, seed)
    typer.echo("Synthetic pipeline completed")
    for name, path in paths.items():
        typer.echo(f"{name}: {path}")


if __name__ == "__main__":
    app()
