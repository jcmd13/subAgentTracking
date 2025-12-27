"""
Tests for Analytics Database - SQLite Analytics

Tests the analytics database functionality including schema creation,
event insertion, querying, and data integrity.

Test Coverage:
- Database initialization and schema creation
- Event insertion (all event types)
- Query functions (performance, tool usage, errors)
- Session management
- Error handling and edge cases
"""

import pytest
import tempfile
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any

from src.core import analytics_db
from src.core import config as config_module


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def temp_analytics_dir():
    """Create temporary directory for analytics database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_config(temp_analytics_dir, monkeypatch):
    """Mock configuration with temp directories."""

    class MockConfig:
        def __init__(self):
            self.analytics_dir = temp_analytics_dir
            self.analytics_db_name = "test_tracking.db"
            self.analytics_enabled = True

    test_config = MockConfig()
    monkeypatch.setattr(config_module, "get_config", lambda: test_config)
    monkeypatch.setattr("src.core.analytics_db.get_config", lambda: test_config)

    # Reset global instance
    analytics_db._db_instance = None

    yield test_config


# ============================================================================
# Test Database Initialization
# ============================================================================


class TestDatabaseInitialization:
    """Tests for database initialization and schema creation."""

    def test_init_creates_database_file(self, mock_config):
        """Test that initialization creates database file."""
        db = analytics_db.AnalyticsDB()
        result = db.initialize()

        assert result is True
        assert db.db_path.exists()

    def test_init_creates_all_tables(self, mock_config):
        """Test that all required tables are created."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        expected_tables = [
            "schema_version",
            "sessions",
            "agent_performance",
            "tool_usage",
            "error_patterns",
            "file_operations",
            "decisions",
            "validations",
            "tasks",
        ]

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            for table in expected_tables:
                assert table in tables, f"Table '{table}' not created"

    def test_init_creates_indexes(self, mock_config):
        """Test that indexes are created."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = [row[0] for row in cursor.fetchall()]

            # Check for key indexes
            assert any("idx_agent_perf" in idx for idx in indexes)
            assert any("idx_tool_usage" in idx for idx in indexes)
            assert any("idx_errors" in idx for idx in indexes)

    def test_init_is_idempotent(self, mock_config):
        """Test that initialization can be called multiple times safely."""
        db = analytics_db.AnalyticsDB()

        # Initialize multiple times
        assert db.initialize() is True
        assert db.initialize() is True
        assert db.initialize() is True

        # Should still work
        assert db.db_path.exists()

    def test_init_sets_schema_version(self, mock_config):
        """Test that schema version is recorded."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT version FROM schema_version")
            version = cursor.fetchone()[0]

            assert version == analytics_db.SCHEMA_VERSION


# ============================================================================
# Test Insert Functions
# ============================================================================


class TestInsertFunctions:
    """Tests for event insertion functions."""

    def test_insert_agent_performance(self, mock_config):
        """Test inserting agent performance record."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        result = db.insert_agent_performance(
            session_id="session_20251103_120000",
            event_id="evt_001",
            agent_name="orchestrator",
            invoked_by="user",
            timestamp="2025-11-03T12:00:00Z",
            duration_ms=1500,
            tokens_consumed=5000,
            status="completed",
            task_type="Phase 1 Planning",
        )

        assert result is True

        # Verify data
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM agent_performance")
            row = cursor.fetchone()

            assert row is not None
            assert row["agent_name"] == "orchestrator"
            assert row["duration_ms"] == 1500
            assert row["status"] == "completed"

    def test_insert_tool_usage(self, mock_config):
        """Test inserting tool usage record."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        result = db.insert_tool_usage(
            session_id="session_20251103_120000",
            event_id="evt_002",
            agent_name="config-architect",
            tool_name="Write",
            timestamp="2025-11-03T12:01:00Z",
            operation="create_file",
            duration_ms=45,
            success=True,
        )

        assert result is True

        # Verify data
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tool_usage")
            row = cursor.fetchone()

            assert row is not None
            assert row["tool_name"] == "Write"
            assert row["success"] == 1  # SQLite stores boolean as int

    def test_upsert_task_state(self, mock_config):
        """Test upserting task state."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        result = db.upsert_task_state(
            task_id="task_20251220_001",
            session_id="session_20251220_120000",
            timestamp="2025-12-20T12:00:00Z",
            task_name="Add risk scoring",
            stage="plan",
            status="started",
            summary="Initial planning",
            eta_minutes=30,
            owner="orchestrator",
            progress_pct=10.0,
            started_at="2025-12-20T12:00:00Z",
        )
        assert result is True

        # Update stage
        result = db.upsert_task_state(
            task_id="task_20251220_001",
            session_id="session_20251220_120000",
            timestamp="2025-12-20T12:10:00Z",
            stage="implement",
            status="in_progress",
            progress_pct=55.0,
        )
        assert result is True

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?", ("task_20251220_001",))
            row = cursor.fetchone()

            assert row is not None
            assert row["stage"] == "implement"
            assert row["status"] == "in_progress"
            assert row["progress_pct"] == 55.0

    def test_task_query_helpers(self, mock_config):
        """Test task query helpers."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        db.upsert_task_state(
            task_id="task_alpha",
            session_id="session_20251220_120000",
            timestamp="2025-12-20T12:00:00Z",
            task_name="Alpha task",
            stage="plan",
            status="in_progress",
            progress_pct=30.0,
        )
        db.upsert_task_state(
            task_id="task_beta",
            session_id="session_20251220_120000",
            timestamp="2025-12-20T12:05:00Z",
            task_name="Beta task",
            stage="done",
            status="success",
            progress_pct=100.0,
            completed_at="2025-12-20T12:05:00Z",
        )

        task = db.get_task_state("task_alpha")
        assert task is not None
        assert task["task_name"] == "Alpha task"
        assert task["progress_pct"] == 30.0

        tasks = db.list_tasks(status="in_progress")
        assert len(tasks) == 1
        assert tasks[0]["task_id"] == "task_alpha"

    def test_task_progress_summary(self, mock_config):
        """Test task progress summary aggregation."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        db.upsert_task_state(
            task_id="task_one",
            session_id="session_20251220_120000",
            timestamp="2025-12-20T12:00:00Z",
            task_name="Task One",
            stage="plan",
            status="in_progress",
            progress_pct=20.0,
        )
        db.upsert_task_state(
            task_id="task_two",
            session_id="session_20251220_120000",
            timestamp="2025-12-20T12:10:00Z",
            task_name="Task Two",
            stage="build",
            status="in_progress",
            progress_pct=60.0,
        )
        db.upsert_task_state(
            task_id="task_done",
            session_id="session_20251220_120000",
            timestamp="2025-12-20T12:20:00Z",
            task_name="Task Done",
            stage="done",
            status="success",
            progress_pct=100.0,
            completed_at="2025-12-20T12:20:00Z",
        )

        summary = db.get_task_progress_summary()
        assert summary["total_tasks"] == 3
        assert summary["active_tasks"] == 2
        assert summary["completed_tasks"] == 1
        assert summary["avg_progress_active"] == pytest.approx(40.0)

    def test_insert_error_pattern(self, mock_config):
        """Test inserting error pattern record."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        result = db.insert_error_pattern(
            session_id="session_20251103_120000",
            event_id="evt_003",
            agent_name="refactor-agent",
            error_type="ImportError",
            error_message="Module not found",
            timestamp="2025-11-03T12:02:00Z",
            severity="high",
            file_path="src/test.py",
            fix_attempted="Added import statement",
            fix_successful=True,
            resolution_time_ms=500,
        )

        assert result is True

        # Verify data
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM error_patterns")
            row = cursor.fetchone()

            assert row is not None
            assert row["error_type"] == "ImportError"
            assert row["fix_successful"] == 1

    def test_insert_file_operation(self, mock_config):
        """Test inserting file operation record."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        result = db.insert_file_operation(
            session_id="session_20251103_120000",
            event_id="evt_004",
            agent_name="config-architect",
            operation="modify",
            file_path="src/core/config.py",
            timestamp="2025-11-03T12:03:00Z",
            lines_changed=25,
            language="python",
        )

        assert result is True

        # Verify data
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM file_operations")
            row = cursor.fetchone()

            assert row is not None
            assert row["operation"] == "modify"
            assert row["lines_changed"] == 25

    def test_insert_decision(self, mock_config):
        """Test inserting decision record."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        result = db.insert_decision(
            session_id="session_20251103_120000",
            event_id="evt_005",
            agent_name="orchestrator",
            question="Which agent for structured logging?",
            selected="config-architect",
            timestamp="2025-11-03T12:04:00Z",
            rationale="Infrastructure work matches expertise",
            confidence=0.95,
        )

        assert result is True

        # Verify data
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM decisions")
            row = cursor.fetchone()

            assert row is not None
            assert row["selected"] == "config-architect"
            assert row["confidence"] == 0.95

    def test_insert_validation(self, mock_config):
        """Test inserting validation record."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        result = db.insert_validation(
            session_id="session_20251103_120000",
            event_id="evt_006",
            agent_name="test-engineer",
            task="Task 1.1",
            validation_type="unit_test",
            result="pass",
            timestamp="2025-11-03T12:05:00Z",
            checks={"coverage": "pass", "performance": "pass"},
            failures=[],
        )

        assert result is True

        # Verify data
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM validations")
            row = cursor.fetchone()

            assert row is not None
            assert row["result"] == "pass"
            assert '"coverage"' in row["checks_json"]


# ============================================================================
# Test Session Management
# ============================================================================


class TestSessionManagement:
    """Tests for session management functions."""

    def test_insert_session(self, mock_config):
        """Test inserting session record."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        result = db.insert_session(
            session_id="session_20251103_120000",
            started_at="2025-11-03T12:00:00Z",
            phase="Phase 1",
            notes="Initial implementation",
        )

        assert result is True

        # Verify data
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions")
            row = cursor.fetchone()

            assert row is not None
            assert row["session_id"] == "session_20251103_120000"
            assert row["phase"] == "Phase 1"

    def test_update_session_end(self, mock_config):
        """Test updating session end time."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        # Insert session first
        db.insert_session(session_id="session_20251103_120000", started_at="2025-11-03T12:00:00Z")

        # Update end time
        result = db.update_session_end(
            session_id="session_20251103_120000", ended_at="2025-11-03T12:30:00Z", success=True
        )

        assert result is True

        # Verify data
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM sessions WHERE session_id = ?", ("session_20251103_120000",)
            )
            row = cursor.fetchone()

            assert row["ended_at"] == "2025-11-03T12:30:00Z"
            assert row["success"] == 1

    def test_get_session_summary(self, mock_config):
        """Test getting session summary."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        session_id = "session_20251103_120000"

        # Insert session
        db.insert_session(session_id, "2025-11-03T12:00:00Z")

        # Insert some events
        db.insert_agent_performance(
            session_id, "evt_001", "orchestrator", "user", "2025-11-03T12:00:00Z"
        )
        db.insert_tool_usage(session_id, "evt_002", "orchestrator", "Read", "2025-11-03T12:01:00Z")
        db.insert_error_pattern(
            session_id, "evt_003", "orchestrator", "TestError", "Test error", "2025-11-03T12:02:00Z"
        )

        # Get summary
        summary = db.get_session_summary(session_id)

        assert summary is not None
        assert summary["session_id"] == session_id
        assert summary["agent_invocations"] == 1
        assert summary["tool_usages"] == 1
        assert summary["errors"] == 1

    def test_get_session_summary_nonexistent(self, mock_config):
        """Test getting summary for nonexistent session."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        summary = db.get_session_summary("session_99999_999999")

        assert summary is None


# ============================================================================
# Test Query Functions
# ============================================================================


class TestQueryFunctions:
    """Tests for analytics query functions."""

    def test_query_agent_performance(self, mock_config):
        """Test querying agent performance."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        # Insert multiple records
        for i in range(3):
            db.insert_agent_performance(
                session_id="session_20251103_120000",
                event_id=f"evt_{i:03d}",
                agent_name="orchestrator" if i < 2 else "config-architect",
                invoked_by="user",
                timestamp=f"2025-11-03T12:{i:02d}:00Z",
                duration_ms=1000 + i * 100,
            )

        # Query all
        results = db.query_agent_performance()
        assert len(results) == 3

        # Query by agent
        results = db.query_agent_performance(agent="orchestrator")
        assert len(results) == 2
        assert all(r["agent_name"] == "orchestrator" for r in results)

        # Query by session
        results = db.query_agent_performance(session_id="session_20251103_120000")
        assert len(results) == 3

    def test_query_tool_usage(self, mock_config):
        """Test querying tool usage."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        # Insert multiple records
        tools = ["Read", "Write", "Read"]
        for i, tool in enumerate(tools):
            db.insert_tool_usage(
                session_id="session_20251103_120000",
                event_id=f"evt_{i:03d}",
                agent_name="config-architect",
                tool_name=tool,
                timestamp=f"2025-11-03T12:{i:02d}:00Z",
            )

        # Query by tool
        results = db.query_tool_usage(tool="Read")
        assert len(results) == 2

        # Query by agent
        results = db.query_tool_usage(agent="config-architect")
        assert len(results) == 3

    def test_query_error_patterns(self, mock_config):
        """Test querying error patterns."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        # Insert multiple records
        error_types = ["ImportError", "ValueError", "ImportError"]
        for i, error_type in enumerate(error_types):
            db.insert_error_pattern(
                session_id="session_20251103_120000",
                event_id=f"evt_{i:03d}",
                agent_name="refactor-agent",
                error_type=error_type,
                error_message=f"Error {i}",
                timestamp=f"2025-11-03T12:{i:02d}:00Z",
            )

        # Query by error type
        results = db.query_error_patterns(error_type="ImportError")
        assert len(results) == 2

        # Query by agent
        results = db.query_error_patterns(agent="refactor-agent")
        assert len(results) == 3

    def test_query_with_limit(self, mock_config):
        """Test query limit parameter."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        # Insert 10 records
        for i in range(10):
            db.insert_agent_performance(
                session_id="session_20251103_120000",
                event_id=f"evt_{i:03d}",
                agent_name="orchestrator",
                invoked_by="user",
                timestamp=f"2025-11-03T12:{i:02d}:00Z",
            )

        # Query with limit
        results = db.query_agent_performance(limit=5)
        assert len(results) == 5

    def test_query_with_date_range(self, mock_config):
        """Test query with date range."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        # Insert records with different timestamps
        timestamps = [
            "2025-11-01T12:00:00Z",
            "2025-11-02T12:00:00Z",
            "2025-11-03T12:00:00Z",
        ]

        for i, ts in enumerate(timestamps):
            db.insert_agent_performance(
                session_id="session_20251103_120000",
                event_id=f"evt_{i:03d}",
                agent_name="orchestrator",
                invoked_by="user",
                timestamp=ts,
            )

        # Query with date range
        results = db.query_agent_performance(
            start_date="2025-11-02T00:00:00Z", end_date="2025-11-03T23:59:59Z"
        )

        assert len(results) == 2


# ============================================================================
# Test Convenience Functions
# ============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_get_analytics_db_creates_instance(self, mock_config):
        """Test that get_analytics_db creates instance."""
        db = analytics_db.get_analytics_db()

        assert db is not None
        assert isinstance(db, analytics_db.AnalyticsDB)
        assert db.db_path.exists()

    def test_get_analytics_db_returns_same_instance(self, mock_config):
        """Test that get_analytics_db returns singleton."""
        db1 = analytics_db.get_analytics_db()
        db2 = analytics_db.get_analytics_db()

        assert db1 is db2

    def test_insert_event_agent_invocation(self, mock_config):
        """Test insert_event with agent invocation."""
        event_data = {
            "event_type": "agent_invocation",
            "session_id": "session_20251103_120000",
            "event_id": "evt_001",
            "agent": "orchestrator",
            "invoked_by": "user",
            "timestamp": "2025-11-03T12:00:00Z",
            "duration_ms": 1500,
            "status": "completed",
        }

        result = analytics_db.insert_event("agent_invocation", event_data)

        assert result is True

        # Verify
        db = analytics_db.get_analytics_db()
        rows = db.query_agent_performance()
        assert len(rows) == 1

    def test_insert_event_tool_usage(self, mock_config):
        """Test insert_event with tool usage."""
        event_data = {
            "session_id": "session_20251103_120000",
            "event_id": "evt_002",
            "agent": "config-architect",
            "tool": "Write",
            "timestamp": "2025-11-03T12:00:00Z",
            "success": True,
        }

        result = analytics_db.insert_event("tool_usage", event_data)

        assert result is True

        # Verify
        db = analytics_db.get_analytics_db()
        rows = db.query_tool_usage()
        assert len(rows) == 1

    def test_insert_event_unknown_type(self, mock_config):
        """Test insert_event with unknown event type."""
        result = analytics_db.insert_event("unknown_type", {})

        assert result is False


# ============================================================================
# Test Error Handling
# ============================================================================


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_connection_context_manager(self, mock_config):
        """Test database connection context manager."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            assert result[0] == 1

    def test_connection_rollback_on_error(self, mock_config):
        """Test that connection rolls back on error."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        try:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                # This will fail - invalid SQL
                cursor.execute("INVALID SQL")
        except Exception:
            pass  # Expected

        # Database should still be usable
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            assert cursor.fetchone()[0] == 1

    def test_insert_with_missing_required_fields(self, mock_config):
        """Test insert functions handle missing fields gracefully."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        # Should not crash even with empty strings
        result = db.insert_agent_performance(
            session_id="", event_id="", agent_name="", invoked_by="", timestamp=""
        )

        # May fail validation but shouldn't crash
        assert isinstance(result, bool)

    def test_initialize_handles_directory_creation_error(self, mock_config, monkeypatch):
        """Test that initialize handles directory creation errors."""
        db = analytics_db.AnalyticsDB()

        # Mock mkdir to raise an exception
        def mock_mkdir(*args, **kwargs):
            raise OSError("Permission denied")

        monkeypatch.setattr(Path, "mkdir", mock_mkdir)

        # Should return False on error
        result = db.initialize()
        assert result is False

    def test_query_functions_with_session_id_filter(self, mock_config):
        """Test query functions with session_id parameter."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        # Insert data for two sessions
        db.insert_agent_performance(
            session_id="session1",
            event_id="evt_001",
            agent_name="agent1",
            invoked_by="user",
            timestamp=datetime.utcnow().isoformat(),
            duration_ms=100,
        )

        db.insert_agent_performance(
            session_id="session2",
            event_id="evt_002",
            agent_name="agent1",
            invoked_by="user",
            timestamp=datetime.utcnow().isoformat(),
            duration_ms=200,
        )

        # Query with session_id filter
        results = db.query_agent_performance(agent="agent1", session_id="session1")
        assert len(results) == 1
        assert results[0]["session_id"] == "session1"

        # Insert tool usage for testing
        db.insert_tool_usage(
            session_id="session1",
            event_id="evt_003",
            agent_name="agent1",
            tool_name="Read",
            timestamp=datetime.utcnow().isoformat(),
        )

        db.insert_tool_usage(
            session_id="session2",
            event_id="evt_004",
            agent_name="agent1",
            tool_name="Write",
            timestamp=datetime.utcnow().isoformat(),
        )

        # Query tool usage with session_id
        tool_results = db.query_tool_usage(session_id="session1")
        assert len(tool_results) == 1
        assert tool_results[0]["session_id"] == "session1"

        # Insert error patterns for testing
        db.insert_error_pattern(
            session_id="session1",
            event_id="evt_005",
            agent_name="agent1",
            error_type="TestError",
            error_message="Test error message",
            timestamp=datetime.utcnow().isoformat(),
        )

        db.insert_error_pattern(
            session_id="session2",
            event_id="evt_006",
            agent_name="agent1",
            error_type="TestError",
            error_message="Test error message 2",
            timestamp=datetime.utcnow().isoformat(),
        )

        # Query errors with session_id
        error_results = db.query_error_patterns(session_id="session1")
        assert len(error_results) == 1
        assert error_results[0]["session_id"] == "session1"

    def test_insert_functions_error_handling(self, mock_config, monkeypatch):
        """Test that insert functions handle database errors gracefully."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        # Mock get_connection to raise an exception
        def mock_connection(*args, **kwargs):
            raise sqlite3.OperationalError("Database locked")

        monkeypatch.setattr(db, "get_connection", mock_connection)

        # All insert functions should return False on error
        assert (
            db.insert_agent_performance(
                session_id="test",
                event_id="evt_001",
                agent_name="agent",
                invoked_by="user",
                timestamp=datetime.utcnow().isoformat(),
            )
            is False
        )

        assert (
            db.insert_tool_usage(
                session_id="test",
                event_id="evt_001",
                agent_name="agent",
                tool_name="Read",
                timestamp=datetime.utcnow().isoformat(),
            )
            is False
        )

        assert (
            db.insert_error_pattern(
                session_id="test",
                event_id="evt_001",
                agent_name="agent",
                error_type="TestError",
                error_message="Test error",
                timestamp=datetime.utcnow().isoformat(),
            )
            is False
        )

        assert (
            db.insert_file_operation(
                session_id="test",
                event_id="evt_001",
                agent_name="agent",
                operation="read",
                file_path="test.py",
                timestamp=datetime.utcnow().isoformat(),
            )
            is False
        )

        assert (
            db.insert_decision(
                session_id="test",
                event_id="evt_001",
                agent_name="agent",
                question="Test?",
                selected="Option A",
                timestamp=datetime.utcnow().isoformat(),
            )
            is False
        )

        assert (
            db.insert_validation(
                session_id="test",
                event_id="evt_001",
                agent_name="agent",
                task="Task 1",
                validation_type="test",
                result="PASS",
                timestamp=datetime.utcnow().isoformat(),
            )
            is False
        )

        assert (
            db.insert_session(session_id="test", started_at=datetime.utcnow().isoformat()) is False
        )

    def test_query_functions_error_handling(self, mock_config, monkeypatch):
        """Test that query functions handle database errors gracefully."""
        db = analytics_db.AnalyticsDB()
        db.initialize()

        # Mock get_connection to raise an exception
        def mock_connection(*args, **kwargs):
            raise sqlite3.OperationalError("Database locked")

        monkeypatch.setattr(db, "get_connection", mock_connection)

        # Query functions should return empty lists on error
        assert db.query_agent_performance() == []
        assert db.query_tool_usage() == []
        assert db.query_error_patterns() == []
        assert db.get_session_summary("test_session") is None

    def test_insert_event_with_all_event_types(self, mock_config):
        """Test insert_event convenience function with all event types."""
        analytics_db.get_analytics_db().initialize()

        # Test all event types
        assert (
            analytics_db.insert_event(
                "agent_invocation",
                {
                    "session_id": "test",
                    "event_id": "evt_001",
                    "agent": "agent1",
                    "invoked_by": "user",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            is True
        )

        assert (
            analytics_db.insert_event(
                "tool_usage",
                {
                    "session_id": "test",
                    "event_id": "evt_002",
                    "agent": "agent1",
                    "tool": "Read",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            is True
        )

        assert (
            analytics_db.insert_event(
                "error",
                {
                    "session_id": "test",
                    "event_id": "evt_003",
                    "agent": "agent1",
                    "error_type": "TestError",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            is True
        )

        assert (
            analytics_db.insert_event(
                "file_operation",
                {
                    "session_id": "test",
                    "event_id": "evt_004",
                    "agent": "agent1",
                    "operation": "read",
                    "file_path": "test.py",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            is True
        )

        assert (
            analytics_db.insert_event(
                "decision",
                {
                    "session_id": "test",
                    "event_id": "evt_005",
                    "agent": "agent1",
                    "question": "Test?",
                    "selected": "Option A",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            is True
        )

        assert (
            analytics_db.insert_event(
                "validation",
                {
                    "session_id": "test",
                    "event_id": "evt_006",
                    "agent": "agent1",
                    "task": "Task 1",
                    "validation_type": "test",
                    "result": "PASS",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            is True
        )

        # Test unknown event type returns False
        assert (
            analytics_db.insert_event(
                "unknown_type", {"session_id": "test", "event_id": "evt_007", "agent": "agent1"}
            )
            is False
        )
