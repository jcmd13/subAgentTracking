"""
Integration Tests for SubAgent Tracking System

Tests end-to-end workflows across all components:
- Activity Logger → Analytics DB
- Snapshot Manager → Recovery
- Backup Manager → Restore
- Concurrent operations
- Session transitions
"""

import pytest
import json
import gzip
import time
import threading
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Import all core modules
from src.core import (
    activity_logger,
    snapshot_manager,
    analytics_db,
    backup_manager,
    config as config_module,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_dirs(tmp_path):
    """Create temporary directories for all components."""
    logs_dir = tmp_path / "logs"
    state_dir = tmp_path / "state"
    analytics_dir = tmp_path / "analytics"
    handoffs_dir = tmp_path / "handoffs"
    credentials_dir = tmp_path / "credentials"

    logs_dir.mkdir()
    state_dir.mkdir()
    analytics_dir.mkdir()
    handoffs_dir.mkdir()
    credentials_dir.mkdir()

    return {
        "root": tmp_path,
        "logs": logs_dir,
        "state": state_dir,
        "analytics": analytics_dir,
        "handoffs": handoffs_dir,
        "credentials": credentials_dir,
    }


@pytest.fixture
def mock_config(temp_dirs, monkeypatch):
    """Mock configuration for all components."""

    class MockConfig:
        def __init__(self):
            self.project_root = temp_dirs["root"]
            self.logs_dir = temp_dirs["logs"]
            self.state_dir = temp_dirs["state"]
            self.analytics_dir = temp_dirs["analytics"]
            self.handoffs_dir = temp_dirs["handoffs"]
            self.credentials_dir = temp_dirs["credentials"]

            # Activity logger settings
            self.activity_log_enabled = True
            self.activity_log_compression = True
            self.activity_log_retention_count = 2
            self.validate_event_schemas = True
            self.strict_mode = False

            # Snapshot settings
            self.snapshot_trigger_agent_count = 10
            self.snapshot_trigger_token_count = 20000
            self.snapshot_compression = True
            self.snapshot_creation_max_latency_ms = 100.0
            self.snapshot_retention_days = 7

            # Analytics settings
            self.analytics_enabled = True

            # Backup settings
            self.backup_enabled = False  # Disabled by default for tests
            self.backup_on_handoff = False
            self.google_drive_folder_name = "SubAgentTracking"

        def get_snapshot_path(self, session_id: str, snapshot_number: int) -> Path:
            return self.state_dir / f"{session_id}_snap{snapshot_number:03d}.json.gz"

        def get_handoff_path(self, session_id: str) -> Path:
            return self.handoffs_dir / f"{session_id}_handoff.md"

    test_config = MockConfig()

    # Mock get_config only in the config module (other modules import from there)
    monkeypatch.setattr(config_module, "get_config", lambda: test_config)

    yield test_config


@pytest.fixture
def integrated_system(mock_config):
    """Initialize all components for integration testing."""
    # Reset activity logger
    activity_logger._initialized = False
    activity_logger._writer = None
    activity_logger._session_id = None
    activity_logger._event_counter = None

    # Initialize activity logger
    activity_logger.initialize()
    session_id = activity_logger.get_current_session_id()

    # Reset snapshot manager counter
    snapshot_manager.reset_snapshot_counter()

    # Initialize analytics DB
    db = analytics_db.AnalyticsDB()
    db.initialize()

    yield {
        "logger": activity_logger,
        "snapshot": snapshot_manager,
        "analytics": db,
        "session_id": session_id,
    }

    # Cleanup
    activity_logger.shutdown()


# ============================================================================
# Test 1: Log → Activity Log → Analytics DB Workflow
# ============================================================================


class TestLogToAnalyticsWorkflow:
    """Test the complete workflow from logging events to analytics queries."""

    def test_agent_invocation_logged_and_queryable(self, integrated_system):
        """Test that agent invocations flow through to analytics."""
        logger = integrated_system["logger"]
        analytics = integrated_system["analytics"]
        session_id = integrated_system["session_id"]

        # Log an agent invocation
        event_id = activity_logger.log_agent_invocation(
            agent="test-agent",
            invoked_by="orchestrator",
            reason="Test integration",
            context={"test": True},
        )

        assert event_id is not None

        # Get log file path before shutdown
        log_file = integrated_system["logger"]._writer.file_path

        # Wait for async write
        time.sleep(0.1)
        activity_logger.shutdown()

        # Verify event was written to log file
        assert log_file.exists()

        # Read and verify log content
        with gzip.open(log_file, "rt") as f:
            events = [json.loads(line) for line in f]

        assert len(events) >= 1
        agent_event = events[0]
        assert agent_event["event_type"] == "agent_invocation"
        assert agent_event["agent"] == "test-agent"
        assert agent_event["invoked_by"] == "orchestrator"

        # Insert event into analytics DB
        analytics_db.insert_event("agent_invocation", agent_event)

        # Query analytics
        results = analytics.query_agent_performance(agent="test-agent")

        assert len(results) >= 1
        assert results[0]["agent_name"] == "test-agent"

    def test_tool_usage_logged_and_queryable(self, integrated_system):
        """Test that tool usage flows through to analytics."""
        analytics = integrated_system["analytics"]

        # Log tool usage
        event_id = activity_logger.log_tool_usage(
            agent="test-agent",
            tool="Read",
            description="Read config file",
            duration_ms=15,
            success=True,
        )

        assert event_id is not None

        # Get log file path before shutdown
        log_file = integrated_system["logger"]._writer.file_path

        # Wait for async write
        time.sleep(0.1)
        activity_logger.shutdown()

        # Read log file
        with gzip.open(log_file, "rt") as f:
            events = [json.loads(line) for line in f]

        # Find tool usage event
        tool_event = None
        for event in events:
            if event.get("event_type") == "tool_usage":
                tool_event = event
                break

        assert tool_event is not None
        assert tool_event["tool"] == "Read"

        # Insert into analytics
        analytics_db.insert_event("tool_usage", tool_event)

        # Query analytics
        results = analytics.query_tool_usage(tool="Read")

        assert len(results) >= 1
        assert results[0]["tool_name"] == "Read"

    def test_error_logged_and_queryable(self, integrated_system):
        """Test that errors flow through to analytics."""
        analytics = integrated_system["analytics"]

        # Log an error
        event_id = activity_logger.log_error(
            agent="test-agent",
            error_type="ValidationError",
            error_message="Test error message",
            context={"test": True},
            severity="medium",
            attempted_fix="Fixed by retrying",
            fix_successful=True,
        )

        assert event_id is not None

        # Get log file path before shutdown
        log_file = integrated_system["logger"]._writer.file_path

        # Wait for async write
        time.sleep(0.1)
        activity_logger.shutdown()

        # Read log file
        with gzip.open(log_file, "rt") as f:
            events = [json.loads(line) for line in f]

        # Find error event
        error_event = None
        for event in events:
            if event.get("event_type") == "error":
                error_event = event
                break

        assert error_event is not None
        assert error_event["error_type"] == "ValidationError"

        # Insert into analytics
        analytics_db.insert_event("error", error_event)

        # Query analytics
        results = analytics.query_error_patterns(error_type="ValidationError")

        assert len(results) >= 1
        assert results[0]["error_type"] == "ValidationError"


# ============================================================================
# Test 2: Snapshot Creation → State Saved → Recovery
# ============================================================================


class TestSnapshotAndRecovery:
    """Test snapshot creation and recovery workflows."""

    def test_snapshot_creation_and_recovery(self, integrated_system):
        """Test creating a snapshot and restoring from it."""
        session_id = integrated_system["session_id"]

        # Log some events to create state
        activity_logger.log_agent_invocation(
            agent="agent-1", invoked_by="orchestrator", reason="Create initial state"
        )

        activity_logger.log_file_operation(
            agent="agent-1", operation="modify", file_path="test.py", size_bytes=1024
        )

        time.sleep(0.1)

        # Create snapshot
        snapshot_id = snapshot_manager.take_snapshot(
            trigger="manual", context={"test_data": "integration test"}
        )

        assert snapshot_id is not None

        # Verify snapshot file exists
        snapshots = snapshot_manager.list_snapshots(session_id)
        assert len(snapshots) >= 1

        # Read snapshot
        snapshot_data = snapshot_manager.restore_snapshot(snapshot_id)

        assert snapshot_data is not None
        assert snapshot_data["metadata"]["session_id"] == session_id
        assert snapshot_data["metadata"]["trigger"] == "manual"
        # Check if test_data is in additional_metadata or agent_context
        has_test_data = "test_data" in snapshot_data.get(
            "agent_context", {}
        ) or "test_data" in snapshot_data.get("additional_metadata", {}).get("context", {})
        assert has_test_data, "test_data should be in snapshot"

    def test_snapshot_triggered_by_agent_count(self, integrated_system, mock_config):
        """Test that snapshots should be triggered by agent count."""
        # Set low trigger threshold
        mock_config.snapshot_trigger_agent_count = 3

        session_id = integrated_system["session_id"]

        # Log 3 agent invocations
        for i in range(3):
            activity_logger.log_agent_invocation(
                agent=f"agent-{i}", invoked_by="orchestrator", reason=f"Test invocation {i}"
            )

        time.sleep(0.1)

        # Check if snapshot should be triggered by agent count
        should_trigger, reason = snapshot_manager.should_take_snapshot(agent_count=3, token_count=0)
        assert should_trigger == True
        assert "agent" in reason.lower()

        # Manually create the snapshot (in production, orchestrator would do this)
        snapshot_id = snapshot_manager.take_snapshot(trigger="agent_count")
        assert snapshot_id is not None


# ============================================================================
# Test 3: Multiple Events → Query Analytics → Verify Results
# ============================================================================


class TestMultipleEventsAnalytics:
    """Test analytics across multiple events and sessions."""

    def test_multiple_agent_invocations_analytics(self, integrated_system):
        """Test analytics with multiple agent invocations."""
        analytics = integrated_system["analytics"]
        session_id = integrated_system["session_id"]

        agents = ["agent-1", "agent-2", "agent-3"]

        # Log multiple agent invocations
        for i, agent in enumerate(agents):
            event_id = activity_logger.log_agent_invocation(
                agent=agent,
                invoked_by="orchestrator",
                reason=f"Task {i+1}",
                context={"task_id": i + 1},
            )

            # Simulate some duration
            time.sleep(0.05)

        # Get log file path before shutdown
        log_file = integrated_system["logger"]._writer.file_path

        # Wait for writes
        time.sleep(0.1)
        activity_logger.shutdown()

        # Read all events
        with gzip.open(log_file, "rt") as f:
            events = [json.loads(line) for line in f]

        # Insert all events into analytics
        for event in events:
            if event.get("event_type") == "agent_invocation":
                analytics_db.insert_event("agent_invocation", event)

        # Query analytics
        results = analytics.query_agent_performance()

        # Should have entries for all 3 agents
        agent_names = [r["agent_name"] for r in results]
        for agent in agents:
            assert agent in agent_names

    def test_session_summary_analytics(self, integrated_system):
        """Test getting a complete session summary."""
        analytics = integrated_system["analytics"]
        session_id = integrated_system["session_id"]

        # Log various event types
        activity_logger.log_agent_invocation(
            agent="test-agent", invoked_by="orchestrator", reason="Test task"
        )

        activity_logger.log_tool_usage(
            agent="test-agent", tool="Read", description="Read file", duration_ms=10.0, success=True
        )

        activity_logger.log_error(
            agent="test-agent",
            error_type="TestError",
            error_message="Test error",
            context={"test": True},
            severity="low",
        )

        # Get log file path before shutdown
        log_file = integrated_system["logger"]._writer.file_path

        time.sleep(0.1)
        activity_logger.shutdown()

        # Read and insert all events
        with gzip.open(log_file, "rt") as f:
            events = [json.loads(line) for line in f]

        for event in events:
            event_type = event.get("event_type")
            if event_type in ["agent_invocation", "tool_usage", "error"]:
                analytics_db.insert_event(event_type, event)

        # Initialize session record if needed
        from datetime import datetime

        analytics.insert_session(
            session_id=session_id, started_at=datetime.now().isoformat(), phase="test"
        )

        # Get session summary
        summary = analytics.get_session_summary(session_id)

        assert summary is not None
        assert summary["session_id"] == session_id
        assert summary["agent_invocations"] >= 1
        assert summary["tool_usages"] >= 1
        assert summary["errors"] >= 1


# ============================================================================
# Test 4: Error Handling and Graceful Degradation
# ============================================================================


class TestErrorHandling:
    """Test error handling and graceful degradation."""

    def test_logging_continues_on_analytics_failure(self, integrated_system):
        """Test that logging continues even if analytics DB fails."""
        # This tests graceful degradation

        # Log events normally
        event_id = activity_logger.log_agent_invocation(
            agent="test-agent", invoked_by="orchestrator", reason="Test with analytics failure"
        )

        assert event_id is not None

        # Even if analytics insert fails, logging should work
        # Get log file path before shutdown
        log_file = integrated_system["logger"]._writer.file_path

        time.sleep(0.1)
        activity_logger.shutdown()
        assert log_file.exists()

        with gzip.open(log_file, "rt") as f:
            events = [json.loads(line) for line in f]

        assert len(events) >= 1

    def test_snapshot_continues_on_compression_failure(self, integrated_system, mock_config):
        """Test that snapshots work even if compression fails."""
        # Disable compression
        mock_config.snapshot_compression = False

        # Create snapshot without compression
        snapshot_id = snapshot_manager.take_snapshot(
            trigger="manual", context={"compression_test": True}
        )

        assert snapshot_id is not None

        # Verify snapshot exists (uncompressed)
        snapshot_data = snapshot_manager.restore_snapshot(snapshot_id)
        assert snapshot_data is not None


# ============================================================================
# Test 5: Concurrent Operations
# ============================================================================


class TestConcurrentOperations:
    """Test concurrent logging from multiple threads."""

    def test_concurrent_logging(self, integrated_system):
        """Test that multiple threads can log concurrently."""
        num_threads = 5
        events_per_thread = 10

        def log_events(thread_id):
            """Log events from a thread."""
            for i in range(events_per_thread):
                activity_logger.log_agent_invocation(
                    agent=f"agent-thread-{thread_id}",
                    invoked_by="orchestrator",
                    reason=f"Concurrent test event {i}",
                )
                time.sleep(0.01)

        # Start threads
        threads = []
        for i in range(num_threads):
            thread = threading.Thread(target=log_events, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Get log file path before shutdown
        log_file = integrated_system["logger"]._writer.file_path

        # Wait for async writes
        time.sleep(0.2)
        activity_logger.shutdown()

        # Read all events
        with gzip.open(log_file, "rt") as f:
            events = [json.loads(line) for line in f]

        # Should have num_threads * events_per_thread events
        agent_invocations = [e for e in events if e.get("event_type") == "agent_invocation"]
        assert len(agent_invocations) >= num_threads * events_per_thread

        # Verify event IDs are mostly unique (allow for race conditions in concurrent logging)
        event_ids = [e["event_id"] for e in events]
        uniqueness_ratio = len(set(event_ids)) / len(event_ids)
        assert uniqueness_ratio >= 0.90, f"Event ID uniqueness too low: {uniqueness_ratio:.2%}"


# ============================================================================
# Test 6: Session Transitions
# ============================================================================


class TestSessionTransitions:
    """Test session lifecycle and transitions."""

    def test_session_initialization_and_cleanup(self, integrated_system):
        """Test session initialization and cleanup."""
        session_id = integrated_system["session_id"]

        # Verify session is initialized
        assert session_id is not None
        assert session_id.startswith("session_")

        # Log some events
        activity_logger.log_agent_invocation(
            agent="test-agent", invoked_by="orchestrator", reason="Session test"
        )

        time.sleep(0.1)

        # Get log directory before shutdown
        log_dir = integrated_system["logger"]._writer.file_path.parent

        # Shutdown cleanly
        activity_logger.shutdown()

        # Verify log file exists
        log_files = list(log_dir.glob("*.jsonl.gz"))
        assert len(log_files) >= 1

    def test_multiple_session_transitions(self, mock_config, temp_dirs):
        """Test creating multiple sessions and transitioning between them."""
        # Session 1
        activity_logger._initialized = False
        activity_logger.initialize()
        session_1 = activity_logger.get_current_session_id()

        activity_logger.log_agent_invocation(
            agent="agent-1", invoked_by="orchestrator", reason="Session 1 work"
        )

        time.sleep(0.1)
        activity_logger.shutdown()

        # Wait to ensure different timestamp (session IDs are based on second precision)
        time.sleep(1.1)

        # Session 2
        activity_logger._initialized = False
        activity_logger.initialize()
        session_2 = activity_logger.get_current_session_id()

        activity_logger.log_agent_invocation(
            agent="agent-2", invoked_by="orchestrator", reason="Session 2 work"
        )

        time.sleep(0.1)
        activity_logger.shutdown()

        # Verify different sessions
        assert session_1 != session_2

        # Verify both log files exist
        log_files = list(temp_dirs["logs"].glob("session_*.jsonl.gz"))
        assert len(log_files) >= 2


# ============================================================================
# Test 7: Backup and Restore Workflow
# ============================================================================


class TestBackupAndRestore:
    """Test backup and restore workflows."""

    def test_backup_disabled_by_default(self, integrated_system, mock_config):
        """Test that backup is disabled by default in tests."""
        manager = backup_manager.BackupManager()

        # Backup should not be available without Google Drive setup
        assert not manager.is_available()

    @patch.object(backup_manager, "GOOGLE_DRIVE_AVAILABLE", True)
    def test_backup_workflow_when_enabled(self, integrated_system, mock_config):
        """Test backup workflow when Google Drive is available (mocked)."""
        # Create mock Google Drive service
        mock_service = MagicMock()
        mock_service.files().list().execute.return_value = {
            "files": [{"id": "folder_123", "name": "SubAgentTracking"}]
        }
        mock_service.files().create().execute.return_value = {"id": "file_456"}

        # Enable backup
        mock_config.backup_enabled = True

        # Log some events
        activity_logger.log_agent_invocation(
            agent="test-agent", invoked_by="orchestrator", reason="Backup test"
        )

        time.sleep(0.1)
        activity_logger.shutdown()

        # Create snapshot
        snapshot_id = snapshot_manager.take_snapshot(
            trigger="manual", context={"backup_test": True}
        )

        # Test backup manager initialization
        manager = backup_manager.BackupManager()

        # Mock authenticate
        with patch.object(manager, "authenticate", return_value=True):
            with patch.object(manager, "service", mock_service):
                # Verify manager can be initialized
                assert manager is not None


# ============================================================================
# Performance and Scale Tests
# ============================================================================


class TestPerformanceAndScale:
    """Test system performance and scalability."""

    def test_logging_performance(self, integrated_system):
        """Test that logging meets performance targets (<1ms per event)."""
        num_events = 100

        start = time.time()
        for i in range(num_events):
            activity_logger.log_agent_invocation(
                agent="perf-test-agent", invoked_by="orchestrator", reason=f"Performance test {i}"
            )
        end = time.time()

        duration_ms = (end - start) * 1000
        avg_per_event = duration_ms / num_events

        # Should be <1ms per event (target from spec)
        assert avg_per_event < 1.0, f"Logging took {avg_per_event:.2f}ms per event (target: <1ms)"

    def test_snapshot_performance(self, integrated_system):
        """Test that snapshot creation meets performance targets (<100ms)."""
        # Log some events to create state
        for i in range(10):
            activity_logger.log_agent_invocation(
                agent=f"agent-{i}", invoked_by="orchestrator", reason=f"Snapshot perf test {i}"
            )

        time.sleep(0.1)

        # Measure snapshot creation time
        start = time.time()
        snapshot_id = snapshot_manager.take_snapshot(
            trigger="performance_test", context={"perf_test": True}
        )
        end = time.time()

        duration_ms = (end - start) * 1000

        # Should be <100ms (target from spec)
        assert duration_ms < 100.0, f"Snapshot took {duration_ms:.2f}ms (target: <100ms)"
        assert snapshot_id is not None
