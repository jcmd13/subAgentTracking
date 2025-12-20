"""
Session Summary Generator

Creates lightweight session summaries from activity logs. Designed for quick
wins and dogfooding during development.
"""

import json
import gzip
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

from src.core.config import get_config
from src.core.event_types import (
    AGENT_INVOKED,
    AGENT_FAILED,
    TOOL_USED,
    TOOL_ERROR,
    COST_TRACKED,
    TASK_STARTED,
    TASK_COMPLETED,
    TEST_RUN_COMPLETED,
)
from src.core.session_manager import get_current_session_id


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _build_start_summary(session_id: Optional[str]) -> Dict[str, Any]:
    sid = session_id or get_current_session_id()
    if not sid:
        return {
            "summary_text": "No active session found.",
            "summary_data": {},
            "generated_at": _now_iso(),
        }

    return {
        "summary_text": f"Session started: {sid}",
        "summary_data": {
            "session_id": sid,
            "started_at": _now_iso(),
        },
        "generated_at": _now_iso(),
    }


def _find_log_path(session_id: str) -> Optional[Path]:
    cfg = get_config()
    candidates = [
        cfg.logs_dir / f"{session_id}.jsonl",
        cfg.logs_dir / f"{session_id}.jsonl.gz",
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def _iter_events(log_path: Path):
    open_func = gzip.open if log_path.suffix == ".gz" else open
    with open_func(log_path, "rt", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def generate_session_summary(
    session_id: Optional[str] = None,
    log_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    Generate a minimal session summary from activity logs.

    Returns a dict with summary_text and summary_data.
    """
    sid = session_id or get_current_session_id()
    if not sid:
        return {
            "summary_text": "No active session found.",
            "summary_data": {},
            "generated_at": _now_iso(),
        }

    path = log_path or _find_log_path(sid)
    if not path:
        return {
            "summary_text": f"No log file found for session {sid}.",
            "summary_data": {"session_id": sid},
            "generated_at": _now_iso(),
        }

    counts = {
        "events_total": 0,
        "agents_invoked": 0,
        "agent_failures": 0,
        "tools_used": 0,
        "tool_errors": 0,
        "tasks_started": 0,
        "tasks_completed": 0,
        "tests_passed": 0,
        "tests_failed": 0,
    }
    cost_total = 0.0

    for event in _iter_events(path):
        event_type = event.get("event_type")
        counts["events_total"] += 1

        if event_type == AGENT_INVOKED:
            counts["agents_invoked"] += 1
        elif event_type == AGENT_FAILED:
            counts["agent_failures"] += 1
        elif event_type == TOOL_USED:
            counts["tools_used"] += 1
        elif event_type == TOOL_ERROR:
            counts["tool_errors"] += 1
        elif event_type == TASK_STARTED:
            counts["tasks_started"] += 1
        elif event_type == TASK_COMPLETED:
            counts["tasks_completed"] += 1
        elif event_type == TEST_RUN_COMPLETED:
            status = event.get("status")
            if status == "passed":
                counts["tests_passed"] += 1
            elif status == "failed":
                counts["tests_failed"] += 1
        elif event_type == COST_TRACKED:
            cost_total += float(event.get("cost_usd") or event.get("cost") or 0.0)

    summary_lines = [
        f"Session: {sid}",
        f"Events: {counts['events_total']}",
        f"Agents: {counts['agents_invoked']} invoked, {counts['agent_failures']} failed",
        f"Tools: {counts['tools_used']} used, {counts['tool_errors']} errors",
        f"Tasks: {counts['tasks_started']} started, {counts['tasks_completed']} completed",
        f"Tests: {counts['tests_passed']} passed, {counts['tests_failed']} failed",
        f"Cost: ${cost_total:.4f}",
    ]

    return {
        "summary_text": "\n".join(summary_lines),
        "summary_data": {
            "session_id": sid,
            **counts,
            "cost_total": round(cost_total, 4),
        },
        "generated_at": _now_iso(),
    }


def publish_session_summary(
    summary_type: str,
    session_id: Optional[str] = None,
    log_path: Optional[Path] = None,
    summary_data_extra: Optional[Dict[str, Any]] = None,
    summary_text_override: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate and publish a session summary event.
    """
    if summary_type == "start":
        summary = _build_start_summary(session_id=session_id)
    else:
        summary = generate_session_summary(session_id=session_id, log_path=log_path)
        if summary.get("summary_text", "").startswith("No log file found"):
            sid = summary.get("summary_data", {}).get("session_id") or session_id
            if sid:
                summary["summary_text"] = f"Session ended: {sid}"
                summary["summary_data"] = {
                    **(summary.get("summary_data") or {}),
                    "session_id": sid,
                }
    if summary_text_override:
        summary["summary_text"] = summary_text_override
    if summary_data_extra:
        summary["summary_data"] = {
            **(summary.get("summary_data") or {}),
            **summary_data_extra,
        }

    try:
        from src.core.activity_logger_compat import log_session_summary
        event_id = log_session_summary(
            summary_type=summary_type,
            summary_text=summary["summary_text"],
            summary_data=summary["summary_data"],
            session_id=summary.get("summary_data", {}).get("session_id") or session_id,
        )
        summary["event_id"] = event_id
    except Exception:
        summary["event_id"] = None
    return summary


__all__ = [
    "generate_session_summary",
    "publish_session_summary",
]
