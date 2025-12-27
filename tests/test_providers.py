import pytest

from src.core import providers


def test_stub_providers_generate(monkeypatch):
    monkeypatch.setenv("SUBAGENT_PROVIDER_LIVE", "false")
    prompt = "hello"
    assert "claude" in providers.ClaudeProvider().generate(prompt)
    assert "ollama" in providers.OllamaProvider().generate(prompt)
    assert "gemini" in providers.GeminiProvider().generate(prompt)


def test_fallback_manager_uses_first_success(monkeypatch):
    monkeypatch.setenv("SUBAGENT_PROVIDER_LIVE", "false")
    p1 = providers.ClaudeProvider()
    p2 = providers.OllamaProvider()
    mgr = providers.FallbackManager([p1, p2])
    out = mgr.generate("hi")
    assert out.startswith("[claude")


def test_fallback_manager_skips_failures(monkeypatch):
    monkeypatch.setenv("SUBAGENT_PROVIDER_LIVE", "false")
    class Failing(providers.BaseProvider):
        def __init__(self):
            super().__init__("fail", "none")

        def generate(self, prompt: str) -> str:
            raise RuntimeError("boom")

    fallback = providers.FallbackManager([Failing(), providers.OllamaProvider(model="phi")])
    out = fallback.generate("ok")
    assert out.startswith("[ollama:phi]")


def test_fallback_manager_raises_when_all_fail(monkeypatch):
    monkeypatch.setenv("SUBAGENT_PROVIDER_LIVE", "false")
    class Failing(providers.BaseProvider):
        def __init__(self):
            super().__init__("fail", "none")

        def generate(self, prompt: str) -> str:
            raise RuntimeError("boom")

    mgr = providers.FallbackManager([Failing(), Failing()])
    with pytest.raises(providers.ProviderError):
        mgr.generate("x")


def test_build_providers_from_config(tmp_path, monkeypatch):
    cfg_dir = tmp_path / ".subagent" / "config"
    cfg_dir.mkdir(parents=True)
    config_path = cfg_dir / "providers.yaml"
    config_path.write_text("providers:\\n  order: [ollama, claude]\\n  ollama:\\n    model: mistral\\n  claude:\\n    model: haiku\\n")

    config = {
        "providers": {
            "order": ["ollama", "claude"],
            "ollama": {"model": "mistral"},
            "claude": {"model": "haiku"},
        }
    }
    instances = providers.build_providers(config)
    assert len(instances) == 2
    assert isinstance(instances[0], providers.OllamaProvider)
    assert instances[0].model == "mistral"
    assert isinstance(instances[1], providers.ClaudeProvider)
    assert instances[1].model == "haiku"
