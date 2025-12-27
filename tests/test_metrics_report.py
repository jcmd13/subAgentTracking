import json
from pathlib import Path

import pytest

from src.core.metrics_report import generate_metrics_report


def _write_log(log_path: Path, events):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("\n".join(json.dumps(event) for event in events) + "\n")


def test_metrics_report_session(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    data_dir = tmp_path / ".subagent"
    monkeypatch.setenv("SUBAGENT_DATA_DIR", str(data_dir))
    monkeypatch.setenv("SUBAGENT_CODEX_PROMPT_INSTALL", "false")

    pricing_path = data_dir / "config" / "model_pricing.yaml"
    pricing_path.parent.mkdir(parents=True, exist_ok=True)
    pricing_path.write_text(
        """
models:
  claude-sonnet-4:
    input_price_per_1m: 1.0
    output_price_per_1m: 2.0
"""
    )

    session_id = "session_20250101_000000"
    log_path = data_dir / "logs" / f"{session_id}.jsonl"
    events = [
        {
            "timestamp": "2025-01-01T00:00:00Z",
            "session_id": session_id,
            "event_type": "task.started",
            "task_id": "task_1",
            "task_name": "Test",
        },
        {
            "timestamp": "2025-01-01T00:00:01Z",
            "session_id": session_id,
            "event_type": "agent.completed",
            "agent": "agent_1",
            "duration_ms": 10,
            "tokens_used": 2000,
            "input_tokens": 1000,
            "output_tokens": 1000,
            "exit_code": 0,
            "model": "claude-sonnet-4",
            "task_id": "task_1",
        },
        {
            "timestamp": "2025-01-01T00:00:02Z",
            "session_id": session_id,
            "event_type": "test.run_completed",
            "test_suite": "unit",
            "status": "passed",
        },
        {
            "timestamp": "2025-01-01T00:00:03Z",
            "session_id": session_id,
            "event_type": "task.completed",
            "task_id": "task_1",
        },
    ]
    _write_log(log_path, events)

    quality_report = data_dir / "quality" / "report_20250101_000000.json"
    quality_report.parent.mkdir(parents=True, exist_ok=True)
    quality_report.write_text(
        json.dumps(
            {
                "passed": True,
                "results": [
                    {
                        "name": "coverage",
                        "passed": True,
                        "required": True,
                        "details": {"stdout": "TOTAL 10 0 80%"},
                    }
                ],
            }
        )
    )

    report = generate_metrics_report(scope="session", session_id=session_id, compare_naive=False)
    metrics = report["metrics"]

    assert metrics["tasks"]["started"] == 1
    assert metrics["tasks"]["completed"] == 1
    assert metrics["tests"]["passed"] == 1
    assert metrics["agents"]["completed"] == 1
    assert metrics["cost"]["source"] == "agent_events"
    assert metrics["cost"]["total"] == pytest.approx(0.003)
    assert report["quality"]["coverage_percentages"] == [80]
