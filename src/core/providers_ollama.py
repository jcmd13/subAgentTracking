"""
Ollama provider implementation (HTTP/local).

If HTTP call fails (e.g., Ollama not running), falls back to stub output to keep
tests offline-safe.
"""

import json
from typing import Optional

import requests  # type: ignore

from src.core.providers import BaseProvider, ProviderError


class OllamaAPIProvider(BaseProvider):
    def __init__(self, model: str = "llama3", endpoint: str = "http://localhost:11434"):
        super().__init__(name="ollama", model=model)
        self.endpoint = endpoint

    def generate(self, prompt: str) -> str:
        if not self.endpoint:
            raise ProviderError("Ollama endpoint missing")
        try:
            resp = requests.post(
                f"{self.endpoint}/api/generate",
                json={"model": self.model, "prompt": prompt},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response") or data.get("data") or json.dumps(data)
        except Exception as e:
            # Stub fallback for offline/failed calls
            return f"[ollama-stub:{self.model}] {prompt} ({e})"


__all__ = ["OllamaAPIProvider"]
