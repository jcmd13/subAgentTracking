from src.quality.gates import SecretScanGate


def test_secret_scan_gate_detects_pattern(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(tmp_path / ".subagent"))
    monkeypatch.setenv("SUBAGENT_CODEX_PROMPT_INSTALL", "false")

    file_path = tmp_path / "src" / "config.py"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text('api_key = "abc123"')

    gate = SecretScanGate(paths=[str(file_path)], repo_root=tmp_path)
    result = gate.run()
    assert result.passed is False
    assert result.details["matches"]


def test_secret_scan_gate_passes_without_secrets(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(tmp_path / ".subagent"))
    monkeypatch.setenv("SUBAGENT_CODEX_PROMPT_INSTALL", "false")

    file_path = tmp_path / "src" / "safe.py"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("value = 123\n")

    gate = SecretScanGate(paths=[str(file_path)], repo_root=tmp_path)
    result = gate.run()
    assert result.passed is True
    assert result.details["matches"] == []
