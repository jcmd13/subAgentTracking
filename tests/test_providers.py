import pytest

from src.core import providers


def test_stub_providers_generate():
    prompt = "hello"
    assert "claude" in providers.ClaudeProvider().generate(prompt)
    assert "ollama" in providers.OllamaProvider().generate(prompt)
    assert "gemini" in providers.GeminiProvider().generate(prompt)


def test_fallback_manager_uses_first_success():
    p1 = providers.ClaudeProvider()
    p2 = providers.OllamaProvider()
    mgr = providers.FallbackManager([p1, p2])
    out = mgr.generate("hi")
    assert out.startswith("[claude")


def test_fallback_manager_skips_failures():
    class Failing(providers.BaseProvider):
        def __init__(self):
            super().__init__("fail", "none")

        def generate(self, prompt: str) -> str:
            raise RuntimeError("boom")

    fallback = providers.FallbackManager([Failing(), providers.OllamaProvider(model="phi")])
    out = fallback.generate("ok")
    assert out.startswith("[ollama:phi]")


def test_fallback_manager_raises_when_all_fail():
    class Failing(providers.BaseProvider):
        def __init__(self):
            super().__init__("fail", "none")

        def generate(self, prompt: str) -> str:
            raise RuntimeError("boom")

    mgr = providers.FallbackManager([Failing(), Failing()])
    with pytest.raises(providers.ProviderError):
        mgr.generate("x")
