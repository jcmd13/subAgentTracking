import json
from pathlib import Path

from src.core import session_manager
from src.core import activity_logger


def test_handoff_flow(tmp_path, monkeypatch):
    # Point data dir to temp
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(tmp_path / ".subagent"))

    # Start logger (auto-starts session manager)
    activity_logger.initialize()
    sid = activity_logger.get_current_session_id()
    assert sid

    # Save some state and create handoff
    session_manager.save_state({"progress": 42}, session_id=sid)
    handoff_path = session_manager.create_handoff(session_id=sid, reason="handoff", summary="handoff summary")
    assert handoff_path.exists()
    content = handoff_path.read_text()
    assert "handoff summary" in content
    assert sid in content

    # End session and ensure session file recorded
    session_manager.end_session(session_id=sid, status="completed", notes="done")
    session_file = (tmp_path / ".subagent" / "sessions" / f"{sid}.json")
    assert session_file.exists()
    data = json.loads(session_file.read_text())
    assert data["status"] == "completed"

    # Cleanup logger
    activity_logger.shutdown()
