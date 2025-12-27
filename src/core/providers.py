"""Provider interfaces and fallback manager for multi-model support.

Phase 3:
- BaseProvider abstract class
- Live-capable providers for Claude, Ollama, and Gemini (stubbed when disabled)
- FallbackManager to cycle providers on failure
- Provider factory that loads ordering and models from YAML
"""

from __future__ import annotations

import abc
import json
import os
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


def _is_truthy(value: Optional[str]) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _resolve_live_flag(providers_cfg: Optional[Dict[str, Any]] = None) -> bool:
    if providers_cfg:
        live_value = providers_cfg.get("live")
        if live_value is not None:
            if isinstance(live_value, bool):
                return live_value
            return _is_truthy(str(live_value))
    return _is_truthy(os.getenv("SUBAGENT_PROVIDER_LIVE") or os.getenv("SUBAGENT_LIVE_PROVIDERS"))


class ClaudeProvider(BaseProvider):
    def __init__(
        self,
        model: str = "claude-sonnet-3.5",
        api_key: Optional[str] = None,
        allow_live: Optional[bool] = None,
    ):
        super().__init__(name="claude", model=model)
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY")
        self.allow_live = allow_live if allow_live is not None else _resolve_live_flag()

    def generate(self, prompt: str) -> str:
        if not self.allow_live:
            return f"[claude:{self.model}] {prompt}"
        if not self.api_key:
            raise ProviderError("Anthropic API key missing (set ANTHROPIC_API_KEY).")
        try:
            import anthropic  # type: ignore
        except Exception as e:
            raise ProviderError("Anthropic SDK not installed.") from e

        try:
            client = anthropic.Anthropic(api_key=self.api_key)
            response = client.messages.create(
                model=self.model,
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}],
            )
            content = getattr(response, "content", None)
            if isinstance(content, list) and content:
                block = content[0]
                text = getattr(block, "text", None)
                if text:
                    return text
            return str(response)
        except Exception as e:
            raise ProviderError(f"Anthropic call failed: {e}") from e


class OllamaProvider(BaseProvider):
    def __init__(
        self,
        model: str = "llama3",
        endpoint: Optional[str] = None,
        allow_live: Optional[bool] = None,
    ):
        super().__init__(name="ollama", model=model)
        self.endpoint = endpoint or os.getenv("OLLAMA_HOST") or os.getenv("OLLAMA_BASE_URL")
        self.allow_live = allow_live if allow_live is not None else _resolve_live_flag()

    def generate(self, prompt: str) -> str:
        if not self.allow_live:
            return f"[ollama:{self.model}] {prompt}"
        try:
            import ollama  # type: ignore
        except Exception as e:
            raise ProviderError("Ollama SDK not installed.") from e

        try:
            if self.endpoint:
                client = ollama.Client(host=self.endpoint)
                data = client.generate(model=self.model, prompt=prompt)
            else:
                data = ollama.generate(model=self.model, prompt=prompt)
            response = data.get("response")
            if response:
                return response
            message = data.get("message", {})
            if isinstance(message, dict) and message.get("content"):
                return message["content"]
            return json.dumps(data)
        except Exception as e:
            raise ProviderError(f"Ollama call failed: {e}") from e


class GeminiProvider(BaseProvider):
    def __init__(
        self,
        model: str = "gemini-2.0-pro",
        api_key: Optional[str] = None,
        allow_live: Optional[bool] = None,
    ):
        super().__init__(name="gemini", model=model)
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        self.allow_live = allow_live if allow_live is not None else _resolve_live_flag()

    def generate(self, prompt: str) -> str:
        if not self.allow_live:
            return f"[gemini:{self.model}] {prompt}"
        if not self.api_key:
            raise ProviderError("Gemini API key missing (set GOOGLE_API_KEY).")
        try:
            import google.generativeai as genai  # type: ignore
        except Exception as e:
            raise ProviderError("Gemini SDK not installed.") from e

        try:
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(prompt)
            text = getattr(response, "text", None)
            return text or str(response)
        except Exception as e:
            raise ProviderError(f"Gemini call failed: {e}") from e


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
            "live": False,
            "order": DEFAULT_ORDER,
            "claude": {"model": "claude-sonnet-3.5"},
            "ollama": {"model": "llama3"},
            "gemini": {"model": "gemini-2.0-pro"},
        }
    }

    if config_path:
        path = config_path
    else:
        data_dir = os.getenv("SUBAGENT_DATA_DIR") or ".subagent"
        path = Path(data_dir) / "config" / "providers.yaml"
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
    if config is not None:
        cfg = config
    else:
        cfg = load_provider_config()
    providers_cfg = cfg.get("providers", {})
    if not isinstance(providers_cfg, dict):
        providers_cfg = {}
    live_calls = _resolve_live_flag(providers_cfg)
    order = providers_cfg.get("order") if config is not None else providers_cfg.get("order", DEFAULT_ORDER)
    if not isinstance(order, list):
        order = DEFAULT_ORDER

    instances: List[BaseProvider] = []
    for name in order:
        if name == "claude":
            claude_cfg = providers_cfg.get("claude", {}) if isinstance(providers_cfg.get("claude"), dict) else {}
            model = claude_cfg.get("model", "claude-sonnet-3.5")
            api_key = claude_cfg.get("api_key")
            instances.append(ClaudeProvider(model=model, api_key=api_key, allow_live=live_calls))
        elif name == "ollama":
            ollama_cfg = providers_cfg.get("ollama", {}) if isinstance(providers_cfg.get("ollama"), dict) else {}
            model = ollama_cfg.get("model", "llama3")
            endpoint = ollama_cfg.get("endpoint")
            instances.append(OllamaProvider(model=model, endpoint=endpoint, allow_live=live_calls))
        elif name == "gemini":
            gemini_cfg = providers_cfg.get("gemini", {}) if isinstance(providers_cfg.get("gemini"), dict) else {}
            model = gemini_cfg.get("model", "gemini-2.0-pro")
            api_key = gemini_cfg.get("api_key")
            instances.append(GeminiProvider(model=model, api_key=api_key, allow_live=live_calls))
    return instances


__all__ = [
    "BaseProvider",
    "ProviderError",
    "ClaudeProvider",
    "OllamaProvider",
    "GeminiProvider",
    "FallbackManager",
]
