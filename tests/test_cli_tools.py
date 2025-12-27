import json

from typer.testing import CliRunner

from src.subagent_cli.app import app


runner = CliRunner()


def test_cli_tool_check_and_simulate(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(tmp_path / ".subagent"))
    monkeypatch.setenv("SUBAGENT_CODEX_PROMPT_INSTALL", "false")

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0

    result = runner.invoke(
        app,
        ["tool", "check", "read", "--path", "src/app.py", "--json"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["allowed"] is True

    result = runner.invoke(
        app,
        ["tool", "check", "read", "--path", "README.md"],
    )
    assert result.exit_code == 0
    assert "Denied" in result.stdout

    result = runner.invoke(
        app,
        ["tool", "simulate", "read", "--path", "src/app.py", "--json"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["success"] is True

    result = runner.invoke(
        app,
        ["tool", "simulate", "bash", "--bash", "--json"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["success"] is False


def test_cli_tool_read_write_edit(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(tmp_path / ".subagent"))
    monkeypatch.setenv("SUBAGENT_CODEX_PROMPT_INSTALL", "false")

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0

    target = tmp_path / "src" / "app.py"

    result = runner.invoke(
        app,
        ["tool", "write", str(target), "--content", "print('hello')", "--json"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["success"] is True

    result = runner.invoke(
        app,
        ["tool", "read", str(target), "--json"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "print('hello')" in payload["content"]

    result = runner.invoke(
        app,
        [
            "tool",
            "edit",
            str(target),
            "--find",
            "hello",
            "--replace",
            "world",
            "--json",
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["success"] is True

    result = runner.invoke(
        app,
        ["tool", "read", str(target), "--json"],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "world" in payload["content"]
