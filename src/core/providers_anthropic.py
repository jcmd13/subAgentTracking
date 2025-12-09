"""
Anthropic provider implementation.

This is a stubbed implementation to keep tests offline. Replace the generate()
body with a real Anthropic API call when keys/endpoints are available.
"""

from typing import Optional

from src.core.providers import BaseProvider, ProviderError


class AnthropicProvider(BaseProvider):
    def __init__(self, model: str = "claude-3-sonnet-20240229", api_key: Optional[str] = None):
        super().__init__(name="claude", model=model)
        self.api_key = api_key or "stub-key"

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise ProviderError("Anthropic API key missing")
        # Stubbed offline response
        return f"[anthropic:{self.model}] {prompt}"


__all__ = ["AnthropicProvider"]
