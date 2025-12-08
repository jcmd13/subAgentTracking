import gzip
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer

from src.core import config as core_config
from src.core.activity_logger import list_log_files

app = typer.Typer(help="SubAgent Control CLI (Phase 1 skeleton)")

SUBAGENT_ROOT = Path(".subagent")
TASKS_FILE = SUBAGENT_ROOT / "tasks" / "tasks.json"


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
    TASKS_FILE.write_text(json.dumps(tasks, indent=2))


def _next_task_id(tasks: list[dict]) -> str:
    return f"task_{len(tasks)+1:03d}"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def init() -> None:
    """
    Initialize local SubAgent directories (.subagent/).
    """
    _ensure_subagent_dirs()
    typer.echo(f"Initialized {SUBAGENT_ROOT} directory structure.")


@app.command()
def status(json_output: bool = typer.Option(False, "--json", help="Output JSON")) -> None:
    """
    Show current system status.
    """
    cfg = core_config.get_config()
    payload = {
        "project_root": str(cfg.project_root),
        "logs_dir": str(cfg.logs_dir),
        "state_dir": str(cfg.state_dir),
        "backup_enabled": getattr(cfg, "backup_enabled", False),
        "analytics_enabled": getattr(cfg, "analytics_enabled", False),
        "session_id_format": getattr(cfg, "session_id_format", "session_%Y%m%d_%H%M%S"),
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


@app.command("task-add")
def task_add(description: str = typer.Argument(..., help="Task description"), priority: int = typer.Option(3, "--priority", "-p", help="Priority 1-5")) -> None:
    """
    Create a new task in .subagent/tasks/tasks.json.
    """
    _ensure_subagent_dirs()
    tasks = _load_tasks()
    task_id = _next_task_id(tasks)
    tasks.append(
        {
            "id": task_id,
            "description": description,
            "priority": priority,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "status": "pending",
        }
    )
    _save_tasks(tasks)
    typer.echo(f"Created task {task_id}: {description}")


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
        typer.echo(f"{task['id']}: {task['description']} [{task.get('status','pending')}] (p{task.get('priority',3)})")


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
def logs(follow: bool = typer.Option(False, "--follow", "-f", help="Tail the latest log"), count: int = typer.Option(20, "--count", "-n", help="Lines to show when not following")) -> None:
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
        for line in lines:
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
                    typer.echo(line.rstrip("\n"))
                else:
                    time.sleep(1)
        except KeyboardInterrupt:
            return


def main() -> None:
    app()


if __name__ == "__main__":
    main()
