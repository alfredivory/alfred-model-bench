"""OpenRouter API client."""

import httpx
from pathlib import Path
from typing import Any


class OpenRouterProvider:
    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, api_key_file: str = "~/.config/openrouter/api_key"):
        key_path = Path(api_key_file).expanduser()
        if not key_path.exists():
            raise FileNotFoundError(f"OpenRouter API key not found at {key_path}")
        self.api_key = key_path.read_text().strip()
        self.client = httpx.Client(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://github.com/alfredivory/alfred-model-bench",
                "X-Title": "Alfred Model Bench",
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
        """Send a chat completion request. Returns the full API response dict."""
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp = self.client.post("/chat/completions", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data

    def get_text(self, response: dict) -> str:
        """Extract the assistant text from a completion response."""
        return response["choices"][0]["message"]["content"]

    def get_usage(self, response: dict) -> dict:
        """Extract token usage from response."""
        return response.get("usage", {})

    def close(self):
        self.client.close()
