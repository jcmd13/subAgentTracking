import json
from pathlib import Path

from src.core import session_manager


def test_session_lifecycle(tmp_path, monkeypatch):
    # Point data dir to temp
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(tmp_path / ".subagent"))

    sid = session_manager.start_session(metadata={"owner": "tester"})
    assert sid.startswith("session_")

    # Current pointer is persisted
    current = session_manager.get_current_session_id()
    assert current == sid

    # Session file exists
    session_dir = tmp_path / ".subagent" / "sessions"
    session_file = session_dir / f"{sid}.json"
    assert session_file.exists()
    data = json.loads(session_file.read_text())
    assert data["status"] == "active"
    assert data["metadata"].get("owner") == "tester"

    # Save and load state
    state_path = session_manager.save_state({"foo": "bar"}, session_id=sid)
    assert state_path.exists()
    loaded = session_manager.load_state(session_id=sid)
    assert loaded == {"foo": "bar"}

    # End session
    result = session_manager.end_session(session_id=sid, status="completed", notes="done")
    assert result["success"] is True
    data = json.loads(session_file.read_text())
    assert data["status"] == "completed"
    assert data["metadata"].get("notes") == "done"


def test_handoff_creation(tmp_path, monkeypatch):
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(tmp_path / ".subagent"))
    sid = session_manager.start_session()
    # Save some state to reference
    session_manager.save_state({"a": 1}, session_id=sid)

    handoff_path = session_manager.create_handoff(session_id=sid, reason="handoff", summary="summary text")
    assert handoff_path.exists()
    content = handoff_path.read_text()
    assert sid in content
    assert "summary text" in content
    assert "state" in content.lower()
