import json

from typer.testing import CliRunner

from src.subagent_cli.app import app


runner = CliRunner()


def test_cli_agent_lifecycle(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(tmp_path / ".subagent"))
    monkeypatch.setenv("SUBAGENT_CODEX_PROMPT_INSTALL", "false")

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0

    result = runner.invoke(
        app,
        [
            "agent",
            "spawn",
            "scout",
            "--model",
            "model-x",
            "--token-limit",
            "5",
            "--json",
        ],
    )
    assert result.exit_code == 0
    agent = json.loads(result.stdout)
    agent_id = agent["agent_id"]

    result = runner.invoke(app, ["agent", "list", "--json"])
    assert result.exit_code == 0
    agents = json.loads(result.stdout)
    assert any(a["agent_id"] == agent_id for a in agents)

    result = runner.invoke(app, ["agent", "pause", agent_id])
    assert result.exit_code == 0

    paused = json.loads(runner.invoke(app, ["agent", "show", agent_id, "--json"]).stdout)
    assert paused["status"] == "paused"

    result = runner.invoke(app, ["agent", "resume", agent_id])
    assert result.exit_code == 0

    resumed = json.loads(runner.invoke(app, ["agent", "show", agent_id, "--json"]).stdout)
    assert resumed["status"] == "running"

    result = runner.invoke(app, ["agent", "heartbeat", agent_id, "--tokens-used", "10"])
    assert result.exit_code == 0

    terminated = json.loads(runner.invoke(app, ["agent", "show", agent_id, "--json"]).stdout)
    assert terminated["status"] == "terminated"
