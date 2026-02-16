"""External benchmark data fetcher (for future use)."""

import httpx
from typing import Any


def fetch_openrouter_models() -> list[dict[str, Any]]:
    """Fetch available models and pricing from OpenRouter."""
    resp = httpx.get("https://openrouter.ai/api/v1/models", timeout=30.0)
    resp.raise_for_status()
    return resp.json().get("data", [])


def get_model_pricing(models_data: list[dict], model_id: str) -> dict:
    """Get pricing info for a specific model."""
    for m in models_data:
        if m.get("id") == model_id:
            pricing = m.get("pricing", {})
            return {
                "prompt": float(pricing.get("prompt", 0)),
                "completion": float(pricing.get("completion", 0)),
            }
    return {"prompt": 0.0, "completion": 0.0}


def estimate_cost(usage: dict, pricing: dict) -> float:
    """Estimate cost in USD from token usage and pricing (per token)."""
    prompt_cost = usage.get("prompt_tokens", 0) * pricing.get("prompt", 0)
    completion_cost = usage.get("completion_tokens", 0) * pricing.get("completion", 0)
    return prompt_cost + completion_cost
