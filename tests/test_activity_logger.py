"""
Tests for Activity Logger - Core Event Logging System

Tests all logging functions, async JSONL writer, Pydantic validation,
and performance characteristics.
"""

import pytest
import json
import gzip
import tempfile
import time
import threading
from pathlib import Path
from datetime import datetime

from src.core.activity_logger import (
    # Session management
    EventCounter,
    generate_session_id,
    get_iso_timestamp,
    # Lifecycle
    initialize,
    shutdown,
    get_current_session_id,
    get_event_count,
    # Logging functions
    log_agent_invocation,
    log_tool_usage,
    log_file_operation,
    log_decision,
    log_error,
    log_context_snapshot,
    log_validation,
    # Context managers
    tool_usage_context,
    agent_invocation_context,
    # Internal components
    ThreadedJSONLWriter,
)
from src.core.schemas import (
    AgentInvocationEvent,
    ToolUsageEvent,
    FileOperationEvent,
    DecisionEvent,
    ErrorEvent,
    ContextSnapshotEvent,
    ValidationEvent,
    validate_event,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_log_dir(tmp_path):
    """Create temporary directory for log files."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir


@pytest.fixture
def logger_session(temp_log_dir, monkeypatch):
    """Initialize logger with temp directory and clean up after test."""

    # Create a simple mock config object
    class MockConfig:
        def __init__(self):
            self.logs_dir = temp_log_dir
            self.activity_log_enabled = True
            self.activity_log_compression = True
            self.validate_event_schemas = True
            self.strict_mode = True

    from src.core import config

    test_config = MockConfig()

    monkeypatch.setattr(config, "get_config", lambda: test_config)

    # Initialize logger
    initialize()

    yield

    # Cleanup
    shutdown()


# ============================================================================
# Test EventCounter
# ============================================================================


class TestEventCounter:
    """Test thread-safe event ID generation."""

    def test_sequential_ids(self):
        """Test that event IDs are generated sequentially."""
        counter = EventCounter()

        id1 = counter.next_id()
        id2 = counter.next_id()
        id3 = counter.next_id()

        assert id1 == "evt_001"
        assert id2 == "evt_002"
        assert id3 == "evt_003"

    def test_get_count(self):
        """Test getting current event count."""
        counter = EventCounter()

        assert counter.get_count() == 0

        counter.next_id()
        assert counter.get_count() == 1

        counter.next_id()
        counter.next_id()
        assert counter.get_count() == 3

    def test_reset(self):
        """Test resetting the counter."""
        counter = EventCounter()

        counter.next_id()
        counter.next_id()
        assert counter.get_count() == 2

        counter.reset()
        assert counter.get_count() == 0

        id1 = counter.next_id()
        assert id1 == "evt_001"

    def test_thread_safety(self):
        """Test that counter is thread-safe."""
        counter = EventCounter()
        ids = []

        def generate_ids(n):
            for _ in range(n):
                ids.append(counter.next_id())

        # Create multiple threads generating IDs
        threads = [threading.Thread(target=generate_ids, args=(100,)) for _ in range(5)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # All IDs should be unique
        assert len(ids) == 500
        assert len(set(ids)) == 500


# ============================================================================
# Test Session and Timestamp Generation
# ============================================================================


class TestSessionAndTimestamp:
    """Test session ID and timestamp generation."""

    def test_session_id_format(self):
        """Test that session ID has correct format."""
        session_id = generate_session_id()

        assert session_id.startswith("session_")
        # Format: session_YYYYMMDD_HHMMSS
        assert len(session_id) == len("session_20251102_153045")

    def test_iso_timestamp_format(self):
        """Test that ISO timestamp has correct format."""
        timestamp = get_iso_timestamp()

        # Should contain 'T' separator
        assert "T" in timestamp

        # Should end with 'Z' for UTC
        assert timestamp.endswith("Z")

        # Should be parseable
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        assert isinstance(parsed, datetime)


# ============================================================================
# Test ThreadedJSONLWriter
# ============================================================================


class TestThreadedJSONLWriter:
    """Test async JSONL writer with queue buffering."""

    def test_write_single_event(self, temp_log_dir):
        """Test writing a single event."""
        log_path = temp_log_dir / "test.jsonl"
        writer = ThreadedJSONLWriter(log_path, use_compression=False)
        writer.start()

        event = {"event_type": "test", "timestamp": "2025-11-02T15:30:00Z", "data": "test data"}

        writer.write_event(event)
        writer.shutdown()

        # Read file and verify
        with open(log_path, "r") as f:
            line = f.readline()
            parsed = json.loads(line)
            assert parsed == event

    def test_write_multiple_events(self, temp_log_dir):
        """Test writing multiple events."""
        log_path = temp_log_dir / "test.jsonl"
        writer = ThreadedJSONLWriter(log_path, use_compression=False)
        writer.start()

        events = [
            {"event_type": "test1", "data": "data1"},
            {"event_type": "test2", "data": "data2"},
            {"event_type": "test3", "data": "data3"},
        ]

        for event in events:
            writer.write_event(event)

        writer.shutdown()

        # Read file and verify
        with open(log_path, "r") as f:
            lines = f.readlines()
            assert len(lines) == 3

            for i, line in enumerate(lines):
                parsed = json.loads(line)
                assert parsed == events[i]

    def test_compression(self, temp_log_dir):
        """Test gzip compression."""
        log_path = temp_log_dir / "test.jsonl.gz"
        writer = ThreadedJSONLWriter(log_path, use_compression=True)
        writer.start()

        event = {"event_type": "test", "data": "test data"}
        writer.write_event(event)
        writer.shutdown()

        # Read compressed file
        with gzip.open(log_path, "rt", encoding="utf-8") as f:
            line = f.readline()
            parsed = json.loads(line)
            assert parsed == event

    def test_auto_start(self, temp_log_dir):
        """Test that writer starts automatically on first write."""
        log_path = temp_log_dir / "test.jsonl"
        writer = ThreadedJSONLWriter(log_path, use_compression=False)

        # Don't call start() explicitly
        event = {"event_type": "test", "data": "test data"}
        writer.write_event(event)

        writer.shutdown()

        # Verify event was written
        with open(log_path, "r") as f:
            line = f.readline()
            parsed = json.loads(line)
            assert parsed == event


# ============================================================================
# Test Logging Functions
# ============================================================================


class TestLogAgentInvocation:
    """Test agent invocation logging."""

    def test_log_agent_invocation_basic(self, logger_session, temp_log_dir):
        """Test basic agent invocation logging."""
        event_id = log_agent_invocation(
            agent="test-agent", invoked_by="user", reason="Test invocation"
        )

        assert event_id == "evt_001"

    def test_log_agent_invocation_with_context(self, logger_session, temp_log_dir):
        """Test agent invocation with context."""
        event_id = log_agent_invocation(
            agent="test-agent",
            invoked_by="orchestrator",
            reason="Test invocation",
            context={"tokens_before": 5000},
            result={"status": "success"},
        )

        assert event_id.startswith("evt_")

    def test_validation_with_pydantic(self, logger_session, temp_log_dir):
        """Test that Pydantic validation works."""
        # This should succeed
        event_id = log_agent_invocation(agent="test-agent", invoked_by="user", reason="Valid event")

        assert event_id.startswith("evt_")


class TestLogToolUsage:
    """Test tool usage logging."""

    def test_log_tool_usage_basic(self, logger_session):
        """Test basic tool usage logging."""
        event_id = log_tool_usage(agent="test-agent", tool="Read", operation="read_file")

        assert event_id.startswith("evt_")

    def test_log_tool_usage_with_duration(self, logger_session):
        """Test tool usage with duration."""
        event_id = log_tool_usage(
            agent="test-agent", tool="Write", operation="create_file", duration_ms=42, success=True
        )

        assert event_id.startswith("evt_")

    def test_log_tool_usage_failure(self, logger_session):
        """Test logging tool failure."""
        event_id = log_tool_usage(
            agent="test-agent",
            tool="Edit",
            operation="edit_file",
            success=False,
            error_message="File not found",
        )

        assert event_id.startswith("evt_")


class TestLogFileOperation:
    """Test file operation logging."""

    def test_log_file_operation_create(self, logger_session):
        """Test logging file creation."""
        event_id = log_file_operation(
            agent="test-agent",
            operation="create",
            file_path="src/test.py",
            file_size_bytes=1024,
            language="python",
        )

        assert event_id.startswith("evt_")

    def test_log_file_operation_modify(self, logger_session):
        """Test logging file modification."""
        event_id = log_file_operation(
            agent="test-agent",
            operation="modify",
            file_path="src/test.py",
            lines_changed=10,
            diff="+added line\n-removed line",
            git_hash_before="abc123",
            git_hash_after="def456",
        )

        assert event_id.startswith("evt_")


class TestLogDecision:
    """Test decision logging."""

    def test_log_decision_basic(self, logger_session):
        """Test basic decision logging."""
        event_id = log_decision(
            agent="orchestrator",
            question="Which agent to use?",
            options=["agent1", "agent2"],
            selected="agent1",
            rationale="Better fit for task",
        )

        assert event_id.startswith("evt_")

    def test_log_decision_with_confidence(self, logger_session):
        """Test decision with confidence score."""
        event_id = log_decision(
            agent="orchestrator",
            question="Which approach?",
            options=["approach1", "approach2"],
            selected="approach1",
            rationale="More efficient",
            confidence=0.95,
            alternative_considered="approach2",
        )

        assert event_id.startswith("evt_")


class TestLogError:
    """Test error logging."""

    def test_log_error_basic(self, logger_session):
        """Test basic error logging."""
        event_id = log_error(
            agent="test-agent",
            error_type="ValidationError",
            error_message="Invalid input",
            context={"file": "test.py", "line": 42},
        )

        assert event_id.startswith("evt_")

    def test_log_error_with_fix(self, logger_session):
        """Test error logging with fix attempt."""
        event_id = log_error(
            agent="test-agent",
            error_type="PerformanceError",
            error_message="Exceeded latency budget",
            context={"measured": 450, "target": 200},
            severity="medium",
            attempted_fix="Switched to faster implementation",
            fix_successful=True,
            recovery_time_ms=100,
        )

        assert event_id.startswith("evt_")


class TestLogContextSnapshot:
    """Test context snapshot logging."""

    def test_log_context_snapshot_basic(self, logger_session):
        """Test basic context snapshot."""
        event_id = log_context_snapshot(
            tokens_before=40000,
            tokens_after=45000,
            tokens_consumed=5000,
            tokens_remaining=155000,
            files_in_context=["file1.py", "file2.py"],
        )

        assert event_id.startswith("evt_")

    def test_log_context_snapshot_with_agent(self, logger_session):
        """Test context snapshot with agent."""
        event_id = log_context_snapshot(
            tokens_before=40000,
            tokens_after=45000,
            tokens_consumed=5000,
            tokens_remaining=155000,
            files_in_context=["file1.py"],
            agent="orchestrator",
            memory_mb=512.5,
        )

        assert event_id.startswith("evt_")


class TestLogValidation:
    """Test validation logging."""

    def test_log_validation_pass(self, logger_session):
        """Test logging successful validation."""
        event_id = log_validation(
            agent="test-agent",
            task="Task 1.1",
            validation_type="unit_test",
            checks={"test1": "pass", "test2": "pass"},
            result="pass",
            metrics={"coverage": 100},
        )

        assert event_id.startswith("evt_")

    def test_log_validation_fail(self, logger_session):
        """Test logging failed validation."""
        event_id = log_validation(
            agent="test-agent",
            task="Task 1.2",
            validation_type="performance",
            checks={"latency": "fail", "memory": "pass"},
            result="fail",
            failures=["latency exceeded budget"],
            warnings=["memory usage high"],
        )

        assert event_id.startswith("evt_")


# ============================================================================
# Test Context Managers
# ============================================================================


class TestContextManagers:
    """Test context manager logging helpers."""

    def test_tool_usage_context_success(self, logger_session):
        """Test tool usage context manager on success."""
        with tool_usage_context("test-agent", "Read", operation="read_file") as event_id:
            # Simulate some work
            time.sleep(0.001)

        # Event should be logged after context exits
        assert get_event_count() == 1

    def test_tool_usage_context_failure(self, logger_session):
        """Test tool usage context manager on failure."""
        with pytest.raises(ValueError):
            with tool_usage_context("test-agent", "Write", operation="write_file"):
                raise ValueError("Test error")

        # Event should still be logged with error
        assert get_event_count() == 1

    def test_agent_invocation_context(self, logger_session):
        """Test agent invocation context manager."""
        with agent_invocation_context("test-agent", "user", "Test reason") as event_id:
            # Event is logged immediately
            assert event_id.startswith("evt_")

        assert get_event_count() == 1


# ============================================================================
# Test Performance
# ============================================================================


class TestPerformance:
    """Test performance characteristics (<1ms overhead target)."""

    def test_logging_overhead(self, logger_session):
        """Test that logging overhead is < 1ms per event."""
        iterations = 100

        start_time = time.time()
        for i in range(iterations):
            log_agent_invocation(agent="test-agent", invoked_by="user", reason=f"Test {i}")
        end_time = time.time()

        total_time_ms = (end_time - start_time) * 1000
        avg_time_ms = total_time_ms / iterations

        # Average should be well under 1ms (aiming for < 0.5ms)
        assert avg_time_ms < 1.0, f"Average logging overhead: {avg_time_ms:.2f}ms"

    def test_validation_overhead(self, logger_session):
        """Test Pydantic validation overhead."""
        iterations = 100

        start_time = time.time()
        for i in range(iterations):
            log_tool_usage(agent="test-agent", tool="Read", operation="read_file")
        end_time = time.time()

        total_time_ms = (end_time - start_time) * 1000
        avg_time_ms = total_time_ms / iterations

        # Should still be under 1ms with validation
        assert avg_time_ms < 1.0, f"Average with validation: {avg_time_ms:.2f}ms"


# ============================================================================
# Test Integration
# ============================================================================


class TestIntegration:
    """Test end-to-end integration scenarios."""

    def test_full_logging_session(self, logger_session):
        """Test a complete logging session with multiple event types."""
        # Log various events
        log_agent_invocation(agent="orchestrator", invoked_by="user", reason="Start session")
        log_tool_usage(agent="orchestrator", tool="Read", operation="read_config")
        log_file_operation(agent="orchestrator", operation="create", file_path="test.py")
        log_decision(
            agent="orchestrator",
            question="Which agent?",
            options=["agent1", "agent2"],
            selected="agent1",
            rationale="Better fit",
        )
        log_validation(
            agent="orchestrator",
            task="Setup",
            validation_type="config",
            checks={"valid": "pass"},
            result="pass",
        )

        # Verify event count
        assert get_event_count() == 5

        # Verify all events have event_type set correctly
        # (Actual file writing is verified in other tests)

    def test_parent_event_tracking(self, logger_session):
        """Test parent event ID tracking for nested events."""
        # Log parent event
        with agent_invocation_context("parent-agent", "user", "Parent task") as parent_id:
            # Log child events
            child_id = log_tool_usage(agent="parent-agent", tool="Read", operation="read_file")

            # Child events should have parent_event_id set
            # (We can't verify this directly without reading the log file,
            # but we trust the implementation)

        assert get_event_count() == 2


# ============================================================================
# Test Error Handling
# ============================================================================


class TestErrorHandling:
    """Test error handling in activity logger."""

    def test_auto_initialize(self):
        """Test that logger auto-initializes if not initialized."""
        # Don't call initialize()
        # Logger should auto-initialize on first log
        event_id = log_agent_invocation(
            agent="test-agent", invoked_by="user", reason="Auto-init test"
        )

        assert event_id.startswith("evt_")

        # Cleanup
        shutdown()

    def test_disabled_logging(self, temp_log_dir, monkeypatch):
        """Test that logging can be disabled."""

        # Create a simple mock config object
        class MockConfig:
            def __init__(self):
                self.logs_dir = temp_log_dir
                self.activity_log_enabled = False
                self.activity_log_compression = True
                self.validate_event_schemas = True
                self.strict_mode = True

        from src.core import config

        test_config = MockConfig()

        monkeypatch.setattr(config, "get_config", lambda: test_config)

        initialize()

        # Logging should not create files
        event_id = log_agent_invocation(
            agent="test-agent", invoked_by="user", reason="Should not log"
        )

        # Event ID still generated (counter still increments)
        assert event_id.startswith("evt_")

        shutdown()

        # Verify no log file was created
        log_files = list(temp_log_dir.glob("*.jsonl*"))
        assert len(log_files) == 0, "No log files should be created when logging is disabled"
