"""Ollama local model client."""

import httpx
from typing import Any


class OllamaProvider:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.client = httpx.Client(base_url=base_url, timeout=300.0)

    def is_available(self) -> bool:
        try:
            resp = self.client.get("/api/tags")
            return resp.status_code == 200
        except httpx.ConnectError:
            return False

    def list_models(self) -> list[str]:
        resp = self.client.get("/api/tags")
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", [])]

    def complete(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        resp = self.client.post("/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json()

    def get_text(self, response: dict) -> str:
        return response.get("message", {}).get("content", "")

    def get_usage(self, response: dict) -> dict:
        return {
            "prompt_tokens": response.get("prompt_eval_count", 0),
            "completion_tokens": response.get("eval_count", 0),
        }

    def close(self):
        self.client.close()
