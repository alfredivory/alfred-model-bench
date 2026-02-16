"""Generate results JSON for the dashboard."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def generate_report(
    results: list[dict[str, Any]],
    output_dir: str = "results",
) -> Path:
    """Write a timestamped results JSON file.

    results: list of {model, scenario, score, details, usage, cost, duration_s}
    Returns path to the written file.
    """
    out = Path(output_dir)
    out.mkdir(exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "1.0",
        "results": results,
        "summary": _build_summary(results),
    }

    path = out / f"bench_{ts}.json"
    path.write_text(json.dumps(report, indent=2))
    return path


def _build_summary(results: list[dict]) -> dict:
    """Build per-model and per-scenario summary."""
    by_model: dict[str, list] = {}
    by_scenario: dict[str, list] = {}

    for r in results:
        model = r["model"]
        scenario = r["scenario"]
        score = r["score"]

        by_model.setdefault(model, []).append({"scenario": scenario, "score": score})
        by_scenario.setdefault(scenario, []).append({"model": model, "score": score})

    model_summary = {}
    for model, scores in by_model.items():
        avg = sum(s["score"] for s in scores) / max(len(scores), 1)
        total_cost = sum(
            r.get("cost", 0) for r in results if r["model"] == model
        )
        model_summary[model] = {
            "average_score": round(avg, 1),
            "scores": {s["scenario"]: s["score"] for s in scores},
            "total_cost": round(total_cost, 6),
        }

    scenario_summary = {}
    for scenario, scores in by_scenario.items():
        avg = sum(s["score"] for s in scores) / max(len(scores), 1)
        best = max(scores, key=lambda s: s["score"])
        scenario_summary[scenario] = {
            "average_score": round(avg, 1),
            "best_model": best["model"],
            "best_score": best["score"],
        }

    ranking = sorted(model_summary.items(), key=lambda x: x[1]["average_score"], reverse=True)

    return {
        "models": model_summary,
        "scenarios": scenario_summary,
        "ranking": [{"rank": i + 1, "model": m, "average": s["average_score"]} for i, (m, s) in enumerate(ranking)],
    }
