"""MCP tool handlers for SubAgent."""

from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.bootstrap import ensure_initialized
from src.core.config import get_config
from src.core.activity_logger import list_log_files, get_current_session_id
from src.core.session_summary import generate_session_summary
from src.core.snapshot_manager import create_handoff_summary
from src.core.agent_registry import AgentRegistry, AgentStatus
from src.orchestration.agent_lifecycle import AgentLifecycle
from src.orchestration.agent_spawner import AgentSpawner


class MCPToolError(RuntimeError):
    """Raised when an MCP tool handler fails."""


def _ensure_init() -> None:
    ensure_initialized(prompt_if_needed=False, assume_yes=True)


def _tasks_path() -> Path:
    cfg = get_config(reload=True)
    return cfg.claude_dir / "tasks" / "tasks.json"


def _load_tasks() -> List[Dict[str, Any]]:
    tasks_path = _tasks_path()
    if not tasks_path.exists():
        return []
    try:
        return json.loads(tasks_path.read_text())
    except Exception:
        return []


def _save_tasks(tasks: List[Dict[str, Any]]) -> None:
    tasks_path = _tasks_path()
    tasks_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = tasks_path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(tasks, indent=2))
    tmp_path.replace(tasks_path)


def _next_task_id(tasks: List[Dict[str, Any]]) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"task_{ts}_{len(tasks) + 1:03d}"


def handle_subagent_status(*, verbose: bool = False) -> Dict[str, Any]:
    _ensure_init()
    cfg = get_config(reload=True)
    tasks = _load_tasks()
    logs = list_log_files()
    current_session = get_current_session_id()
    snapshot_count = len(list(cfg.state_dir.glob("session_*_snap*.json*")))

    registry = AgentRegistry()
    agents = registry.list_agents()
    active_agents = [a for a in agents if a.get("status") == AgentStatus.RUNNING.value]

    payload: Dict[str, Any] = {
        "project_root": str(cfg.project_root),
        "data_dir": str(cfg.claude_dir),
        "logs_dir": str(cfg.logs_dir),
        "state_dir": str(cfg.state_dir),
        "backup_enabled": getattr(cfg, "backup_enabled", False),
        "analytics_enabled": getattr(cfg, "analytics_enabled", False),
        "session_id_format": getattr(cfg, "session_id_format", "session_%Y%m%d_%H%M%S"),
        "current_session": current_session,
        "snapshots": snapshot_count,
        "tasks": {
            "count": len(tasks),
            "open": len([t for t in tasks if t.get("status") not in {"done", "completed"}]),
            "latest": tasks[-1]["id"] if tasks else None,
        },
        "agents": {
            "count": len(agents),
            "active": len(active_agents),
        },
        "logs": {
            "latest": logs[0]["file_path"] if logs else None,
            "count": len(logs),
        },
    }

    if verbose:
        payload["tasks"]["items"] = tasks
        payload["agents"]["items"] = agents
        payload["logs"]["items"] = logs

    return payload


def handle_subagent_task_create(
    *,
    title: str,
    description: str,
    acceptance_criteria: Optional[List[str]] = None,
    priority: Optional[int] = None,
    decompose: bool = True,
    constraints: Optional[Dict[str, Any]] = None,
    context: Optional[List[str]] = None,
    task_type: Optional[str] = None,
    deadline: Optional[str] = None,
) -> Dict[str, Any]:
    _ensure_init()
    tasks = _load_tasks()
    task_id = _next_task_id(tasks)
    payload = {
        "id": task_id,
        "title": title,
        "description": f"{title}: {description}",
        "priority": priority or 3,
        "type": task_type,
        "deadline": deadline,
        "acceptance_criteria": acceptance_criteria or [],
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": "pending",
        "context": context or [],
        "metadata": {
            "decompose": bool(decompose),
            "constraints": constraints or {},
        },
    }
    tasks.append(payload)
    _save_tasks(tasks)
    return {"created": True, "task": payload}


def handle_subagent_spawn(
    *,
    task_id: str,
    model: Optional[str] = None,
    budget_tokens: Optional[int] = None,
    budget_minutes: Optional[int] = None,
    permission_profile: Optional[str] = None,
) -> Dict[str, Any]:
    _ensure_init()
    spawner = AgentSpawner()
    budget: Dict[str, Any] = {}
    if budget_tokens is not None:
        budget["token_limit"] = budget_tokens
    if budget_minutes is not None:
        budget["time_limit_seconds"] = int(budget_minutes * 60)
    record = spawner.spawn(
        agent_type="worker",
        task_id=task_id,
        session_id=get_current_session_id(),
        model=model,
        reason="MCP spawn",
        budget=budget or None,
        permission_profile=permission_profile,
    )
    return {"spawned": True, "agent": record}


def handle_subagent_agent_control(
    *,
    agent_id: str,
    action: str,
    new_model: Optional[str] = None,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    _ensure_init()
    lifecycle = AgentLifecycle()
    action_lower = action.lower()
    agent: Optional[Dict[str, Any]] = None

    if action_lower == "pause":
        agent = lifecycle.pause_agent(agent_id, reason=reason)
    elif action_lower == "resume":
        agent = lifecycle.resume_agent(agent_id, reason=reason)
    elif action_lower == "kill":
        agent = lifecycle.terminate_agent(agent_id, reason=reason)
    elif action_lower == "switch_model":
        if not new_model:
            raise MCPToolError("new_model is required for switch_model")
        agent = lifecycle.switch_model(agent_id, new_model, reason=reason)
    else:
        raise MCPToolError(f"Unknown action: {action}")

    if not agent:
        raise MCPToolError(f"Agent not found: {agent_id}")

    return {"updated": True, "agent": agent}


def handle_subagent_review(
    *,
    task_id: str,
    include_diff: bool = True,
    include_quality: bool = True,
    max_diff_chars: int = 8000,
) -> Dict[str, Any]:
    _ensure_init()
    tasks = _load_tasks()
    task = next((item for item in tasks if item.get("id") == task_id), None)
    if not task:
        raise MCPToolError(f"Task not found: {task_id}")

    result: Dict[str, Any] = {"task": task}

    if include_diff:
        diff_text = ""
        try:
            diff = subprocess.run(
                ["git", "diff", "--no-color"],
                capture_output=True,
                text=True,
                check=False,
            )
            diff_text = diff.stdout or ""
        except Exception:
            diff_text = ""
        if len(diff_text) > max_diff_chars:
            diff_text = diff_text[:max_diff_chars].rstrip() + "..."
        result["diff"] = diff_text

    if include_quality:
        cfg = get_config(reload=True)
        latest_path = cfg.claude_dir / "quality" / "latest.json"
        if latest_path.exists():
            try:
                result["quality"] = json.loads(latest_path.read_text())
            except Exception:
                result["quality"] = None
        else:
            result["quality"] = None

    return result


def handle_subagent_handoff(
    *,
    reason: str,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    _ensure_init()
    handoff_path = create_handoff_summary(reason=reason)
    content = ""
    try:
        content = Path(handoff_path).read_text()
    except Exception:
        content = ""
    return {
        "handoff_path": str(handoff_path),
        "notes": notes,
        "content": content,
    }


def handle_subagent_metrics(*, scope: str = "session", compare_naive: bool = True) -> Dict[str, Any]:
    _ensure_init()
    summary = generate_session_summary()
    return {
        "scope": scope,
        "compare_naive": compare_naive,
        "summary": summary,
    }


__all__ = [
    "MCPToolError",
    "handle_subagent_status",
    "handle_subagent_task_create",
    "handle_subagent_spawn",
    "handle_subagent_agent_control",
    "handle_subagent_review",
    "handle_subagent_handoff",
    "handle_subagent_metrics",
]
