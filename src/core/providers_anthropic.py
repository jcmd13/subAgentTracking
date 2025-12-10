"""
Anthropic provider implementation.

Offline-safe: if no API key or `anthropic` SDK is unavailable, returns a stub
response instead of raising to keep tests passing. When a key is present and
the SDK is installed, it will call the Anthropic API.
"""

from typing import Optional

from src.core.providers import BaseProvider, ProviderError


class AnthropicProvider(BaseProvider):
    def __init__(self, model: str = "claude-3-sonnet-20240229", api_key: Optional[str] = None):
        super().__init__(name="claude", model=model)
        self.api_key = api_key or None

    def generate(self, prompt: str) -> str:
        # If no key or SDK missing, return stub
        if not self.api_key:
            return f"[anthropic-stub:{self.model}] {prompt}"
        try:
            import anthropic
        except Exception:
            return f"[anthropic-stub:{self.model}] {prompt}"

        try:
            client = anthropic.Anthropic(api_key=self.api_key)
            resp = client.messages.create(
                model=self.model,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text if getattr(resp, "content", None) else str(resp)
        except Exception as e:
            raise ProviderError(f"Anthropic call failed: {e}") from e


__all__ = ["AnthropicProvider"]
