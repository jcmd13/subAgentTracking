from src.quality.gates import ProtectedTestsGate
from src.quality.runner import QualityGateRunner


def test_quality_gate_runner_passes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(tmp_path / ".subagent"))
    monkeypatch.setenv("SUBAGENT_CODEX_PROMPT_INSTALL", "false")

    gate = ProtectedTestsGate(modified_paths=["src/app.py"])
    runner = QualityGateRunner(gates=[gate])
    report = runner.run(persist=False)
    assert report["passed"] is True


def test_quality_gate_runner_blocks_tests(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(tmp_path / ".subagent"))
    monkeypatch.setenv("SUBAGENT_CODEX_PROMPT_INSTALL", "false")

    gate = ProtectedTestsGate(modified_paths=["tests/test_app.py"])
    runner = QualityGateRunner(gates=[gate])
    report = runner.run(persist=False)
    assert report["passed"] is False
    assert report["results"][0]["name"] == "protected_tests"
