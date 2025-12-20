import json
from pathlib import Path
from typer.testing import CliRunner

from src.subagent_cli.app import app


runner = CliRunner()


def test_cli_session_commands(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(tmp_path / ".subagent"))

    # init
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0

    # start session
    result = runner.invoke(app, ["session-start", "--note", "test"], catch_exceptions=False)
    assert result.exit_code == 0
    session_id = None
    for line in result.stdout.splitlines():
        if line.startswith("Started session"):
            session_id = line.split(":")[-1].strip()
    assert session_id

    # list sessions
    result = runner.invoke(app, ["session-list", "--json"], catch_exceptions=False)
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data) == 1
    assert data[0]["session_id"] == session_id

    # end session
    result = runner.invoke(app, ["session-end", "--session-id", session_id, "--status", "completed"], catch_exceptions=False)
    assert result.exit_code == 0

    # confirm status updated
    sessions = json.loads(runner.invoke(app, ["session-list", "--json"], catch_exceptions=False).stdout)
    assert sessions[0]["status"] == "completed"
