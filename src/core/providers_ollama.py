"""
Ollama provider implementation (stubbed).

Replace generate() with real HTTP/local ollama calls when available.
"""

from src.core.providers import BaseProvider, ProviderError


class OllamaAPIProvider(BaseProvider):
    def __init__(self, model: str = "llama3", endpoint: str = "http://localhost:11434"):
        super().__init__(name="ollama", model=model)
        self.endpoint = endpoint

    def generate(self, prompt: str) -> str:
        if not self.endpoint:
            raise ProviderError("Ollama endpoint missing")
        return f"[ollama-api:{self.model}] {prompt}"


__all__ = ["OllamaAPIProvider"]
