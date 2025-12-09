"""Provider interfaces and fallback manager for multi-model support.

Phase 3 scaffold:
- BaseProvider abstract class
- Stub providers for Claude, Ollama, and Gemini
- FallbackManager to cycle providers on failure

This is intentionally lightweight and offline-safe; real API calls should
replace the stubbed `generate` implementations in a future phase.
"""

from __future__ import annotations

import abc
from typing import List, Optional, Iterable


class ProviderError(Exception):
    """Raised when a provider fails to generate a response."""


class BaseProvider(abc.ABC):
    name: str
    model: str

    def __init__(self, name: str, model: str):
        self.name = name
        self.model = model

    @abc.abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate a response for the given prompt."""


class ClaudeProvider(BaseProvider):
    def __init__(self, model: str = "claude-sonnet-3.5"):
        super().__init__(name="claude", model=model)

    def generate(self, prompt: str) -> str:
        # Stubbed response for offline tests
        return f"[claude:{self.model}] {prompt}"


class OllamaProvider(BaseProvider):
    def __init__(self, model: str = "llama3"):
        super().__init__(name="ollama", model=model)

    def generate(self, prompt: str) -> str:
        return f"[ollama:{self.model}] {prompt}"


class GeminiProvider(BaseProvider):
    def __init__(self, model: str = "gemini-2.0-pro"):
        super().__init__(name="gemini", model=model)

    def generate(self, prompt: str) -> str:
        return f"[gemini:{self.model}] {prompt}"


class FallbackManager:
    """Simple fallback manager that tries providers in order until one succeeds."""

    def __init__(self, providers: Iterable[BaseProvider]):
        self.providers: List[BaseProvider] = list(providers)

    def generate(self, prompt: str) -> str:
        last_error: Optional[Exception] = None
        for provider in self.providers:
            try:
                return provider.generate(prompt)
            except Exception as e:  # pragma: no cover - exercised in tests via custom provider
                last_error = e
                continue
        raise ProviderError(f"All providers failed: {last_error}")


__all__ = [
    "BaseProvider",
    "ProviderError",
    "ClaudeProvider",
    "OllamaProvider",
    "GeminiProvider",
    "FallbackManager",
]
