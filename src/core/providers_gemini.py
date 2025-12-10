"""
Gemini provider implementation (stubbed with optional real call).
"""

from typing import Optional

from src.core.providers import BaseProvider, ProviderError


class GeminiAPIProvider(BaseProvider):
    def __init__(self, model: str = "gemini-2.0-pro", api_key: Optional[str] = None):
        super().__init__(name="gemini", model=model)
        self.api_key = api_key or None

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            return f"[gemini-stub:{self.model}] {prompt}"

        try:
            import google.generativeai as genai  # type: ignore
        except Exception:
            return f"[gemini-stub:{self.model}] {prompt}"

        try:
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(prompt)
            return getattr(response, "text", str(response))
        except Exception as e:
            raise ProviderError(f"Gemini call failed: {e}") from e


__all__ = ["GeminiAPIProvider"]
