"""NEAR AI Cloud API client (OpenAI-compatible)."""

import httpx
from pathlib import Path
from typing import Any


class NearAIProvider:
    BASE_URL = "https://cloud-api.near.ai/v1"

    def __init__(self, api_key_file: str = "~/.config/near-ai/api_key"):
        key_path = Path(api_key_file).expanduser()
        if not key_path.exists():
            raise FileNotFoundError(f"NEAR AI API key not found at {key_path}")
        self.api_key = key_path.read_text().strip()
        self.client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
            },
            timeout=120.0,
        )

    def complete(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp = self.client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        return resp.json()

    def get_text(self, response: dict) -> str:
        return response["choices"][0]["message"]["content"]

    def get_usage(self, response: dict) -> dict:
        return response.get("usage", {})

    def close(self):
        self.client.close()
