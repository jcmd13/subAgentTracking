import json
from datetime import datetime, timedelta, timezone

from typer.testing import CliRunner

from src.subagent_cli.app import app


runner = CliRunner()


def _extract_task_id(output: str) -> str:
    for line in output.splitlines():
        if line.startswith("Created task "):
            return line.split("Created task ", 1)[1].split(":")[0].strip()
    return ""


def test_cli_task_commands(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(tmp_path / ".subagent"))
    monkeypatch.setenv("SUBAGENT_CODEX_PROMPT_INSTALL", "false")

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0

    result = runner.invoke(
        app,
        [
            "task",
            "add",
            "Test task",
            "--priority",
            "2",
            "--type",
            "research",
            "--deadline",
            "2025-01-01",
            "--acceptance",
            "Must pass",
            "--context",
            "UI research",
        ],
    )
    assert result.exit_code == 0
    task_id = _extract_task_id(result.stdout)
    assert task_id

    result = runner.invoke(app, ["task", "list", "--open"])
    assert result.exit_code == 0
    assert task_id in result.stdout

    result = runner.invoke(app, ["task", "show", task_id, "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["description"] == "Test task"
    assert data["priority"] == 2
    assert data["type"] == "research"
    assert data["context"] == ["UI research"]

    result = runner.invoke(
        app,
        [
            "task",
            "update",
            task_id,
            "--status",
            "in_progress",
            "--priority",
            "1",
            "--description",
            "Updated task",
            "--acceptance",
            "New criteria",
            "--context",
            "More context",
        ],
    )
    assert result.exit_code == 0

    updated = json.loads(runner.invoke(app, ["task", "show", task_id, "--json"]).stdout)
    assert updated["status"] == "in_progress"
    assert updated["priority"] == 1
    assert updated["description"] == "Updated task"
    assert updated["acceptance_criteria"] == ["New criteria"]
    assert updated["context"] == ["More context"]

    result = runner.invoke(app, ["task", "complete", task_id])
    assert result.exit_code == 0
    completed = json.loads(runner.invoke(app, ["task", "show", task_id, "--json"]).stdout)
    assert completed["status"] == "done"
    assert completed.get("completed_at")


def test_cli_logs_filters(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / ".subagent"
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(data_dir))
    monkeypatch.setenv("SUBAGENT_CODEX_PROMPT_INSTALL", "false")

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0

    logs_dir = data_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    session_id = "session_20250101_120000"
    log_path = logs_dir / f"{session_id}.jsonl"

    base_time = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)
    events = [
        {
            "timestamp": base_time.isoformat().replace("+00:00", "Z"),
            "event_type": "task.started",
            "task_id": "task_alpha",
        },
        {
            "timestamp": (base_time + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"),
            "event_type": "task.completed",
            "task_id": "task_beta",
        },
        {
            "timestamp": (base_time + timedelta(minutes=10)).isoformat().replace("+00:00", "Z"),
            "event_type": "task.completed",
            "task_id": "task_alpha",
        },
    ]
    log_path.write_text("\n".join(json.dumps(e) for e in events) + "\n")

    result = runner.invoke(
        app,
        ["logs", "--session", session_id, "--lines", "10", "--task-id", "task_alpha"],
    )
    assert result.exit_code == 0
    assert "task_alpha" in result.stdout
    assert "task_beta" not in result.stdout

    result = runner.invoke(
        app,
        ["logs", "--session", session_id, "--lines", "10", "--event-type", "task.completed"],
    )
    assert result.exit_code == 0
    assert "task.completed" in result.stdout
    assert "task.started" not in result.stdout

    since_ts = events[1]["timestamp"]
    result = runner.invoke(
        app,
        ["logs", "--session", session_id, "--lines", "10", "--since", since_ts],
    )
    assert result.exit_code == 0
    assert "task_beta" in result.stdout
    assert "task_alpha" in result.stdout
