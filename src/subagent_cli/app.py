import asyncio
import gzip
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Iterable
from collections import deque

import typer
import yaml

from src.core import config as core_config
from src.core.activity_logger import list_log_files
from src.core.activity_logger import get_current_session_id
from src.core.activity_logger_compat import (
    initialize as initialize_activity_logger,
    shutdown as shutdown_activity_logger,
    log_task_started,
    log_task_stage_changed,
    log_task_completed,
    log_test_run_started,
    log_test_run_completed,
    log_approval_granted,
    log_approval_denied,
)
from src.core.activity_logger_subscriber import (
    initialize_activity_logger_subscriber,
    shutdown_activity_logger_subscriber,
)
from src.core.agent_registry import AgentRegistry, AgentStatus
from src.core.bootstrap import ensure_initialized
from src.core.config import Config
from src.core import session_manager
from src.core.prd_state import prd_exists
from src.core.reference_checker import get_reference_checker
from src.core.approval_store import list_approvals, record_decision
from src.orchestration.agent_lifecycle import AgentLifecycle
from src.orchestration.agent_monitor import AgentMonitor
from src.orchestration.agent_spawner import AgentSpawner
from src.orchestration.permissions import PermissionManager
from src.orchestration.tool_proxy import ToolProxy
from src.orchestration.file_tools import FileToolProxy
from src.quality.runner import QualityGateRunner
from src.core.metrics_report import generate_metrics_report, render_metrics_markdown

app = typer.Typer(help="SubAgent Control CLI (Phase 1 skeleton)")
task_app = typer.Typer(help="Task management")
app.add_typer(task_app, name="task")
agent_app = typer.Typer(help="Agent lifecycle management")
app.add_typer(agent_app, name="agent")
tool_app = typer.Typer(help="Tool permission checks")
app.add_typer(tool_app, name="tool")
quality_app = typer.Typer(help="Quality gates")
app.add_typer(quality_app, name="quality")
approval_app = typer.Typer(help="Approval queue")
app.add_typer(approval_app, name="approval")
dashboard_app = typer.Typer(help="Dashboard server")
app.add_typer(dashboard_app, name="dashboard")
monitor_app = typer.Typer(help="Realtime WebSocket monitor")
app.add_typer(monitor_app, name="monitor")

_AUTO_SESSION_SKIP = {
    "init",
    "session-start",
    "session-end",
    "session-list",
    "metrics",
    "dashboard",
    "monitor",
    "help",
}

_DEFAULT_PERMISSIONS = {
    "permissions": {
        "default_profile": "default_worker",
        "profiles": {
            "default_worker": {
                "tools": ["read", "write", "edit", "provider"],
                "paths_allowed": ["src/**", "tests/**"],
                "paths_forbidden": [".env*", "*.secret", ".subagent/config.yaml"],
                "can_spawn_subagents": False,
                "can_modify_tests": False,
                "can_run_bash": False,
                "can_access_network": False,
            },
            "elevated": {
                "can_run_bash": True,
                "can_access_network": True,
            },
        },
    }
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_subagent_dirs() -> None:
    """Create the .subagent directory structure expected by the CLI."""
    root = Path(_load_config()["data_dir"])
    subdirs = [
        root,
        root / "config",
        root / "logs",
        root / "state",
        root / "sessions",
        root / "tasks",
        root / "handoffs",
        root / "quality",
        root / "approvals",
        root / "observability",
        root / "analytics",
        root / "credentials",
    ]
    for d in subdirs:
        d.mkdir(parents=True, exist_ok=True)
        gitkeep = d / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()


def _get_config_path() -> Path:
    data_dir_override = os.getenv("SUBAGENT_DATA_DIR")
    if data_dir_override:
        return Path(data_dir_override) / "config.yaml"
    return Path(".subagent") / "config.yaml"


def _get_tasks_file(config_values: Optional[Dict[str, Any]] = None) -> Path:
    cfg = config_values or _load_config()
    return Path(cfg["data_dir"]) / "tasks" / "tasks.json"


def _get_permissions_path(config_values: Optional[Dict[str, Any]] = None) -> Path:
    cfg = config_values or _load_config()
    return Path(cfg["data_dir"]) / "config" / "permissions.yaml"


def _get_observability_dir() -> Path:
    root = Path(_load_config()["data_dir"])
    obs_dir = root / "observability"
    obs_dir.mkdir(parents=True, exist_ok=True)
    return obs_dir


def _pid_path(name: str) -> Path:
    return _get_observability_dir() / f"{name}.pid"


def _log_path(name: str) -> Path:
    return _get_observability_dir() / f"{name}.log"


def _read_pid(pid_path: Path) -> Optional[int]:
    try:
        return int(pid_path.read_text().strip())
    except Exception:
        return None


def _pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _start_background(cmd: List[str], name: str) -> Optional[int]:
    pid_path = _pid_path(name)
    if pid_path.exists():
        pid = _read_pid(pid_path)
        if pid and _pid_running(pid):
            typer.echo(f"{name} already running (pid {pid}).")
            return None
        pid_path.unlink(missing_ok=True)

    log_path = _log_path(name)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = log_path.open("a", encoding="utf-8")
    proc = subprocess.Popen(
        cmd,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    log_file.close()
    pid_path.write_text(str(proc.pid))
    typer.echo(f"Started {name} (pid {proc.pid}). Logs: {log_path}")
    return proc.pid


def _stop_background(name: str) -> None:
    pid_path = _pid_path(name)
    pid = _read_pid(pid_path)
    if not pid:
        typer.echo(f"{name} is not running.")
        return
    if not _pid_running(pid):
        pid_path.unlink(missing_ok=True)
        typer.echo(f"{name} pid file removed (process not running).")
        return
    os.kill(pid, signal.SIGTERM)
    time.sleep(0.2)
    if _pid_running(pid):
        os.kill(pid, signal.SIGKILL)
    pid_path.unlink(missing_ok=True)
    typer.echo(f"Stopped {name} (pid {pid}).")

def _load_tasks() -> list[dict]:
    tasks_file = _get_tasks_file()
    if tasks_file.exists():
        try:
            return json.loads(tasks_file.read_text())
        except Exception:
            return []
    return []


def _save_tasks(tasks: list[dict]) -> None:
    tasks_file = _get_tasks_file()
    tasks_file.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = tasks_file.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(tasks, indent=2))
    tmp_path.replace(tasks_file)


def _next_task_id(tasks: list[dict]) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"task_{ts}_{len(tasks)+1:03d}"


def _load_config() -> Dict[str, Any]:
    """Load CLI config from YAML if present (with defaults)."""
    config_path = _get_config_path()
    defaults: Dict[str, Any] = {
        "task_defaults": {"priority": 3},
        "status": {"watch_interval": 2.0},
        "data_dir": str(config_path.parent),
    }
    if config_path.exists():
        try:
            data = yaml.safe_load(config_path.read_text()) or {}
            defaults.update(_validate_cli_config(data, defaults))
        except Exception:
            typer.echo(f"Warning: Failed to parse {config_path}, using defaults.")
    return defaults


def _load_core_config(reload: bool = False) -> Config:
    """
    Load core config (respects SUBAGENT_DATA_DIR and SUBAGENT_TRACKING_ROOT).

    Args:
        reload: Force reload of config module state
    """
    cfg = _load_config()
    os.environ.setdefault("SUBAGENT_DATA_DIR", cfg["data_dir"])
    return core_config.get_config(reload=reload)


def _validate_cli_config(config_data: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize CLI config values."""
    validated = defaults.copy()

    data_dir = config_data.get("data_dir", defaults["data_dir"])
    if isinstance(data_dir, str) and data_dir:
        validated["data_dir"] = data_dir

    task_defaults = config_data.get("task_defaults", {}) or {}
    priority = task_defaults.get("priority", defaults["task_defaults"]["priority"])
    if not isinstance(priority, int) or not (1 <= priority <= 5):
        priority = defaults["task_defaults"]["priority"]
    validated["task_defaults"]["priority"] = priority

    status_cfg = config_data.get("status", {}) or {}
    interval = status_cfg.get("watch_interval", defaults["status"]["watch_interval"])
    try:
        interval = float(interval)
        if interval <= 0:
            raise ValueError()
    except Exception:
        interval = defaults["status"]["watch_interval"]
    validated["status"]["watch_interval"] = interval

    return validated


def _save_default_config() -> None:
    config_path = _get_config_path()
    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            yaml.safe_dump(
                {
                    "task_defaults": {"priority": 3},
                    "status": {"watch_interval": 2.0},
                }
            )
        )


def _write_permissions_template() -> None:
    permissions_path = _get_permissions_path()
    if permissions_path.exists():
        return
    permissions_path.parent.mkdir(parents=True, exist_ok=True)
    permissions_path.write_text(yaml.safe_dump(_DEFAULT_PERMISSIONS))


def _should_auto_session(command: Optional[str]) -> bool:
    if not command:
        return False
    return command not in _AUTO_SESSION_SKIP


def _get_active_session_id(cfg: Config) -> Optional[str]:
    session_id = session_manager.get_current_session_id()
    if not session_id:
        return None
    session_path = cfg.claude_dir / "sessions" / f"{session_id}.json"
    if not session_path.exists():
        return None
    try:
        data = json.loads(session_path.read_text())
    except Exception:
        return None
    if data.get("status") == "active" and not data.get("ended_at"):
        return session_id
    return None


def _run_async(coro) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(coro)
    else:
        loop.create_task(coro)


def _flush_activity_logger_subscriber() -> None:
    try:
        _run_async(shutdown_activity_logger_subscriber())
    except Exception:
        return


def _maybe_run_reference_check(
    agent: str,
    trigger: str,
    context: Optional[str] = None,
) -> None:
    if not prd_exists():
        return
    checker = get_reference_checker()
    if not checker:
        return
    requirements = checker.get_relevant_requirements(
        current_context=context,
        max_items=5,
    )
    prompt = checker.generate_reference_prompt(requirements, trigger)
    requirement_ids = [req.get("id") for req in requirements if req.get("id")]
    checker.log_reference(
        requirement_ids=requirement_ids,
        agent=agent,
        trigger=trigger,
        context=context,
    )
    typer.echo(prompt, err=True)


def _start_cli_session(command: Optional[str]) -> Dict[str, Any]:
    cfg = _load_core_config(reload=True)
    ensure_initialized(prompt_if_needed=True)

    active_session_id = _get_active_session_id(cfg)
    auto_started = False
    if active_session_id:
        session_id = active_session_id
    else:
        session_id = session_manager.start_session(
            metadata={"source": "cli", "command": command or "unknown"}
        )
        auto_started = True

    if cfg.activity_log_enabled:
        initialize_activity_logger_subscriber(
            session_id=session_id,
            use_compression=cfg.activity_log_compression,
        )
    initialize_activity_logger(session_id=session_id)
    _maybe_run_reference_check(
        agent="local-cli",
        trigger="cli_start",
        context=command,
    )

    return {"session_id": session_id, "auto_started": auto_started}


def _end_cli_session(state: Optional[Dict[str, Any]]) -> None:
    if not state:
        return
    session_id = state.get("session_id")
    auto_started = state.get("auto_started", False)

    if auto_started and session_id:
        shutdown_activity_logger(session_id=session_id)
        session_manager.end_session(
            session_id=session_id,
            status="completed",
            notes="cli_auto_end",
        )

    _flush_activity_logger_subscriber()


# ---------------------------------------------------------------------------
# Event Emission Helpers
# ---------------------------------------------------------------------------


def _resolve_session_id(session_id: Optional[str]) -> Optional[str]:
    return session_id or session_manager.get_current_session_id()


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.callback()
def _cli_callback(ctx: typer.Context) -> None:
    command = ctx.invoked_subcommand
    if not _should_auto_session(command):
        return
    state = _start_cli_session(command)
    ctx.call_on_close(lambda: _end_cli_session(state))


@app.command()
def init() -> None:
    """
    Initialize local SubAgent directories (.subagent/).
    """
    cfg = _load_config()
    os.environ.setdefault("SUBAGENT_DATA_DIR", cfg["data_dir"])
    _ensure_subagent_dirs()
    _save_default_config()
    _write_permissions_template()
    typer.echo(f"Initialized {Path(cfg['data_dir']).resolve()} directory structure.")


@app.command("session-start")
def session_start(
    session_id: Optional[str] = typer.Option(None, "--session-id", help="Custom session ID"),
    note: Optional[str] = typer.Option(None, "--note", "-n", help="Metadata note"),
) -> None:
    """Start a new session and persist metadata."""
    cfg = _load_core_config(reload=True)
    ensure_initialized(prompt_if_needed=True)
    meta = {"note": note} if note else {}
    sid = session_manager.start_session(session_id=session_id, metadata=meta)
    if cfg.activity_log_enabled:
        initialize_activity_logger_subscriber(
            session_id=sid,
            use_compression=cfg.activity_log_compression,
        )
    initialize_activity_logger(session_id=sid)
    _maybe_run_reference_check(
        agent="local-cli",
        trigger="session_start",
        context=note,
    )
    typer.echo(f"Started session: {sid}")


@app.command("session-end")
def session_end(
    session_id: Optional[str] = typer.Option(None, "--session-id", help="Session ID to end"),
    status: str = typer.Option("completed", "--status", "-s", help="Final status"),
    note: Optional[str] = typer.Option(None, "--note", "-n", help="Notes"),
) -> None:
    """End a session and mark status."""
    _load_core_config(reload=True)
    result = session_manager.end_session(session_id=session_id, status=status, notes=note)
    if not result.get("success"):
        typer.echo(f"Failed to end session: {result.get('error')}")
        raise typer.Exit(code=1)
    shutdown_activity_logger(session_id=result.get("session_id"))
    _flush_activity_logger_subscriber()
    typer.echo(f"Ended session: {result['session_id']}")


@app.command("session-list")
def session_list(json_output: bool = typer.Option(False, "--json", help="Output JSON")) -> None:
    """List persisted sessions."""
    _load_core_config(reload=True)
    sessions = session_manager.list_sessions()
    if json_output:
        typer.echo(json.dumps(sessions, indent=2))
    else:
        if not sessions:
            typer.echo("No sessions found.")
            return
        for s in sessions:
            typer.echo(f"{s.get('session_id')} [{s.get('status')}] started={s.get('started_at')} ended={s.get('ended_at')}")


@app.command()
def status(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
    watch: bool = typer.Option(False, "--watch", "-w", help="Continuously refresh status"),
    interval: float = typer.Option(None, "--interval", "-i", help="Seconds between updates when watching"),
) -> None:
    """
    Show current system status.
    """
    cli_cfg = _load_config()
    cfg = _load_core_config()

    def render() -> None:
        cfg_local = _load_core_config(reload=True)
        tasks = _load_tasks()
        logs = list_log_files()
        latest_log = logs[0]["file_path"] if logs else None
        current_session = get_current_session_id()
        snapshot_count = len(list(cfg_local.state_dir.glob("session_*_snap*.json*")))
        payload = {
            "project_root": str(cfg_local.project_root),
            "logs_dir": str(cfg_local.logs_dir),
            "state_dir": str(cfg_local.state_dir),
            "backup_enabled": getattr(cfg_local, "backup_enabled", False),
            "analytics_enabled": getattr(cfg_local, "analytics_enabled", False),
            "session_id_format": getattr(cfg_local, "session_id_format", "session_%Y%m%d_%H%M%S"),
            "current_session": current_session,
            "snapshots": snapshot_count,
            "tasks": {
                "count": len(tasks),
                "open": len([t for t in tasks if t.get("status") != "done"]),
                "latest": tasks[-1]["id"] if tasks else None,
            },
            "logs": {
                "latest": str(latest_log) if latest_log else None,
                "count": len(logs),
            },
        }
        if json_output:
            typer.echo(json.dumps(payload, indent=2))
        else:
            typer.echo(f"Project root:      {payload['project_root']}")
            typer.echo(f"Logs dir:          {payload['logs_dir']}")
            typer.echo(f"State dir:         {payload['state_dir']}")
            typer.echo(f"Backup enabled:    {payload['backup_enabled']}")
            typer.echo(f"Analytics enabled: {payload['analytics_enabled']}")
            typer.echo(f"Session ID format: {payload['session_id_format']}")
            typer.echo(f"Current session:   {payload['current_session'] or 'none'}")
            typer.echo(f"Snapshots:         {payload['snapshots']}")
            typer.echo(f"Tasks:             {payload['tasks']['count']} total, {payload['tasks']['open']} open")
            if payload["tasks"]["latest"]:
                typer.echo(f"Latest task:       {payload['tasks']['latest']}")
            if payload["logs"]["latest"]:
                typer.echo(f"Latest log:        {payload['logs']['latest']}")

    if watch:
        try:
            refresh = interval or cli_cfg["status"]["watch_interval"]
            while True:
                typer.clear()
                render()
                time.sleep(refresh)
        except KeyboardInterrupt:
            return
    else:
        render()


@app.command("metrics")
def metrics(
    scope: str = typer.Option("session", "--scope", help="Scope: session, task, project"),
    session_id: Optional[str] = typer.Option(None, "--session-id", help="Session ID (session scope)"),
    task_id: Optional[str] = typer.Option(None, "--task-id", help="Task ID (task scope)"),
    compare: bool = typer.Option(True, "--compare/--no-compare", help="Include naive comparison"),
    export: Optional[Path] = typer.Option(None, "--export", "-e", help="Write markdown report"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Show cost and quality metrics."""
    _load_core_config(reload=True)
    try:
        report = generate_metrics_report(
            scope=scope,
            session_id=session_id,
            task_id=task_id,
            compare_naive=compare,
        )
    except ValueError as exc:
        typer.echo(f"Error: {exc}")
        raise typer.Exit(code=1)

    if export:
        export_path = Path(export)
        export_path.parent.mkdir(parents=True, exist_ok=True)
        export_path.write_text(render_metrics_markdown(report))
        if not json_output:
            typer.echo(f"Wrote report to {export_path}")

    if json_output:
        typer.echo(json.dumps(report, indent=2))
        return

    metrics_payload = report.get("metrics", {})
    cost = metrics_payload.get("cost", {})
    tokens = metrics_payload.get("tokens", {})
    tasks = metrics_payload.get("tasks", {})
    tests = metrics_payload.get("tests", {})
    agents = metrics_payload.get("agents", {})
    quality = report.get("quality", {}) or {}
    naive = report.get("naive_comparison") or {}

    typer.echo(f"Scope:            {report.get('scope')}")
    if report.get("session_id"):
        typer.echo(f"Session:          {report.get('session_id')}")
    if report.get("task_id"):
        typer.echo(f"Task:             {report.get('task_id')}")
    typer.echo(f"Events:           {metrics_payload.get('events_total', 0)}")
    typer.echo(f"Agents:           {agents.get('completed', 0)} completed, {agents.get('failed', 0)} failed")
    typer.echo(f"Tasks:            {tasks.get('started', 0)} started, {tasks.get('completed', 0)} completed")
    typer.echo(f"Tests:            {tests.get('passed', 0)} passed, {tests.get('failed', 0)} failed")
    typer.echo(f"Tokens:           {tokens.get('total', 0)} total")
    typer.echo(f"Cost:             ${cost.get('total', 0.0)} ({cost.get('source', 'none')})")
    if naive:
        savings = naive.get("savings_pct")
        savings_label = f"{savings}%" if savings is not None else "n/a"
        typer.echo(
            f"Naive cost:       ${naive.get('naive_cost')} "
            f"(x{naive.get('naive_multiplier')}, savings {savings_label})"
        )
    if quality:
        typer.echo(f"Quality reports:  {quality.get('report_count', 0)}")


def _render_task(task: dict, json_output: bool = False) -> None:
    if json_output:
        typer.echo(json.dumps(task, indent=2))
        return

    typer.echo(f"{task.get('id')} [{task.get('status', 'pending')}]")
    typer.echo(f"  desc:      {task.get('description')}")
    typer.echo(f"  priority:  {task.get('priority')}")
    if task.get("type"):
        typer.echo(f"  type:      {task.get('type')}")
    if task.get("deadline"):
        typer.echo(f"  deadline:  {task.get('deadline')}")
    if task.get("acceptance_criteria"):
        typer.echo("  criteria:")
        for c in task.get("acceptance_criteria", []):
            typer.echo(f"    - {c}")
    if task.get("context"):
        typer.echo("  context:")
        for c in task.get("context", []):
            typer.echo(f"    - {c}")
    if task.get("created_at"):
        typer.echo(f"  created:   {task.get('created_at')}")
    if task.get("status"):
        typer.echo(f"  status:    {task.get('status')}")


def _render_agent(agent: dict, json_output: bool = False) -> None:
    if json_output:
        typer.echo(json.dumps(agent, indent=2))
        return

    typer.echo(f"{agent.get('agent_id')} [{agent.get('status', 'unknown')}]")
    typer.echo(f"  type:      {agent.get('agent_type')}")
    typer.echo(f"  model:     {agent.get('model')}")
    if agent.get("session_id"):
        typer.echo(f"  session:   {agent.get('session_id')}")
    if agent.get("task_id"):
        typer.echo(f"  task:      {agent.get('task_id')}")
    if agent.get("started_at"):
        typer.echo(f"  started:   {agent.get('started_at')}")
    if agent.get("completed_at"):
        typer.echo(f"  completed: {agent.get('completed_at')}")
    if agent.get("last_heartbeat"):
        typer.echo(f"  heartbeat: {agent.get('last_heartbeat')}")


@app.command("task-add")
def task_add(
    description: str = typer.Argument(..., help="Task description"),
    priority: int = typer.Option(None, "--priority", "-p", help="Priority 1-5"),
    task_type: Optional[str] = typer.Option(None, "--type", "-t", help="Task type/category"),
    deadline: Optional[str] = typer.Option(None, "--deadline", "-d", help="Deadline (ISO date/time or freeform)"),
    criteria: List[str] = typer.Option([], "--acceptance", "-a", help="Acceptance criteria (repeatable)"),
    status: str = typer.Option("pending", "--status", "-s", help="Task status"),
    context: List[str] = typer.Option([], "--context", "-c", help="Additional context/notes (repeatable)"),
) -> None:
    """
    Create a new task in .subagent/tasks/tasks.json.
    """
    _ensure_subagent_dirs()
    config_values = _load_config()
    tasks = _load_tasks()
    task_id = _next_task_id(tasks)
    tasks.append(
        {
            "id": task_id,
            "description": description,
            "priority": priority or config_values["task_defaults"].get("priority", 3),
            "type": task_type,
            "deadline": deadline,
            "acceptance_criteria": criteria,
            "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": status,
            "context": context,
        }
    )
    _save_tasks(tasks)
    typer.echo(f"Created task {task_id}: {description}")


@app.command("task-update")
def task_update(
    task_id: str = typer.Argument(..., help="Task ID"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="New status"),
    priority: Optional[int] = typer.Option(None, "--priority", "-p", help="Priority 1-5"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Updated description"),
    task_type: Optional[str] = typer.Option(None, "--type", "-t", help="Task type/category"),
    deadline: Optional[str] = typer.Option(None, "--deadline", help="Deadline (ISO date/time or freeform)"),
    criteria: List[str] = typer.Option([], "--acceptance", "-a", help="Replace acceptance criteria (repeatable)"),
    context: List[str] = typer.Option([], "--context", "-c", help="Replace context notes (repeatable)"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Update a task's status/priority/description."""
    tasks = _load_tasks()
    updated = False
    for task in tasks:
        if task.get("id") == task_id:
            if status:
                task["status"] = status
            if priority is not None and 1 <= priority <= 5:
                task["priority"] = priority
            if description:
                task["description"] = description
            if task_type is not None:
                task["type"] = task_type
            if deadline is not None:
                task["deadline"] = deadline
            if criteria:
                task["acceptance_criteria"] = criteria
            if context:
                task["context"] = context
            updated = True
            break
    if not updated:
        typer.echo(f"Task not found: {task_id}")
        raise typer.Exit(code=1)
    _save_tasks(tasks)
    if json_output:
        typer.echo(json.dumps({"updated": task_id}, indent=2))
    else:
        typer.echo(f"Updated {task_id}")


@app.command("task-complete")
def task_complete(task_id: str = typer.Argument(..., help="Task ID")) -> None:
    """Mark a task as done."""
    tasks = _load_tasks()
    for task in tasks:
        if task.get("id") == task_id:
            task["status"] = "done"
            task["completed_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            _save_tasks(tasks)
            typer.echo(f"Completed {task_id}")
            return
    typer.echo(f"Task not found: {task_id}")
    raise typer.Exit(code=1)


@app.command("task-list")
def task_list(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    open_only: bool = typer.Option(False, "--open", help="Show only non-done tasks"),
) -> None:
    """List tasks stored in .subagent/tasks/tasks.json."""
    tasks = _load_tasks()
    if open_only:
        tasks = [t for t in tasks if t.get("status") != "done"]
    if status:
        tasks = [t for t in tasks if t.get("status") == status]

    if json_output:
        typer.echo(json.dumps(tasks, indent=2))
    else:
        if not tasks:
            typer.echo("No tasks found.")
            return
        for task in tasks:
            _render_task(task, json_output=False)
            typer.echo("")


@app.command("task-show")
def task_show(
    task_id: str = typer.Argument(..., help="Task ID to show"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Show a single task by ID."""
    tasks = _load_tasks()
    task = next((t for t in tasks if t.get("id") == task_id), None)
    if not task:
        typer.echo(f"Task not found: {task_id}")
        raise typer.Exit(code=1)
    _render_task(task, json_output=json_output)


@task_app.command("add")
def task_add_group(
    description: str = typer.Argument(..., help="Task description"),
    priority: int = typer.Option(None, "--priority", "-p", help="Priority 1-5"),
    task_type: Optional[str] = typer.Option(None, "--type", "-t", help="Task type/category"),
    deadline: Optional[str] = typer.Option(None, "--deadline", "-d", help="Deadline (ISO date/time or freeform)"),
    criteria: List[str] = typer.Option([], "--acceptance", "-a", help="Acceptance criteria (repeatable)"),
    status: str = typer.Option("pending", "--status", "-s", help="Task status"),
    context: List[str] = typer.Option([], "--context", "-c", help="Additional context/notes (repeatable)"),
) -> None:
    """Create a new task."""
    task_add(
        description=description,
        priority=priority,
        task_type=task_type,
        deadline=deadline,
        criteria=criteria,
        status=status,
        context=context,
    )


@task_app.command("update")
def task_update_group(
    task_id: str = typer.Argument(..., help="Task ID"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="New status"),
    priority: Optional[int] = typer.Option(None, "--priority", "-p", help="Priority 1-5"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Updated description"),
    task_type: Optional[str] = typer.Option(None, "--type", "-t", help="Task type/category"),
    deadline: Optional[str] = typer.Option(None, "--deadline", help="Deadline (ISO date/time or freeform)"),
    criteria: List[str] = typer.Option([], "--acceptance", "-a", help="Replace acceptance criteria (repeatable)"),
    context: List[str] = typer.Option([], "--context", "-c", help="Replace context notes (repeatable)"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Update a task."""
    task_update(
        task_id=task_id,
        status=status,
        priority=priority,
        description=description,
        task_type=task_type,
        deadline=deadline,
        criteria=criteria,
        context=context,
        json_output=json_output,
    )


@task_app.command("complete")
def task_complete_group(task_id: str = typer.Argument(..., help="Task ID")) -> None:
    """Mark a task as done."""
    task_complete(task_id=task_id)


@task_app.command("list")
def task_list_group(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    open_only: bool = typer.Option(False, "--open", help="Show only non-done tasks"),
) -> None:
    """List tasks."""
    task_list(json_output=json_output, status=status, open_only=open_only)


@task_app.command("show")
def task_show_group(
    task_id: str = typer.Argument(..., help="Task ID to show"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Show a single task by ID."""
    task_show(task_id=task_id, json_output=json_output)


@approval_app.command("list")
def approval_list(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    show_all: bool = typer.Option(False, "--all", help="Show all approvals"),
) -> None:
    """List approval requests."""
    if show_all:
        status = None
    elif status is None:
        status = "required"
    approvals = list_approvals(status=status)
    if json_output:
        typer.echo(json.dumps(approvals, indent=2))
        return
    if not approvals:
        typer.echo("No approvals found.")
        return
    for approval in approvals:
        approval_id = approval.get("approval_id", "--")
        approval_status = approval.get("status", "unknown")
        tool = approval.get("tool", "unknown")
        operation = approval.get("operation")
        file_path = approval.get("file_path")
        risk = approval.get("risk_score")
        line_parts = [f"{approval_id} [{approval_status}]", tool]
        if operation:
            line_parts.append(operation)
        if file_path:
            line_parts.append(file_path)
        if risk is not None:
            line_parts.append(f"risk={risk:.2f}")
        typer.echo(" ".join(line_parts))


@approval_app.command("approve")
def approval_approve(
    approval_id: str = typer.Argument(..., help="Approval ID"),
    actor: Optional[str] = typer.Option("user", "--actor", help="Decision actor"),
    reason: Optional[str] = typer.Option(None, "--reason", "-r", help="Decision rationale"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Approve a pending approval request."""
    try:
        record = record_decision(approval_id, "granted", actor=actor, reason=reason)
    except ValueError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)
    if not record:
        typer.echo(f"Approval not found: {approval_id}")
        raise typer.Exit(code=1)
    decision = record.decision or {}
    try:
        log_approval_granted(
            approval_id=record.approval_id,
            actor=actor,
            reason=reason,
            tool=record.tool,
            operation=record.operation,
            file_path=record.file_path,
            risk_score=record.risk_score,
            reasons=record.reasons,
            summary=record.summary,
            decided_at=decision.get("decided_at"),
            session_id=_resolve_session_id(None),
        )
    except Exception:
        pass
    if json_output:
        typer.echo(json.dumps(record.to_dict(), indent=2))
    else:
        typer.echo(f"Approved {record.approval_id}")


@approval_app.command("deny")
def approval_deny(
    approval_id: str = typer.Argument(..., help="Approval ID"),
    actor: Optional[str] = typer.Option("user", "--actor", help="Decision actor"),
    reason: Optional[str] = typer.Option(None, "--reason", "-r", help="Decision rationale"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Deny a pending approval request."""
    try:
        record = record_decision(approval_id, "denied", actor=actor, reason=reason)
    except ValueError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)
    if not record:
        typer.echo(f"Approval not found: {approval_id}")
        raise typer.Exit(code=1)
    decision = record.decision or {}
    try:
        log_approval_denied(
            approval_id=record.approval_id,
            actor=actor,
            reason=reason,
            tool=record.tool,
            operation=record.operation,
            file_path=record.file_path,
            risk_score=record.risk_score,
            reasons=record.reasons,
            summary=record.summary,
            decided_at=decision.get("decided_at"),
            session_id=_resolve_session_id(None),
        )
    except Exception:
        pass
    if json_output:
        typer.echo(json.dumps(record.to_dict(), indent=2))
    else:
        typer.echo(f"Denied {record.approval_id}")


@agent_app.command("spawn")
def agent_spawn(
    agent_type: str = typer.Argument(..., help="Agent type"),
    task_id: Optional[str] = typer.Option(None, "--task-id", help="Related task ID"),
    session_id: Optional[str] = typer.Option(None, "--session-id", help="Session ID"),
    model: Optional[str] = typer.Option(None, "--model", help="Model name override"),
    invoked_by: str = typer.Option("user", "--invoked-by", help="Invoker name"),
    reason: str = typer.Option("Manual agent spawn", "--reason", help="Spawn reason"),
    task_type: Optional[str] = typer.Option(None, "--task-type", help="Task type for routing"),
    context_tokens: int = typer.Option(0, "--context-tokens", help="Estimated context tokens"),
    files: List[str] = typer.Option([], "--file", "-f", help="Context files (repeatable)"),
    token_limit: Optional[int] = typer.Option(None, "--token-limit", help="Token budget"),
    time_limit: Optional[int] = typer.Option(None, "--time-limit", help="Time budget (seconds)"),
    cost_limit: Optional[float] = typer.Option(None, "--cost-limit", help="Cost budget (USD)"),
    heartbeat_interval: Optional[int] = typer.Option(None, "--heartbeat-interval", help="Expected heartbeat interval (seconds)"),
    heartbeat_timeout: Optional[int] = typer.Option(None, "--heartbeat-timeout", help="Heartbeat timeout (seconds)"),
    sla_timeout: Optional[int] = typer.Option(None, "--sla-timeout", help="SLA timeout (seconds)"),
    permission_profile: Optional[str] = typer.Option(None, "--permission-profile", help="Permission profile name"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Spawn a new agent record."""
    _load_core_config(reload=True)
    spawner = AgentSpawner()
    budget: Dict[str, Any] = {}
    if token_limit is not None:
        budget["token_limit"] = token_limit
    if time_limit is not None:
        budget["time_limit_seconds"] = time_limit
    if cost_limit is not None:
        budget["cost_limit_usd"] = cost_limit
    if heartbeat_interval is not None:
        budget["heartbeat_interval_seconds"] = heartbeat_interval
    if heartbeat_timeout is not None:
        budget["heartbeat_timeout_seconds"] = heartbeat_timeout
    if sla_timeout is not None:
        budget["sla_timeout_seconds"] = sla_timeout
    record = spawner.spawn(
        agent_type=agent_type,
        task_id=task_id,
        session_id=_resolve_session_id(session_id),
        model=model,
        invoked_by=invoked_by,
        reason=reason,
        task_type=task_type,
        context_tokens=context_tokens,
        files=files,
        budget=budget or None,
        permission_profile=permission_profile,
    )
    if json_output:
        typer.echo(json.dumps(record, indent=2))
    else:
        typer.echo(f"Spawned agent {record['agent_id']} ({record['agent_type']})")


@agent_app.command("list")
def agent_list(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
    status: Optional[AgentStatus] = typer.Option(None, "--status", help="Filter by status"),
    session_id: Optional[str] = typer.Option(None, "--session-id", help="Filter by session ID"),
    agent_type: Optional[str] = typer.Option(None, "--type", help="Filter by agent type"),
) -> None:
    """List agent records."""
    _load_core_config(reload=True)
    registry = AgentRegistry()
    agents = registry.list_agents(
        status=status.value if status else None,
        session_id=session_id,
        agent_type=agent_type,
    )
    if json_output:
        typer.echo(json.dumps(agents, indent=2))
        return
    if not agents:
        typer.echo("No agents found.")
        return
    for agent in agents:
        _render_agent(agent, json_output=False)
        typer.echo("")


@agent_app.command("show")
def agent_show(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Show a single agent record."""
    _load_core_config(reload=True)
    registry = AgentRegistry()
    agent = registry.get_agent(agent_id)
    if not agent:
        typer.echo(f"Agent not found: {agent_id}")
        raise typer.Exit(code=1)
    _render_agent(agent, json_output=json_output)


@agent_app.command("pause")
def agent_pause(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    reason: Optional[str] = typer.Option(None, "--reason", help="Pause reason"),
) -> None:
    """Pause an agent."""
    _load_core_config(reload=True)
    lifecycle = AgentLifecycle()
    agent = lifecycle.pause_agent(agent_id, reason=reason)
    if not agent:
        typer.echo(f"Agent not found: {agent_id}")
        raise typer.Exit(code=1)
    typer.echo(f"Paused {agent_id}")


@agent_app.command("resume")
def agent_resume(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    reason: Optional[str] = typer.Option(None, "--reason", help="Resume reason"),
) -> None:
    """Resume a paused agent."""
    _load_core_config(reload=True)
    lifecycle = AgentLifecycle()
    agent = lifecycle.resume_agent(agent_id, reason=reason)
    if not agent:
        typer.echo(f"Agent not found: {agent_id}")
        raise typer.Exit(code=1)
    typer.echo(f"Resumed {agent_id}")


@agent_app.command("terminate")
def agent_terminate(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    reason: Optional[str] = typer.Option(None, "--reason", help="Termination reason"),
) -> None:
    """Terminate an agent."""
    _load_core_config(reload=True)
    lifecycle = AgentLifecycle()
    agent = lifecycle.terminate_agent(agent_id, reason=reason)
    if not agent:
        typer.echo(f"Agent not found: {agent_id}")
        raise typer.Exit(code=1)
    typer.echo(f"Terminated {agent_id}")


@agent_app.command("switch-model")
def agent_switch_model(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    model: str = typer.Argument(..., help="New model name"),
    reason: Optional[str] = typer.Option(None, "--reason", help="Switch reason"),
) -> None:
    """Switch an agent's model."""
    _load_core_config(reload=True)
    lifecycle = AgentLifecycle()
    agent = lifecycle.switch_model(agent_id, model, reason=reason)
    if not agent:
        typer.echo(f"Agent not found: {agent_id}")
        raise typer.Exit(code=1)
    typer.echo(f"Switched {agent_id} to {model}")


@agent_app.command("heartbeat")
def agent_heartbeat(
    agent_id: str = typer.Argument(..., help="Agent ID"),
    tokens_used: Optional[int] = typer.Option(None, "--tokens-used", help="Tokens used"),
    input_tokens: Optional[int] = typer.Option(None, "--input-tokens", help="Input tokens"),
    output_tokens: Optional[int] = typer.Option(None, "--output-tokens", help="Output tokens"),
    elapsed_seconds: Optional[int] = typer.Option(None, "--elapsed-seconds", help="Elapsed seconds"),
    cost_usd: Optional[float] = typer.Option(None, "--cost-usd", help="Cost in USD"),
    note: Optional[str] = typer.Option(None, "--note", help="Heartbeat note"),
) -> None:
    """Record a heartbeat and enforce budgets."""
    _load_core_config(reload=True)
    metrics: Dict[str, Any] = {}
    if tokens_used is not None:
        metrics["tokens_used"] = tokens_used
    if input_tokens is not None:
        metrics["input_tokens"] = input_tokens
    if output_tokens is not None:
        metrics["output_tokens"] = output_tokens
    if elapsed_seconds is not None:
        metrics["elapsed_seconds"] = elapsed_seconds
    if cost_usd is not None:
        metrics["cost_usd"] = cost_usd
    monitor = AgentMonitor()
    result = monitor.record_heartbeat(agent_id, metrics=metrics or None, note=note)
    if not result.get("success"):
        typer.echo(f"Agent not found: {agent_id}")
        raise typer.Exit(code=1)
    if result.get("terminated"):
        typer.echo(f"Agent {agent_id} terminated (budget exceeded)")
    else:
        typer.echo(f"Heartbeat recorded for {agent_id}")


@tool_app.command("check")
def tool_check(
    tool: str = typer.Argument(..., help="Tool name"),
    operation: Optional[str] = typer.Option(None, "--operation", help="Tool operation"),
    path: Optional[str] = typer.Option(None, "--path", help="Target path"),
    requires_network: bool = typer.Option(False, "--network", help="Requires network"),
    requires_bash: bool = typer.Option(False, "--bash", help="Requires bash"),
    modifies_tests: bool = typer.Option(False, "--modifies-tests", help="Modifies tests"),
    profile: Optional[str] = typer.Option(None, "--profile", help="Permission profile"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Check whether a tool call is permitted."""
    _load_core_config(reload=True)
    manager = PermissionManager()
    decision = manager.validate(
        tool=tool,
        operation=operation,
        path=path,
        requires_network=requires_network,
        requires_bash=requires_bash,
        modifies_tests=modifies_tests,
        profile_name=profile,
    )
    payload = {
        "tool": tool,
        "operation": operation,
        "path": path,
        "allowed": decision.allowed,
        "reason": decision.reason,
        "violations": decision.violations,
    }
    if json_output:
        typer.echo(json.dumps(payload, indent=2))
        return
    if decision.allowed:
        typer.echo("Allowed")
    else:
        typer.echo(f"Denied: {decision.reason or 'permission_violation'}")


@tool_app.command("simulate")
def tool_simulate(
    tool: str = typer.Argument(..., help="Tool name"),
    result_value: str = typer.Option("ok", "--result", help="Result to return"),
    operation: Optional[str] = typer.Option(None, "--operation", help="Tool operation"),
    path: Optional[str] = typer.Option(None, "--path", help="Target path"),
    requires_network: bool = typer.Option(False, "--network", help="Requires network"),
    requires_bash: bool = typer.Option(False, "--bash", help="Requires bash"),
    modifies_tests: bool = typer.Option(False, "--modifies-tests", help="Modifies tests"),
    profile: Optional[str] = typer.Option(None, "--profile", help="Permission profile"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Simulate a tool call through ToolProxy."""
    _load_core_config(reload=True)
    proxy = ToolProxy(agent_id="cli", profile_name=profile)

    def _noop(result: str) -> str:
        return result

    outcome = proxy.execute(
        tool,
        _noop,
        parameters={"result": result_value},
        operation=operation,
        file_path=path,
        requires_network=requires_network,
        requires_bash=requires_bash,
        modifies_tests=modifies_tests,
        profile_name=profile,
    )
    payload = {
        "success": outcome.success,
        "result": outcome.result,
        "error": outcome.error,
    }
    if json_output:
        typer.echo(json.dumps(payload, indent=2))
        return
    if outcome.success:
        typer.echo(f"Result: {outcome.result}")
    else:
        typer.echo(f"Error: {outcome.error}")


@tool_app.command("read")
def tool_read(
    path: str = typer.Argument(..., help="File path"),
    profile: Optional[str] = typer.Option(None, "--profile", help="Permission profile"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Read a file through ToolProxy."""
    _load_core_config(reload=True)
    proxy = FileToolProxy(agent_id="cli", profile_name=profile)
    outcome = proxy.read(path)
    payload = {"success": outcome.success, "content": outcome.result, "error": outcome.error}
    if json_output:
        typer.echo(json.dumps(payload, indent=2))
        return
    if outcome.success:
        typer.echo(outcome.result)
    else:
        typer.echo(f"Error: {outcome.error}")


@tool_app.command("write")
def tool_write(
    path: str = typer.Argument(..., help="File path"),
    content: Optional[str] = typer.Option(None, "--content", help="Content to write"),
    profile: Optional[str] = typer.Option(None, "--profile", help="Permission profile"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Write a file through ToolProxy."""
    _load_core_config(reload=True)
    if content is None:
        content = typer.get_text_stream("stdin").read()
    proxy = FileToolProxy(agent_id="cli", profile_name=profile)
    outcome = proxy.write(path, content)
    payload = {"success": outcome.success, "result": outcome.result, "error": outcome.error}
    if json_output:
        typer.echo(json.dumps(payload, indent=2))
        return
    if outcome.success:
        typer.echo(f"Wrote {path}")
    else:
        typer.echo(f"Error: {outcome.error}")


@tool_app.command("edit")
def tool_edit(
    path: str = typer.Argument(..., help="File path"),
    find: str = typer.Option(..., "--find", help="Text to find"),
    replace: str = typer.Option(..., "--replace", help="Replacement text"),
    count: int = typer.Option(1, "--count", help="Replacement count (0=all)"),
    profile: Optional[str] = typer.Option(None, "--profile", help="Permission profile"),
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
) -> None:
    """Edit a file through ToolProxy."""
    _load_core_config(reload=True)
    proxy = FileToolProxy(agent_id="cli", profile_name=profile)
    outcome = proxy.edit(path, find=find, replace=replace, count=count)
    payload = {"success": outcome.success, "result": outcome.result, "error": outcome.error}
    if json_output:
        typer.echo(json.dumps(payload, indent=2))
        return
    if outcome.success:
        typer.echo(f"Edited {path}")
    else:
        typer.echo(f"Error: {outcome.error}")


@quality_app.command("run")
def quality_run(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
    test_suite: str = typer.Option("quality-gates", "--test-suite", help="Test suite label"),
    task_id: Optional[str] = typer.Option(None, "--task-id", help="Related task ID"),
) -> None:
    """Run quality gates."""
    _load_core_config(reload=True)
    runner = QualityGateRunner()
    start_time = time.monotonic()
    log_test_run_started(
        test_suite=test_suite,
        task_id=task_id,
        command="subagent quality run",
    )
    report = runner.run()
    duration_ms = int((time.monotonic() - start_time) * 1000)
    results = report.get("results", [])
    total = len(results)
    passed_count = sum(1 for r in results if r.get("passed", False))
    failed_required = [
        r for r in results if not r.get("passed", False) and r.get("required", True)
    ]
    failed_optional = [
        r for r in results if not r.get("passed", False) and not r.get("required", True)
    ]
    if failed_required:
        status = "failed"
    elif failed_optional:
        status = "warning"
    else:
        status = "passed"
    summary_parts = [f"{passed_count}/{total} gates passed"]
    if failed_required:
        summary_parts.append(
            "required failed: " + ", ".join(r.get("name", "unknown") for r in failed_required)
        )
    if failed_optional:
        summary_parts.append(
            "optional failed: " + ", ".join(r.get("name", "unknown") for r in failed_optional)
        )
    summary = "; ".join(summary_parts)
    log_test_run_completed(
        test_suite=test_suite,
        status=status,
        task_id=task_id,
        duration_ms=duration_ms,
        summary=summary,
    )
    if json_output:
        typer.echo(json.dumps(report, indent=2))
        if not report.get("passed", False):
            raise typer.Exit(code=1)
        return
    for result in report.get("results", []):
        name = result.get("name")
        required = result.get("required", True)
        passed = result.get("passed", False)
        status = "PASS" if passed else ("WARN" if not required else "FAIL")
        message = result.get("message") or ""
        duration_ms = result.get("duration_ms")
        duration_label = f" ({duration_ms}ms)" if duration_ms is not None else ""
        line = f"[{status}] {name}{duration_label}"
        if message:
            line = f"{line}: {message}"
        typer.echo(line)
    if report.get("passed", False):
        typer.echo("Quality gates passed.")
        return
    typer.echo("Quality gates failed.")
    raise typer.Exit(code=1)


@dashboard_app.command("start")
def dashboard_start(
    host: str = typer.Option("localhost", "--host", help="Dashboard host"),
    port: int = typer.Option(8080, "--port", help="Dashboard port"),
    background: bool = typer.Option(True, "--background/--foreground", help="Run in background"),
) -> None:
    """Start the dashboard HTTP server."""
    if background:
        cmd = [
            sys.executable,
            "-m",
            "src.observability.dashboard_server",
            "--host",
            host,
            "--port",
            str(port),
        ]
        _start_background(cmd, "dashboard")
        return

    from src.observability.dashboard_server import start_dashboard_server, stop_dashboard_server

    start_dashboard_server(host=host, port=port)
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        stop_dashboard_server()


@dashboard_app.command("stop")
def dashboard_stop() -> None:
    """Stop the dashboard HTTP server."""
    _stop_background("dashboard")


@monitor_app.command("start")
def monitor_start(
    host: str = typer.Option("localhost", "--host", help="WebSocket host"),
    port: int = typer.Option(8765, "--port", help="WebSocket port"),
    max_connections: int = typer.Option(100, "--max-connections", help="Max connections"),
    buffer_size: int = typer.Option(100, "--buffer-size", help="Event buffer size"),
    metrics_interval: float = typer.Option(1.0, "--metrics-interval", help="Metrics interval seconds"),
    window_size: int = typer.Option(300, "--window-size", help="Default metrics window"),
    auto_subscribe: bool = typer.Option(True, "--auto-subscribe/--no-auto-subscribe", help="Subscribe to event bus"),
    background: bool = typer.Option(True, "--background/--foreground", help="Run in background"),
) -> None:
    """Start the realtime WebSocket monitor."""
    cmd = [
        sys.executable,
        "-m",
        "src.observability.realtime_monitor",
        "--host",
        host,
        "--port",
        str(port),
        "--max-connections",
        str(max_connections),
        "--buffer-size",
        str(buffer_size),
        "--metrics-interval",
        str(metrics_interval),
        "--window-size",
        str(window_size),
    ]
    if not auto_subscribe:
        cmd.append("--no-auto-subscribe")

    if background:
        _start_background(cmd, "monitor")
        return

    subprocess.call(cmd)


@monitor_app.command("stop")
def monitor_stop() -> None:
    """Stop the realtime WebSocket monitor."""
    _stop_background("monitor")


@app.command("emit-task-start")
def emit_task_start(
    task_id: str = typer.Argument(..., help="Task ID"),
    task_name: str = typer.Argument(..., help="Task name"),
    stage: str = typer.Argument(..., help="Task stage (plan/implement/test)"),
    summary: Optional[str] = typer.Option(None, "--summary", help="Task summary"),
    eta_minutes: Optional[float] = typer.Option(None, "--eta-min", help="ETA in minutes"),
    owner: Optional[str] = typer.Option(None, "--owner", help="Owner/agent"),
    session_id: Optional[str] = typer.Option(None, "--session-id", help="Session ID"),
) -> None:
    """Emit a task.started event."""
    sid = _resolve_session_id(session_id)
    event_id = log_task_started(
        task_id=task_id,
        task_name=task_name,
        stage=stage,
        summary=summary,
        eta_minutes=eta_minutes,
        owner=owner,
        session_id=sid,
    )
    typer.echo(f"Emitted task.started: {event_id}")


@app.command("emit-task-stage")
def emit_task_stage(
    task_id: str = typer.Argument(..., help="Task ID"),
    stage: str = typer.Argument(..., help="New task stage"),
    task_name: Optional[str] = typer.Option(None, "--task-name", help="Task name"),
    previous_stage: Optional[str] = typer.Option(None, "--previous-stage", help="Previous stage"),
    summary: Optional[str] = typer.Option(None, "--summary", help="Stage summary"),
    progress_pct: Optional[float] = typer.Option(None, "--progress", help="Progress percent"),
    session_id: Optional[str] = typer.Option(None, "--session-id", help="Session ID"),
) -> None:
    """Emit a task.stage_changed event."""
    sid = _resolve_session_id(session_id)
    event_id = log_task_stage_changed(
        task_id=task_id,
        stage=stage,
        task_name=task_name,
        previous_stage=previous_stage,
        summary=summary,
        progress_pct=progress_pct,
        session_id=sid,
    )
    typer.echo(f"Emitted task.stage_changed: {event_id}")


@app.command("emit-task-complete")
def emit_task_complete(
    task_id: str = typer.Argument(..., help="Task ID"),
    status: str = typer.Argument(..., help="Completion status (success/failed/warning)"),
    task_name: Optional[str] = typer.Option(None, "--task-name", help="Task name"),
    summary: Optional[str] = typer.Option(None, "--summary", help="Completion summary"),
    duration_ms: Optional[int] = typer.Option(None, "--duration-ms", help="Duration in ms"),
    session_id: Optional[str] = typer.Option(None, "--session-id", help="Session ID"),
) -> None:
    """Emit a task.completed event."""
    sid = _resolve_session_id(session_id)
    event_id = log_task_completed(
        task_id=task_id,
        status=status,
        task_name=task_name,
        summary=summary,
        duration_ms=duration_ms,
        session_id=sid,
    )
    typer.echo(f"Emitted task.completed: {event_id}")


@app.command("emit-test-start")
def emit_test_start(
    test_suite: str = typer.Argument(..., help="Test suite name"),
    task_id: Optional[str] = typer.Option(None, "--task-id", help="Related task ID"),
    command: Optional[str] = typer.Option(None, "--command", help="Command executed"),
    session_id: Optional[str] = typer.Option(None, "--session-id", help="Session ID"),
) -> None:
    """Emit a test.run_started event."""
    sid = _resolve_session_id(session_id)
    event_id = log_test_run_started(
        test_suite=test_suite,
        task_id=task_id,
        command=command,
        session_id=sid,
    )
    typer.echo(f"Emitted test.run_started: {event_id}")


@app.command("emit-test-complete")
def emit_test_complete(
    test_suite: str = typer.Argument(..., help="Test suite name"),
    status: str = typer.Argument(..., help="Result status (passed/failed/warning)"),
    task_id: Optional[str] = typer.Option(None, "--task-id", help="Related task ID"),
    duration_ms: Optional[int] = typer.Option(None, "--duration-ms", help="Duration in ms"),
    passed: Optional[int] = typer.Option(None, "--passed", help="Tests passed"),
    failed: Optional[int] = typer.Option(None, "--failed", help="Tests failed"),
    summary: Optional[str] = typer.Option(None, "--summary", help="Summary"),
    session_id: Optional[str] = typer.Option(None, "--session-id", help="Session ID"),
) -> None:
    """Emit a test.run_completed event."""
    sid = _resolve_session_id(session_id)
    event_id = log_test_run_completed(
        test_suite=test_suite,
        status=status,
        task_id=task_id,
        duration_ms=duration_ms,
        passed=passed,
        failed=failed,
        summary=summary,
        session_id=sid,
    )
    typer.echo(f"Emitted test.run_completed: {event_id}")


def _tail_file_lines(path: Path, lines: int = 20) -> Iterable[str]:
    """Return last N lines from a text or gzip file."""
    if not path.exists():
        return []
    buffer: deque[str] = deque(maxlen=lines)
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for line in f:
                buffer.append(line.rstrip("\n"))
    else:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                buffer.append(line.rstrip("\n"))
    return list(buffer)


@app.command("logs")
def logs(
    session_id: Optional[str] = typer.Option(None, "--session", "-s", help="Session ID to show"),
    follow: bool = typer.Option(False, "--follow", "-f", help="Follow the latest log"),
    lines: int = typer.Option(20, "--lines", "--count", "-n", help="Number of lines to show"),
    task_id: Optional[str] = typer.Option(None, "--task-id", "--task", help="Filter log lines by task id"),
    event_type: Optional[str] = typer.Option(None, "--event-type", "-e", help="Filter by event_type"),
    since: Optional[str] = typer.Option(None, "--since", help="Filter events at/after ISO timestamp"),
) -> None:
    """View or follow activity logs."""
    _load_core_config(reload=True)
    log_files = list_log_files()
    target = None

    if session_id:
        target = next((l for l in log_files if l["session_id"] == session_id), None)
    else:
        target = log_files[0] if log_files else None

    if not target:
        typer.echo("No log files found.")
        raise typer.Exit(code=1)

    log_path: Path = target["file_path"]

    def print_lines(lines_iter: Iterable[str]) -> None:
        for line in _filter_lines(list(lines_iter), task_id, event_type, since):
            typer.echo(line)

    print_lines(_tail_file_lines(log_path, lines=lines))

    if follow:
        try:
            with (gzip.open(log_path, "rt", encoding="utf-8") if log_path.suffix == ".gz" else open(log_path, "r", encoding="utf-8")) as f:
                f.seek(0, os.SEEK_END)
                while True:
                    chunk = f.readline()
                    if chunk:
                        print_lines([chunk.rstrip("\n")])
                    else:
                        time.sleep(0.5)
        except KeyboardInterrupt:
            return


@app.command("config-show")
def config_show(json_output: bool = typer.Option(False, "--json", help="Output JSON")) -> None:
    """Show effective CLI + core config."""
    cli_cfg = _load_config()
    core_cfg = _load_core_config(reload=True)
    payload = {
        "cli": cli_cfg,
        "core": {
            "project_root": str(core_cfg.project_root),
            "data_dir": str(core_cfg.claude_dir),
            "logs_dir": str(core_cfg.logs_dir),
            "state_dir": str(core_cfg.state_dir),
            "analytics_dir": str(core_cfg.analytics_dir),
            "credentials_dir": str(core_cfg.credentials_dir),
            "backup_enabled": getattr(core_cfg, "backup_enabled", False),
            "analytics_enabled": getattr(core_cfg, "analytics_enabled", False),
        },
    }
    if json_output:
        typer.echo(json.dumps(payload, indent=2))
    else:
        typer.echo(f"Project root: {payload['core']['project_root']}")
        typer.echo(f"Data dir:     {payload['core']['data_dir']}")
        typer.echo(f"Logs dir:     {payload['core']['logs_dir']}")
        typer.echo(f"State dir:    {payload['core']['state_dir']}")
        typer.echo(f"Analytics:    {payload['core']['analytics_dir']}")
        typer.echo(f"Creds:        {payload['core']['credentials_dir']}")
        typer.echo(f"Backup:       {payload['core']['backup_enabled']}")
        typer.echo(f"Analytics DB: {payload['core']['analytics_enabled']}")
        typer.echo(f"CLI defaults: priority={cli_cfg['task_defaults']['priority']}, watch_interval={cli_cfg['status']['watch_interval']}")


def _parse_iso(ts: str) -> Optional[datetime]:
    try:
        if ts.endswith("Z"):
            ts = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(ts)
    except Exception:
        return None


def _filter_lines(
    lines: list[str],
    task_id: Optional[str],
    event_type: Optional[str],
    since: Optional[str],
) -> list[str]:
    if not any([task_id, event_type, since]):
        return lines

    since_dt = _parse_iso(since) if since else None

    filtered = []
    for line in lines:
        try:
            event = json.loads(line)
        except Exception:
            continue
        if task_id and not (event.get("task") == task_id or event.get("task_id") == task_id):
            continue
        if event_type and event.get("event_type") != event_type:
            continue
        if since_dt:
            ts = event.get("timestamp")
            ts_dt = _parse_iso(ts) if ts else None
            if ts_dt and ts_dt < since_dt:
                continue
        filtered.append(line)
    return filtered


def main() -> None:
    app()


if __name__ == "__main__":
    main()
