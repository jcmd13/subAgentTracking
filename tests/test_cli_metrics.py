import json
from pathlib import Path

from typer.testing import CliRunner

from src.subagent_cli.app import app


runner = CliRunner()


def _write_log(log_path: Path, events):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("\n".join(json.dumps(event) for event in events) + "\n")


def test_cli_metrics_json_and_export(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(tmp_path / ".subagent"))
    monkeypatch.setenv("SUBAGENT_CODEX_PROMPT_INSTALL", "false")

    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0

    pricing_path = tmp_path / ".subagent" / "config" / "model_pricing.yaml"
    pricing_path.parent.mkdir(parents=True, exist_ok=True)
    pricing_path.write_text(
        """
models:
  claude-sonnet-4:
    input_price_per_1m: 1.0
    output_price_per_1m: 1.0
"""
    )

    session_id = "session_20250101_000000"
    log_path = tmp_path / ".subagent" / "logs" / f"{session_id}.jsonl"
    events = [
        {
            "timestamp": "2025-01-01T00:00:00Z",
            "session_id": session_id,
            "event_type": "agent.completed",
            "agent": "agent_1",
            "duration_ms": 10,
            "tokens_used": 1000,
            "input_tokens": 500,
            "output_tokens": 500,
            "exit_code": 0,
            "model": "claude-sonnet-4",
        }
    ]
    _write_log(log_path, events)

    result = runner.invoke(app, ["metrics", "--scope", "session", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["metrics"]["agents"]["completed"] == 1

    export_path = tmp_path / "report.md"
    result = runner.invoke(app, ["metrics", "--export", str(export_path)])
    assert result.exit_code == 0
    assert export_path.exists()
