import subprocess

from src.quality.gates import CommandGate


def test_command_gate_passes_with_stub(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(tmp_path / ".subagent"))
    monkeypatch.setenv("SUBAGENT_CODEX_PROMPT_INSTALL", "false")

    def runner(command, timeout):
        return subprocess.CompletedProcess(command, returncode=0, stdout="ok", stderr="")

    gate = CommandGate("stub", ["echo", "ok"], runner=runner, permission_profile="elevated")
    result = gate.run()
    assert result.passed is True
    assert result.details["exit_code"] == 0


def test_command_gate_fails_with_stub(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(tmp_path / ".subagent"))
    monkeypatch.setenv("SUBAGENT_CODEX_PROMPT_INSTALL", "false")

    def runner(command, timeout):
        return subprocess.CompletedProcess(command, returncode=1, stdout="", stderr="fail")

    gate = CommandGate("stub", ["false"], runner=runner, permission_profile="elevated")
    result = gate.run()
    assert result.passed is False
    assert "fail" in result.message
