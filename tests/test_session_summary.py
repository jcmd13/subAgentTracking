import json

import pytest

from src.core.session_summary import generate_session_summary


@pytest.fixture
def temp_config(monkeypatch, tmp_path):
    from src.core.config import Config

    cfg = Config()
    cfg.logs_dir = tmp_path / "logs"
    cfg.state_dir = tmp_path / "state"
    cfg.analytics_dir = tmp_path / "analytics"

    cfg.logs_dir.mkdir(parents=True, exist_ok=True)
    cfg.state_dir.mkdir(parents=True, exist_ok=True)
    cfg.analytics_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("src.core.session_summary.get_config", lambda: cfg)
    return cfg


def test_generate_session_summary_with_log(temp_config):
    session_id = "session_20250101_000000"
    log_path = temp_config.logs_dir / f"{session_id}.jsonl"

    events = [
        {"event_type": "agent.invoked"},
        {"event_type": "agent.failed"},
        {"event_type": "tool.used"},
        {"event_type": "tool.error"},
        {"event_type": "task.started"},
        {"event_type": "task.completed"},
        {"event_type": "test.run_completed", "status": "passed"},
        {"event_type": "test.run_completed", "status": "failed"},
        {"event_type": "cost.tracked", "cost_usd": 1.2345},
    ]

    with open(log_path, "w", encoding="utf-8") as handle:
        for event in events:
            handle.write(json.dumps(event) + "\n")

    summary = generate_session_summary(session_id=session_id)
    data = summary["summary_data"]

    assert data["events_total"] == len(events)
    assert data["agents_invoked"] == 1
    assert data["agent_failures"] == 1
    assert data["tools_used"] == 1
    assert data["tool_errors"] == 1
    assert data["tasks_started"] == 1
    assert data["tasks_completed"] == 1
    assert data["tests_passed"] == 1
    assert data["tests_failed"] == 1
    assert data["cost_total"] == 1.2345
    assert f"Session: {session_id}" in summary["summary_text"]


def test_generate_session_summary_no_active_session(monkeypatch):
    monkeypatch.setattr("src.core.session_summary.get_current_session_id", lambda: None)
    summary = generate_session_summary(session_id=None)
    assert summary["summary_text"] == "No active session found."


def test_generate_session_summary_missing_log(temp_config):
    session_id = "session_20250101_000000"
    summary = generate_session_summary(session_id=session_id)
    assert summary["summary_text"] == f"No log file found for session {session_id}."
    assert summary["summary_data"]["session_id"] == session_id
