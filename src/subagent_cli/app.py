import gzip
import json
import os
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
from src.core.config import Config

app = typer.Typer(help="SubAgent Control CLI (Phase 1 skeleton)")

SUBAGENT_ROOT = Path(".subagent")
TASKS_FILE = SUBAGENT_ROOT / "tasks" / "tasks.json"
CONFIG_PATH = SUBAGENT_ROOT / "config.yaml"

# Ensure core config uses .subagent for data directories
os.environ.setdefault("SUBAGENT_DATA_DIR", str(SUBAGENT_ROOT))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_subagent_dirs() -> None:
    """Create the .subagent directory structure expected by the CLI."""
    subdirs = [
        SUBAGENT_ROOT,
        SUBAGENT_ROOT / "logs",
        SUBAGENT_ROOT / "state",
        SUBAGENT_ROOT / "sessions",
        SUBAGENT_ROOT / "tasks",
        SUBAGENT_ROOT / "handoffs",
        SUBAGENT_ROOT / "quality",
        SUBAGENT_ROOT / "analytics",
        SUBAGENT_ROOT / "credentials",
    ]
    for d in subdirs:
        d.mkdir(parents=True, exist_ok=True)
        gitkeep = d / ".gitkeep"
        if not gitkeep.exists():
            gitkeep.touch()


def _load_tasks() -> list[dict]:
    if TASKS_FILE.exists():
        try:
            return json.loads(TASKS_FILE.read_text())
        except Exception:
            return []
    return []


def _save_tasks(tasks: list[dict]) -> None:
    TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = TASKS_FILE.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(tasks, indent=2))
    tmp_path.replace(TASKS_FILE)


def _next_task_id(tasks: list[dict]) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"task_{ts}_{len(tasks)+1:03d}"


def _load_config() -> Dict[str, Any]:
    """Load CLI config from YAML if present (with defaults)."""
    defaults: Dict[str, Any] = {
        "task_defaults": {"priority": 3},
        "status": {"watch_interval": 2.0},
    }
    if CONFIG_PATH.exists():
        try:
            data = yaml.safe_load(CONFIG_PATH.read_text()) or {}
            defaults.update(_validate_cli_config(data, defaults))
        except Exception:
            typer.echo("Warning: Failed to parse .subagent/config.yaml, using defaults.")
    return defaults


def _load_core_config(reload: bool = False) -> Config:
    """
    Load core config (respects SUBAGENT_DATA_DIR and SUBAGENT_TRACKING_ROOT).

    Args:
        reload: Force reload of config module state
    """
    return core_config.get_config(reload=reload)


def _validate_cli_config(config_data: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and normalize CLI config values."""
    validated = defaults.copy()

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
    if not CONFIG_PATH.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            yaml.safe_dump(
                {
                    "task_defaults": {"priority": 3},
                    "status": {"watch_interval": 2.0},
                }
            )
        )


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def init() -> None:
    """
    Initialize local SubAgent directories (.subagent/).
    """
    _ensure_subagent_dirs()
    _save_default_config()
    typer.echo(f"Initialized {SUBAGENT_ROOT} directory structure.")


@app.command()
def status(
    json_output: bool = typer.Option(False, "--json", help="Output JSON"),
    watch: bool = typer.Option(False, "--watch", "-w", help="Continuously refresh status"),
    interval: float = typer.Option(2.0, "--interval", "-i", help="Seconds between updates when watching"),
) -> None:
    """
    Show current system status.
    """
    cfg = core_config.get_config()
    def render() -> None:
        cfg_local = core_config.get_config(reload=True)
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
            while True:
                typer.clear()
                render()
                time.sleep(interval)
        except KeyboardInterrupt:
            return
    else:
        render()


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
    if task.get("created_at"):
        typer.echo(f"  created:   {task.get('created_at')}")
    if task.get("status"):
        typer.echo(f"  status:    {task.get('status')}")


@app.command("task-add")
def task_add(
    description: str = typer.Argument(..., help="Task description"),
    priority: int = typer.Option(None, "--priority", "-p", help="Priority 1-5"),
    task_type: Optional[str] = typer.Option(None, "--type", "-t", help="Task type/category"),
    deadline: Optional[str] = typer.Option(None, "--deadline", "-d", help="Deadline (ISO date/time or freeform)"),
    criteria: List[str] = typer.Option([], "--acceptance", "-a", help="Acceptance criteria (repeatable)"),
    status: str = typer.Option("pending", "--status", "-s", help="Task status"),
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
        }
    )
    _save_tasks(tasks)
    typer.echo(f"Created task {task_id}: {description}")


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
    lines: int = typer.Option(20, "--lines", "-n", help="Number of lines to show"),
) -> None:
    """View or follow activity logs."""
    logs = list_log_files()
    target = None

    if session_id:
        target = next((l for l in logs if l["session_id"] == session_id), None)
    else:
        target = logs[0] if logs else None

    if not target:
        typer.echo("No log files found.")
        raise typer.Exit(code=1)

    log_path: Path = target["file_path"]

    def print_last_lines():
        for line in _tail_file_lines(log_path, lines=lines):
            typer.echo(line)

    print_last_lines()

    if follow:
        try:
            with (gzip.open(log_path, "rt", encoding="utf-8") if log_path.suffix == ".gz" else open(log_path, "r", encoding="utf-8")) as f:
                f.seek(0, os.SEEK_END)
                while True:
                    chunk = f.readline()
                    if chunk:
                        typer.echo(chunk.rstrip("\n"))
                    else:
                        time.sleep(0.5)
        except KeyboardInterrupt:
            return


@app.command("task-list")
def task_list(json_output: bool = typer.Option(False, "--json", help="Output JSON")) -> None:
    """
    List tasks from .subagent/tasks/tasks.json.
    """
    _ensure_subagent_dirs()
    tasks = _load_tasks()
    if json_output:
        typer.echo(json.dumps(tasks, indent=2))
        return
    if not tasks:
        typer.echo("No tasks found.")
        return
    for task in tasks:
        summary = f"{task['id']}: {task['description']} [{task.get('status','pending')}] (p{task.get('priority',3)})"
        if task.get("deadline"):
            summary += f" due {task['deadline']}"
        if task.get("type"):
            summary += f" type={task['type']}"
        typer.echo(summary)


@app.command("task-update")
def task_update(
    task_id: str = typer.Argument(..., help="Task ID to update"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="New description"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="New status"),
    priority: Optional[int] = typer.Option(None, "--priority", "-p", help="New priority"),
    task_type: Optional[str] = typer.Option(None, "--type", "-t", help="New type/category"),
    deadline: Optional[str] = typer.Option(None, "--deadline", help="New deadline"),
    criteria: List[str] = typer.Option([], "--acceptance", "-a", help="Replace acceptance criteria (repeatable)"),
) -> None:
    """
    Update an existing task.
    """
    _ensure_subagent_dirs()
    tasks = _load_tasks()
    updated = False
    for task in tasks:
        if task["id"] != task_id:
            continue
        if description is not None:
            task["description"] = description
        if status is not None:
            task["status"] = status
        if priority is not None:
            task["priority"] = priority
        if task_type is not None:
            task["type"] = task_type
        if deadline is not None:
            task["deadline"] = deadline
        if criteria:
            task["acceptance_criteria"] = criteria
        updated = True
        break
    if not updated:
        typer.echo(f"Task {task_id} not found.")
        raise typer.Exit(code=1)
    _save_tasks(tasks)
    typer.echo(f"Updated task {task_id}.")


@app.command("task-complete")
def task_complete(task_id: str = typer.Argument(..., help="Task ID to mark complete")) -> None:
    """
    Mark a task as completed.
    """
    _ensure_subagent_dirs()
    tasks = _load_tasks()
    completed = False
    for task in tasks:
        if task["id"] != task_id:
            continue
        task["status"] = "done"
        task["completed_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        completed = True
        break
    if not completed:
        typer.echo(f"Task {task_id} not found.")
        raise typer.Exit(code=1)
    _save_tasks(tasks)
    typer.echo(f"Marked task {task_id} as done.")


@app.command("task-show")
def task_show(task_id: str) -> None:
    """
    Show a single task by ID.
    """
    tasks = _load_tasks()
    match = next((t for t in tasks if t["id"] == task_id), None)
    if not match:
        typer.echo(f"Task {task_id} not found.")
        raise typer.Exit(code=1)
    typer.echo(json.dumps(match, indent=2))


@app.command()
def logs(
    follow: bool = typer.Option(False, "--follow", "-f", help="Tail the latest log"),
    count: int = typer.Option(20, "--count", "-n", help="Lines to show when not following"),
    task_id: Optional[str] = typer.Option(None, "--task-id", help="Filter log lines by task id"),
    event_type: Optional[str] = typer.Option(None, "--event-type", "-e", help="Filter by event_type"),
    since: Optional[str] = typer.Option(None, "--since", help="Filter events at/after ISO timestamp"),
) -> None:
    """
    Show or tail the latest activity log.
    """
    cfg = core_config.get_config()
    logs_dir = cfg.logs_dir
    log_files = sorted(logs_dir.glob("*.jsonl*"), reverse=True)
    if not log_files:
        typer.echo("No logs found.")
        return
    latest = log_files[0]
    typer.echo(f"Reading {latest}")
    if follow:
        _tail_file(latest)
    else:
        lines = _read_last_lines(latest, count)
        for line in _filter_lines(lines, task_id, event_type, since):
            typer.echo(line.rstrip("\n"))


def _read_last_lines(path: Path, count: int) -> list[str]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt") as f:
            lines = f.readlines()
    else:
        lines = path.read_text().splitlines()
    return lines[-count:]


def _tail_file(path: Path) -> None:
    typer.echo("Press Ctrl+C to stop.")
    open_fn = gzip.open if path.suffix == ".gz" else open
    with open_fn(path, "rt") as f:
        f.seek(0, 2)
        try:
            while True:
                line = f.readline()
                if line:
                    for filtered in _filter_lines([line], None, None, None):
                        typer.echo(filtered.rstrip("\n"))
                else:
                    time.sleep(1)
        except KeyboardInterrupt:
            return


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
