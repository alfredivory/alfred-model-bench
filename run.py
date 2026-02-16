#!/usr/bin/env python3
"""CLI entry point for Alfred Model Bench."""

import json
import shutil
import click
from pathlib import Path

from src.runner import BenchmarkRunner


@click.group()
def cli():
    """Alfred Model Bench — benchmark LLMs across real-world scenarios."""
    pass


@cli.command()
@click.option("--all", "run_all", is_flag=True, help="Run all models × all scenarios.")
@click.option("--scenario", "scenario_filter", default=None, help="Filter scenarios by name.")
@click.option("--model", "model_filter", default=None, help="Filter models by id substring.")
def run(run_all, scenario_filter, model_filter):
    """Run benchmarks."""
    if not run_all and not scenario_filter and not model_filter:
        click.echo("Specify --all, --scenario <name>, or --model <id>.")
        raise SystemExit(1)

    runner = BenchmarkRunner()
    try:
        path = runner.run_and_report(
            model_filter=model_filter,
            scenario_filter=scenario_filter,
        )
        if path:
            # Symlink latest.json
            latest = Path("results/latest.json")
            latest.unlink(missing_ok=True)
            shutil.copy2(str(path), str(latest))
            click.echo(f"Latest results: {latest}")
    finally:
        runner.close()


@cli.command()
@click.option("--input", "input_path", default="results/latest.json", help="Results JSON to use.")
@click.option("--open", "open_browser", is_flag=True, help="Open dashboard in browser.")
def report(input_path, open_browser):
    """Generate/open the dashboard from results."""
    p = Path(input_path)
    if not p.exists():
        click.echo(f"Results file not found: {p}")
        click.echo("Run benchmarks first: python run.py run --all")
        raise SystemExit(1)

    click.echo(f"Dashboard ready: dashboard/index.html")
    click.echo(f"Data source: {p} ({json.loads(p.read_text())['timestamp']})")

    if open_browser:
        import webbrowser
        webbrowser.open(str(Path("dashboard/index.html").resolve()))


if __name__ == "__main__":
    cli()
