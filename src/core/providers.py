"""Provider interfaces and fallback manager for multi-model support.

Phase 3 scaffold:
- BaseProvider abstract class
- Stub providers for Claude, Ollama, and Gemini
- FallbackManager to cycle providers on failure
- Provider factory that loads ordering and models from YAML

This is intentionally lightweight and offline-safe; real API calls should
replace the stubbed `generate` implementations in a future phase.
"""

from __future__ import annotations

import abc
import json
from pathlib import Path
from typing import List, Optional, Iterable, Dict, Any

import yaml


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


# ---------------------------------------------------------------------------
# Provider factory helpers
# ---------------------------------------------------------------------------


DEFAULT_ORDER = ["claude", "ollama", "gemini"]


def load_provider_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load provider config from YAML if present.

    Example config structure::

        providers:
          order: ["ollama", "claude", "gemini"]
          claude:
            model: "claude-sonnet-3.5"
          ollama:
            model: "llama3"
          gemini:
            model: "gemini-2.0-pro"
    """

    cfg = {
        "providers": {
            "order": DEFAULT_ORDER,
            "claude": {"model": "claude-sonnet-3.5"},
            "ollama": {"model": "llama3"},
            "gemini": {"model": "gemini-2.0-pro"},
        }
    }

    path = config_path or Path(".subagent/config/providers.yaml")
    if path.exists():
        try:
            data = yaml.safe_load(path.read_text()) or {}
            providers_cfg = data.get("providers", {})
            if isinstance(providers_cfg, dict):
                order = providers_cfg.get("order")
                cfg["providers"].update(providers_cfg)
                if order is not None:
                    cfg["providers"]["order"] = order
        except Exception:
            # Fallback to defaults on parse errors
            pass

    return cfg


def build_providers(config: Optional[Dict[str, Any]] = None) -> List[BaseProvider]:
    """Build provider instances from config dict."""
    cfg = config or load_provider_config()
    providers_cfg = cfg.get("providers", {})
    order = providers_cfg.get("order")
    if not isinstance(order, list):
        order = DEFAULT_ORDER

    instances: List[BaseProvider] = []
    for name in order:
        if name == "claude":
            model = providers_cfg.get("claude", {}).get("model", "claude-sonnet-3.5")
            instances.append(ClaudeProvider(model=model))
        elif name == "ollama":
            model = providers_cfg.get("ollama", {}).get("model", "llama3")
            instances.append(OllamaProvider(model=model))
        elif name == "gemini":
            model = providers_cfg.get("gemini", {}).get("model", "gemini-2.0-pro")
            instances.append(GeminiProvider(model=model))
    return instances


__all__ = [
    "BaseProvider",
    "ProviderError",
    "ClaudeProvider",
    "OllamaProvider",
    "GeminiProvider",
    "FallbackManager",
]
