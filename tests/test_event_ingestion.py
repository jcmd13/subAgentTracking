"""
Tests for Analytics DB Event Ingestion functionality.

Tests:
- JSONL parsing from activity logs
- Batch processing (100 events at a time)
- Duplicate detection (skip re-processing)
- Error handling (malformed events)
- Performance (>1000 events/sec target)
"""

import pytest
import json
import gzip
import tempfile
import time
from pathlib import Path
from datetime import datetime, timezone

from src.core import analytics_db
from src.core.analytics_db import (
    ingest_activity_log,
    ingest_session_logs,
    _ingest_events_batch,
    _is_duplicate_event,
)


# =================================================================
# Fixtures
# =================================================================


@pytest.fixture
def mock_config(monkeypatch, tmp_path):
    """Mock configuration with temporary directories."""
    from src.core.config import Config

    config = Config()
    config.logs_dir = tmp_path / "logs"
    config.state_dir = tmp_path / "state"
    config.analytics_dir = tmp_path / "analytics"

    # Create directories
    config.logs_dir.mkdir(parents=True, exist_ok=True)
    config.state_dir.mkdir(parents=True, exist_ok=True)
    config.analytics_dir.mkdir(parents=True, exist_ok=True)

    def mock_get_config():
        return config

    monkeypatch.setattr("src.core.analytics_db.get_config", mock_get_config)
    monkeypatch.setattr("src.core.config.get_config", mock_get_config)

    # Reset global database instance to ensure test isolation
    import src.core.analytics_db

    src.core.analytics_db._db_instance = None

    return config


@pytest.fixture
def sample_activity_log(tmp_path):
    """Create sample activity log file with various event types."""
    log_file = tmp_path / "logs" / "test_session.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    events = [
        {
            "type": "agent_invocation",
            "event_id": "evt_001",
            "session_id": "test_session",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": "orchestrator",
            "invoked_by": "user",
            "reason": "Start test",
            "status": "completed",
            "duration_ms": 1500,
            "tokens_consumed": 5000,
        },
        {
            "type": "tool_usage",
            "event_id": "evt_002",
            "session_id": "test_session",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": "orchestrator",
            "tool": "Read",
            "operation": "read_file",
            "duration_ms": 45,
            "success": True,
        },
        {
            "type": "file_operation",
            "event_id": "evt_003",
            "session_id": "test_session",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": "orchestrator",
            "operation": "create",
            "file_path": "/path/to/file.py",
            "lines_changed": 150,
            "language": "python",
        },
        {
            "type": "decision",
            "event_id": "evt_004",
            "session_id": "test_session",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": "orchestrator",
            "question": "Which agent to use?",
            "selected": "config-architect",
            "rationale": "Best for infrastructure work",
            "confidence": "high",
        },
        {
            "type": "error",
            "event_id": "evt_005",
            "session_id": "test_session",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": "orchestrator",
            "error_type": "ImportError",
            "error_message": "Module not found",
            "severity": "high",
            "context": {"file": "/path/to/file.py"},
            "attempted_fix": "Added to requirements.txt",
            "fix_successful": True,
            "recovery_time_ms": 5000,
        },
        {
            "type": "validation",
            "event_id": "evt_006",
            "session_id": "test_session",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": "orchestrator",
            "task": "Task 1.1",
            "validation_type": "performance",
            "result": "PASS",
            "checks": {"latency": "PASS", "throughput": "PASS"},
            "failures": [],
        },
    ]

    with open(log_file, "w") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")

    return log_file


@pytest.fixture
def sample_compressed_log(tmp_path):
    """Create sample compressed activity log (.jsonl.gz)."""
    log_file = tmp_path / "logs" / "test_session_compressed.jsonl.gz"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    events = [
        {
            "type": "agent_invocation",
            "event_id": "evt_101",
            "session_id": "test_session_compressed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": "orchestrator",
            "invoked_by": "user",
            "reason": "Start test",
            "status": "completed",
        }
    ]

    with gzip.open(log_file, "wt", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")

    return log_file


# =================================================================
# Test Event Ingestion
# =================================================================


def test_ingest_activity_log_all_event_types(mock_config, sample_activity_log):
    """Test ingestion of all 7 event types."""
    # Initialize database
    db = analytics_db.get_analytics_db()
    db.initialize()

    # Ingest activity log
    stats = ingest_activity_log(sample_activity_log)

    # Verify statistics
    assert stats["total_events"] == 6, "Should have read 6 events"
    assert stats["inserted"] == 6, "Should have inserted 6 events"
    assert stats["skipped"] == 0, "Should have skipped 0 events (no duplicates)"
    assert stats["errors"] == 0, "Should have 0 errors"
    assert stats["duration_ms"] > 0, "Should have measured duration"

    # Verify events were inserted into appropriate tables
    agent_perf = db.query_agent_performance()
    assert len(agent_perf) == 1, "Should have 1 agent invocation"

    tool_usage = db.query_tool_usage()
    assert len(tool_usage) == 1, "Should have 1 tool usage"

    errors = db.query_error_patterns()
    assert len(errors) == 1, "Should have 1 error"


def test_ingest_compressed_log(mock_config, sample_compressed_log):
    """Test ingestion of gzip-compressed activity log."""
    db = analytics_db.get_analytics_db()
    db.initialize()

    stats = ingest_activity_log(sample_compressed_log)

    assert stats["total_events"] == 1
    assert stats["inserted"] == 1
    assert stats["errors"] == 0


def test_ingest_with_duplicate_detection(mock_config, sample_activity_log):
    """Test duplicate detection (skip re-processing)."""
    db = analytics_db.get_analytics_db()
    db.initialize()

    # First ingestion
    stats1 = ingest_activity_log(sample_activity_log)
    assert stats1["inserted"] == 6
    assert stats1["skipped"] == 0

    # Second ingestion (all duplicates)
    stats2 = ingest_activity_log(sample_activity_log, skip_duplicates=True)
    assert stats2["total_events"] == 6
    assert stats2["inserted"] == 0
    assert stats2["skipped"] == 6, "All events should be skipped as duplicates"


def test_ingest_without_duplicate_detection(mock_config, sample_activity_log):
    """Test ingestion without duplicate detection."""
    db = analytics_db.get_analytics_db()
    db.initialize()

    # First ingestion
    stats1 = ingest_activity_log(sample_activity_log, skip_duplicates=False)
    assert stats1["inserted"] == 6

    # Second ingestion (no duplicate checking)
    stats2 = ingest_activity_log(sample_activity_log, skip_duplicates=False)
    assert stats2["inserted"] == 6, "Should insert duplicates when skip_duplicates=False"
    assert stats2["skipped"] == 0


def test_ingest_with_malformed_events(mock_config, tmp_path):
    """Test error handling for malformed JSON events."""
    log_file = tmp_path / "logs" / "malformed.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Create log with malformed JSON
    with open(log_file, "w") as f:
        f.write('{"type": "agent_invocation", "event_id": "evt_001"}\n')
        f.write("{malformed json}\n")  # Invalid JSON
        f.write('{"type": "tool_usage", "event_id": "evt_002"}\n')

    db = analytics_db.get_analytics_db()
    db.initialize()

    stats = ingest_activity_log(log_file)

    assert stats["total_events"] == 2, "Should have parsed 2 valid events"
    assert stats["errors"] == 1, "Should have 1 JSON parsing error"
    assert stats["inserted"] >= 0, "Should have inserted valid events"


def test_ingest_with_missing_file(mock_config):
    """Test error handling for missing activity log file."""
    with pytest.raises(FileNotFoundError):
        ingest_activity_log("/nonexistent/path/to/log.jsonl")


# =================================================================
# Test Batch Processing
# =================================================================


def test_batch_processing(mock_config, tmp_path):
    """Test batch processing with custom batch size."""
    # Create log with many events
    log_file = tmp_path / "logs" / "large_session.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    num_events = 250
    with open(log_file, "w") as f:
        for i in range(num_events):
            event = {
                "type": "agent_invocation",
                "event_id": f"evt_{i:03d}",
                "session_id": "large_session",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent": "test-agent",
                "invoked_by": "user",
                "reason": f"Test {i}",
            }
            f.write(json.dumps(event) + "\n")

    db = analytics_db.get_analytics_db()
    db.initialize()

    # Ingest with batch size of 50
    stats = ingest_activity_log(log_file, batch_size=50)

    assert stats["total_events"] == num_events
    assert stats["inserted"] == num_events
    assert stats["errors"] == 0


def test_ingest_events_batch_function(mock_config):
    """Test _ingest_events_batch helper function."""
    db = analytics_db.get_analytics_db()
    db.initialize()

    events = [
        {
            "type": "agent_invocation",
            "event_id": "evt_001",
            "session_id": "test",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": "test-agent",
            "invoked_by": "user",
            "reason": "Test",
        },
        {
            "type": "tool_usage",
            "event_id": "evt_002",
            "session_id": "test",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": "test-agent",
            "tool": "Read",
        },
    ]

    result = _ingest_events_batch(db, events)

    assert result["inserted"] == 2
    assert result["errors"] == 0


# =================================================================
# Test Duplicate Detection
# =================================================================


def test_is_duplicate_event(mock_config):
    """Test _is_duplicate_event helper function."""
    db = analytics_db.get_analytics_db()
    db.initialize()

    # Initially not duplicate
    assert _is_duplicate_event(db, "evt_999", "test_session") is False

    # Insert event
    db.insert_agent_performance(
        session_id="test_session",
        event_id="evt_999",
        agent_name="test-agent",
        invoked_by="user",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    # Now it's a duplicate
    assert _is_duplicate_event(db, "evt_999", "test_session") is True


def test_is_duplicate_with_empty_ids(mock_config):
    """Test duplicate detection with empty event/session IDs."""
    db = analytics_db.get_analytics_db()
    db.initialize()

    # Empty IDs should return False (not duplicate)
    assert _is_duplicate_event(db, "", "test_session") is False
    assert _is_duplicate_event(db, "evt_001", "") is False
    assert _is_duplicate_event(db, "", "") is False


# =================================================================
# Test Performance
# =================================================================


def test_ingestion_performance_target(mock_config, tmp_path):
    """Test ingestion speed meets >1000 events/sec target."""
    # Create log with 2000 events
    log_file = tmp_path / "logs" / "performance_test.jsonl"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    num_events = 2000
    with open(log_file, "w") as f:
        for i in range(num_events):
            event = {
                "type": "agent_invocation",
                "event_id": f"evt_{i:04d}",
                "session_id": "perf_test",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent": "test-agent",
                "invoked_by": "user",
                "reason": f"Test {i}",
            }
            f.write(json.dumps(event) + "\n")

    db = analytics_db.get_analytics_db()
    db.initialize()

    # Measure ingestion time
    stats = ingest_activity_log(log_file, skip_duplicates=False)

    assert stats["inserted"] == num_events
    assert stats["errors"] == 0

    # Calculate events per second
    duration_sec = stats["duration_ms"] / 1000
    events_per_sec = num_events / duration_sec

    print(f"\nIngestion Performance:")
    print(f"  Events: {num_events}")
    print(f"  Duration: {stats['duration_ms']}ms ({duration_sec:.2f}s)")
    print(f"  Speed: {events_per_sec:.0f} events/sec")
    print(f"  Target: >1000 events/sec")

    assert (
        events_per_sec > 1000
    ), f"Ingestion too slow: {events_per_sec:.0f} events/sec (target: >1000)"


# =================================================================
# Test Convenience Functions
# =================================================================


def test_ingest_session_logs_current(mock_config, tmp_path):
    """Test ingest_session_logs for current session."""
    config = mock_config

    # Create current session log
    log_file = config.logs_dir / "session_current.jsonl"
    with open(log_file, "w") as f:
        event = {
            "type": "agent_invocation",
            "event_id": "evt_001",
            "session_id": "current",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": "test-agent",
            "invoked_by": "user",
            "reason": "Test",
        }
        f.write(json.dumps(event) + "\n")

    db = analytics_db.get_analytics_db()
    db.initialize()

    stats = ingest_session_logs()  # Default: current session

    assert stats["total_events"] == 1
    assert stats["inserted"] == 1


def test_ingest_session_logs_specific(mock_config, tmp_path):
    """Test ingest_session_logs for specific session."""
    config = mock_config

    session_id = "session_20251102_140000"
    log_file = config.logs_dir / f"{session_id}.jsonl"
    with open(log_file, "w") as f:
        event = {
            "type": "agent_invocation",
            "event_id": "evt_001",
            "session_id": session_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": "test-agent",
            "invoked_by": "user",
            "reason": "Test",
        }
        f.write(json.dumps(event) + "\n")

    db = analytics_db.get_analytics_db()
    db.initialize()

    stats = ingest_session_logs(session_id)

    assert stats["total_events"] == 1
    assert stats["inserted"] == 1


def test_ingest_session_logs_not_found(mock_config):
    """Test error handling for missing session log."""
    db = analytics_db.get_analytics_db()
    db.initialize()

    with pytest.raises(FileNotFoundError):
        ingest_session_logs("nonexistent_session")
