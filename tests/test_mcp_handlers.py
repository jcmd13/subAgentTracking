from src.subagent.mcp.handlers import (
    handle_subagent_status,
    handle_subagent_task_create,
    handle_subagent_spawn,
    handle_subagent_agent_control,
    handle_subagent_metrics,
)


def _setup(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(tmp_path / ".subagent"))
    monkeypatch.setenv("SUBAGENT_CODEX_PROMPT_INSTALL", "false")


def test_mcp_task_create_and_status(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    result = handle_subagent_task_create(
        title="Add status",
        description="Expose status for MCP",
        acceptance_criteria=["Returns payload"],
    )
    assert result["created"] is True
    status = handle_subagent_status()
    assert status["tasks"]["count"] == 1


def test_mcp_spawn_and_control(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    task = handle_subagent_task_create(
        title="Spawn",
        description="Spawn agent",
    )["task"]
    spawn = handle_subagent_spawn(task_id=task["id"])
    agent_id = spawn["agent"]["agent_id"]
    control = handle_subagent_agent_control(agent_id=agent_id, action="pause")
    assert control["agent"]["status"] == "paused"


def test_mcp_metrics_returns_summary(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    metrics = handle_subagent_metrics()
    assert "summary" in metrics
