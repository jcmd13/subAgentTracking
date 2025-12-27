from src.core.agent_registry import AgentRegistry, AgentStatus
from src.orchestration.agent_monitor import AgentMonitor


def test_registry_create_and_update(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(tmp_path / ".subagent"))
    monkeypatch.setenv("SUBAGENT_CODEX_PROMPT_INSTALL", "false")

    registry = AgentRegistry()
    agent = registry.create_agent(agent_type="scout", model="model-x")
    assert agent["agent_id"].startswith("agent_")
    assert agent["status"] == AgentStatus.RUNNING.value

    fetched = registry.get_agent(agent["agent_id"])
    assert fetched["agent_type"] == "scout"

    updated = registry.update_agent(agent["agent_id"], status=AgentStatus.PAUSED)
    assert updated["status"] == AgentStatus.PAUSED.value


def test_registry_filters(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(tmp_path / ".subagent"))
    monkeypatch.setenv("SUBAGENT_CODEX_PROMPT_INSTALL", "false")

    registry = AgentRegistry()
    registry.create_agent(agent_type="scout", model="model-x", session_id="s1")
    registry.create_agent(agent_type="builder", model="model-y", session_id="s2")

    assert len(registry.list_agents(session_id="s1")) == 1
    assert len(registry.list_agents(agent_type="builder")) == 1


def test_monitor_budget_enforcement(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(tmp_path / ".subagent"))
    monkeypatch.setenv("SUBAGENT_CODEX_PROMPT_INSTALL", "false")

    registry = AgentRegistry()
    agent = registry.create_agent(
        agent_type="builder",
        model="model-z",
        budget={"token_limit": 5},
    )

    monitor = AgentMonitor(registry=registry)
    result = monitor.record_heartbeat(agent["agent_id"], metrics={"tokens_used": 10})
    assert result["terminated"] is True

    updated = registry.get_agent(agent["agent_id"])
    assert updated["status"] == AgentStatus.TERMINATED.value
