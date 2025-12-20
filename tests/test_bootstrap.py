from pathlib import Path

from src.core.config import reset_config


def test_ensure_initialized_creates_config(tmp_path, monkeypatch):
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(tmp_path / ".subagent"))
    monkeypatch.setenv("SUBAGENT_AUTO_INIT", "true")
    monkeypatch.setenv("SUBAGENT_CODEX_PROMPT_INSTALL", "false")
    reset_config()

    from src.core.bootstrap import ensure_initialized, is_initialized

    assert is_initialized() is False
    assert ensure_initialized(prompt_if_needed=False) is True

    config_path = tmp_path / ".subagent" / "config.yaml"
    assert config_path.exists()
