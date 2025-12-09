"""Session Manager for SubAgent Tracking System.

Provides lightweight persistent session tracking and crash-safe state storage.

Features:
- Unique session IDs (timestamp-based) with optional caller override
- Atomic session metadata persistence under .subagent/sessions/
- Crash-safe current-session pointer
- Simple state save/load helpers per session
- Handoff summary generation (Markdown) for multi-agent handoff

This module is additive and does not change existing runtime flows yet; callers
can opt-in via CLI or orchestration code to enable persistent session tracking.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

from src.core import config as core_config


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _atomic_write(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(path)


def _session_dir(cfg) -> Path:
    return cfg.claude_dir / "sessions"


def _current_file(cfg) -> Path:
    return _session_dir(cfg) / "current.json"


def _session_file(cfg, session_id: str) -> Path:
    return _session_dir(cfg) / f"{session_id}.json"


def generate_session_id(prefix: str = "session") -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}"


def start_session(session_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
    """Start a new session and persist metadata."""
    cfg = core_config.get_config()
    sid = session_id or generate_session_id()
    data = {
        "session_id": sid,
        "started_at": _now_iso(),
        "ended_at": None,
        "status": "active",
        "metadata": metadata or {},
    }
    _atomic_write(_session_file(cfg, sid), data)
    _atomic_write(_current_file(cfg), {"session_id": sid, "updated_at": _now_iso()})
    return sid


def end_session(session_id: Optional[str] = None, status: str = "completed", notes: Optional[str] = None) -> Dict[str, Any]:
    """End an existing session and persist final metadata."""
    cfg = core_config.get_config()
    sid = session_id or get_current_session_id()
    if not sid:
        return {"success": False, "error": "no_active_session"}
    session_path = _session_file(cfg, sid)
    if not session_path.exists():
        return {"success": False, "error": "session_not_found", "session_id": sid}
    data = json.loads(session_path.read_text())
    data["ended_at"] = _now_iso()
    data["status"] = status
    if notes:
        data.setdefault("metadata", {})["notes"] = notes
    _atomic_write(session_path, data)
    _atomic_write(_current_file(cfg), {"session_id": sid, "updated_at": _now_iso()})
    return {"success": True, "session_id": sid}


def get_current_session_id() -> Optional[str]:
    """Return the current session ID from the persisted pointer, if any."""
    cfg = core_config.get_config()
    current = _current_file(cfg)
    if current.exists():
        try:
            data = json.loads(current.read_text())
            return data.get("session_id")
        except Exception:
            return None
    return None


def list_sessions() -> List[Dict[str, Any]]:
    cfg = core_config.get_config()
    sessions = []
    for path in _session_dir(cfg).glob("session_*.json"):
        try:
            data = json.loads(path.read_text())
            data["path"] = str(path)
            sessions.append(data)
        except Exception:
            continue
    sessions.sort(key=lambda x: x.get("started_at", ""))
    return sessions


def save_state(state: Dict[str, Any], session_id: Optional[str] = None) -> Path:
    """Persist arbitrary state for a session (crash-safe)."""
    cfg = core_config.get_config()
    sid = session_id or get_current_session_id() or generate_session_id()
    state_dir = cfg.state_dir / sid
    state_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_dir / "state.json"
    _atomic_write(state_path, {"saved_at": _now_iso(), "state": state})
    return state_path


def load_state(session_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Load previously saved state for a session, if present."""
    cfg = core_config.get_config()
    sid = session_id or get_current_session_id()
    if not sid:
        return None
    state_path = cfg.state_dir / sid / "state.json"
    if not state_path.exists():
        return None
    try:
        data = json.loads(state_path.read_text())
        return data.get("state")
    except Exception:
        return None


def create_handoff(session_id: Optional[str] = None, reason: str = "handoff", summary: Optional[str] = None) -> Path:
    """Create a simple handoff markdown file for the given session."""
    cfg = core_config.get_config()
    sid = session_id or get_current_session_id() or generate_session_id()
    handoff_path = cfg.handoffs_dir / f"{sid}_{reason}.md"
    handoff_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Session Handoff: {sid}",
        "",
        f"- Reason: {reason}",
        f"- Created: {_now_iso()}",
    ]
    if summary:
        lines.extend(["", "## Summary", "", summary])
    state_path = cfg.state_dir / sid / "state.json"
    if state_path.exists():
        lines.extend(["", "## State", "", f"Stored at: {state_path}"])
    handoff_path.write_text("\n".join(lines))
    return handoff_path


__all__ = [
    "start_session",
    "end_session",
    "get_current_session_id",
    "list_sessions",
    "save_state",
    "load_state",
    "create_handoff",
    "generate_session_id",
]
