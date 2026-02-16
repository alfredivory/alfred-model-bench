"""Main benchmark runner."""

import json
import time
import yaml
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table

from .providers.openrouter import OpenRouterProvider
from .providers.ollama import OllamaProvider
from .providers.nearai import NearAIProvider
from .evaluator import Evaluator
from .external import fetch_openrouter_models, get_model_pricing, estimate_cost
from .report import generate_report

console = Console()


def load_config(path: str = "config.yaml") -> dict:
    return yaml.safe_load(Path(path).read_text())


def load_scenario(path: str) -> dict:
    return yaml.safe_load(Path(path).read_text())


def load_all_scenarios(scenarios_dir: str = "scenarios") -> list[dict]:
    scenarios = []
    for f in sorted(Path(scenarios_dir).glob("*.yaml")):
        s = load_scenario(str(f))
        s["_file"] = f.stem
        scenarios.append(s)
    return scenarios


def build_messages(scenario: dict) -> list[dict[str, str]]:
    """Build chat messages from scenario definition."""
    messages = []
    if scenario.get("system_prompt"):
        messages.append({"role": "system", "content": scenario["system_prompt"]})
    messages.append({"role": "user", "content": scenario["prompt"]})
    return messages


class BenchmarkRunner:
    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        self.api_key_file = self.config.get("openrouter_api_key_file", "~/.config/openrouter/api_key")
        self.openrouter = OpenRouterProvider(self.api_key_file)
        self.ollama = OllamaProvider(self.config.get("ollama_url", "http://localhost:11434"))
        self.nearai_key_file = self.config.get("nearai_api_key_file", "~/.config/near-ai/api_key")
        self.nearai = NearAIProvider(self.nearai_key_file)
        self.evaluator = Evaluator(self.config["evaluator_model"], self.api_key_file)
        self._models_data = None

    @property
    def models_data(self):
        if self._models_data is None:
            try:
                self._models_data = fetch_openrouter_models()
            except Exception:
                self._models_data = []
        return self._models_data

    def get_models(self, model_filter: str | None = None) -> list[dict]:
        models = self.config.get("models", [])
        if model_filter:
            models = [m for m in models if model_filter in m["id"]]
        return models

    def run_single(self, model_cfg: dict, scenario: dict) -> dict[str, Any]:
        """Run a single model against a single scenario."""
        model_id = model_cfg["id"]
        provider_name = model_cfg["provider"]
        messages = build_messages(scenario)

        start = time.time()
        try:
            if provider_name == "openrouter":
                raw = self.openrouter.complete(model_id, messages)
                text = self.openrouter.get_text(raw)
                usage = self.openrouter.get_usage(raw)
            elif provider_name == "nearai":
                raw = self.nearai.complete(model_id, messages)
                text = self.nearai.get_text(raw)
                usage = self.nearai.get_usage(raw)
            elif provider_name == "ollama":
                if not self.ollama.is_available():
                    return {"model": model_id, "scenario": scenario["_file"], "score": 0,
                            "error": "Ollama not available", "details": {}, "usage": {}, "cost": 0, "duration_s": 0}
                raw = self.ollama.complete(model_id, messages)
                text = self.ollama.get_text(raw)
                usage = self.ollama.get_usage(raw)
            else:
                return {"model": model_id, "scenario": scenario["_file"], "score": 0,
                        "error": f"Unknown provider: {provider_name}", "details": {}, "usage": {}, "cost": 0, "duration_s": 0}
        except Exception as e:
            return {"model": model_id, "scenario": scenario["_file"], "score": 0,
                    "error": str(e), "details": {}, "usage": {}, "cost": 0, "duration_s": time.time() - start}

        duration = time.time() - start

        # Evaluate
        eval_result = self.evaluator.evaluate_scenario(scenario, text)

        # Cost
        pricing = get_model_pricing(self.models_data, model_id)
        cost = estimate_cost(usage, pricing)

        return {
            "model": model_id,
            "scenario": scenario["_file"],
            "score": eval_result["score"],
            "details": eval_result["details"],
            "response_preview": text[:500],
            "usage": usage,
            "cost": round(cost, 6),
            "duration_s": round(duration, 2),
        }

    def run(
        self,
        model_filter: str | None = None,
        scenario_filter: str | None = None,
    ) -> list[dict]:
        """Run the full benchmark. Returns list of results."""
        models = self.get_models(model_filter)
        scenarios = load_all_scenarios()
        if scenario_filter:
            scenarios = [s for s in scenarios if scenario_filter in s["_file"]]

        if not models:
            console.print("[red]No models matched filter[/red]")
            return []
        if not scenarios:
            console.print("[red]No scenarios matched filter[/red]")
            return []

        total = len(models) * len(scenarios)

        # Load incremental progress if available
        progress_file = Path("results/_progress.jsonl")
        progress_file.parent.mkdir(exist_ok=True)
        results = []
        completed = set()
        if progress_file.exists():
            for line in progress_file.read_text().strip().split("\n"):
                if line:
                    r = json.loads(line)
                    results.append(r)
                    completed.add((r["model"], r["scenario"]))
            if completed:
                console.print(f"[yellow]Resuming: {len(completed)} tests already completed[/yellow]")

        skipped = len(completed)
        console.print(f"\n[bold]Running {len(models)} models × {len(scenarios)} scenarios = {total} tests ({skipped} cached)[/bold]\n")

        with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                      BarColumn(), TextColumn("{task.completed}/{task.total}")) as progress_bar:
            task = progress_bar.add_task("Benchmarking...", total=total, completed=skipped)
            for model_cfg in models:
                for scenario in scenarios:
                    key = (model_cfg["id"], scenario["_file"])
                    if key in completed:
                        progress_bar.advance(task)
                        continue
                    progress_bar.update(task, description=f"{model_cfg['id'][:30]} × {scenario['_file']}")
                    # Skip optional models that aren't available
                    if model_cfg.get("optional") and model_cfg["provider"] == "ollama":
                        if not self.ollama.is_available():
                            progress_bar.advance(task)
                            continue
                    result = self.run_single(model_cfg, scenario)
                    results.append(result)
                    # Save incrementally
                    with open(progress_file, "a") as f:
                        f.write(json.dumps(result) + "\n")
                    if result.get("error"):
                        console.print(f"  [red]✗ {result['error'][:60]}[/red]")
                    else:
                        console.print(f"  [green]✓[/green] {result['model'][:30]} × {result['scenario']}: {result['score']}/100 ({result['duration_s']}s)")
                    progress_bar.advance(task)

        # Clean up progress file on successful completion
        if progress_file.exists():
            progress_file.unlink()

        return results

    def run_and_report(self, **kwargs) -> Path:
        results = self.run(**kwargs)
        if results:
            path = generate_report(results)
            console.print(f"\n[bold green]Report saved to {path}[/bold green]")
            self._print_summary(results)
            return path
        return None

    def _print_summary(self, results: list[dict]):
        table = Table(title="Benchmark Results")
        table.add_column("Model", style="cyan")
        scenarios = sorted(set(r["scenario"] for r in results))
        for s in scenarios:
            table.add_column(s[:15], justify="center")
        table.add_column("Avg", style="bold", justify="center")

        by_model = {}
        for r in results:
            by_model.setdefault(r["model"], {})[r["scenario"]] = r["score"]

        for model, scores in sorted(by_model.items()):
            row = [model.split("/")[-1][:25]]
            vals = []
            for s in scenarios:
                v = scores.get(s, "-")
                row.append(str(v))
                if isinstance(v, (int, float)):
                    vals.append(v)
            avg = round(sum(vals) / max(len(vals), 1), 1) if vals else "-"
            row.append(str(avg))
            table.add_row(*row)

        console.print(table)

    def close(self):
        self.openrouter.close()
        self.ollama.close()
        self.nearai.close()
        self.evaluator.close()
