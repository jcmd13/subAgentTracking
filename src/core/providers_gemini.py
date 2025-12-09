"""
Gemini provider implementation (stubbed).

Replace generate() with real Google AI client calls when configured.
"""

from typing import Optional

from src.core.providers import BaseProvider, ProviderError


class GeminiAPIProvider(BaseProvider):
    def __init__(self, model: str = "gemini-2.0-pro", api_key: Optional[str] = None):
        super().__init__(name="gemini", model=model)
        self.api_key = api_key or "stub-key"

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise ProviderError("Gemini API key missing")
        return f"[gemini-api:{self.model}] {prompt}"


__all__ = ["GeminiAPIProvider"]
