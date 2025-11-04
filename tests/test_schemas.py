"""
Comprehensive tests for event schema validation (src/core/schemas.py)

Tests all 7 event types, validation logic, serialization, and edge cases.
Target: 100% test coverage on schemas module.

Test Categories:
1. Base Event Tests - Common fields validation
2. Agent Invocation Event Tests
3. Tool Usage Event Tests
4. File Operation Event Tests
5. Decision Event Tests
6. Error Event Tests
7. Context Snapshot Event Tests
8. Validation Event Tests
9. Helper Function Tests (validate_event, serialize_event)
10. Edge Cases and Error Conditions
"""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any

from src.core.schemas import (
    BaseEvent,
    AgentInvocationEvent,
    AgentStatus,
    ToolUsageEvent,
    FileOperationEvent,
    FileOperationType,
    DecisionEvent,
    ErrorEvent,
    ErrorSeverity,
    ContextSnapshotEvent,
    ValidationEvent,
    ValidationStatus,
    EVENT_TYPE_REGISTRY,
    validate_event,
    serialize_event,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def base_event_data() -> Dict[str, Any]:
    """Common fields for all events."""
    return {
        "event_type": "test_event",
        "timestamp": "2025-11-02T15:30:00Z",
        "session_id": "session_20251102_153000",
        "event_id": "evt_001",
        "parent_event_id": None,
    }


@pytest.fixture
def agent_invocation_data(base_event_data) -> Dict[str, Any]:
    """Valid agent invocation event data."""
    data = base_event_data.copy()
    data.update({
        "event_type": "agent_invocation",
        "agent": "orchestrator",
        "invoked_by": "user",
        "reason": "Start Phase 1",
        "status": "started",
    })
    return data


# ============================================================================
# 1. Base Event Tests
# ============================================================================

class TestBaseEvent:
    """Test base event validation and common fields."""

    def test_base_event_valid(self, base_event_data):
        """Test creating a valid base event."""
        event = BaseEvent(**base_event_data)
        assert event.event_type == "test_event"
        assert event.session_id == "session_20251102_153000"
        assert event.event_id == "evt_001"

    def test_timestamp_validation_valid_iso(self, base_event_data):
        """Test timestamp validation with valid ISO 8601 formats."""
        valid_timestamps = [
            "2025-11-02T15:30:00Z",
            "2025-11-02T15:30:00.123Z",
            "2025-11-02T15:30:00+00:00",
            "2025-11-02T15:30:00-05:00",
        ]
        for timestamp in valid_timestamps:
            data = base_event_data.copy()
            data["timestamp"] = timestamp
            event = BaseEvent(**data)
            assert event.timestamp == timestamp

    def test_timestamp_validation_invalid(self, base_event_data):
        """Test timestamp validation with invalid formats."""
        invalid_timestamps = [
            "2025-11-02",  # Date only
            "15:30:00",  # Time only
            "not-a-timestamp",  # Invalid string
            "2025/11/02 15:30:00",  # Wrong format
        ]
        for timestamp in invalid_timestamps:
            data = base_event_data.copy()
            data["timestamp"] = timestamp
            with pytest.raises(ValueError, match="Invalid ISO 8601 timestamp"):
                BaseEvent(**data)

    def test_event_id_validation_valid(self, base_event_data):
        """Test event_id validation with valid formats."""
        valid_ids = ["evt_001", "evt_999", "evt_12345"]
        for event_id in valid_ids:
            data = base_event_data.copy()
            data["event_id"] = event_id
            event = BaseEvent(**data)
            assert event.event_id == event_id

    def test_event_id_validation_invalid(self, base_event_data):
        """Test event_id validation with invalid formats."""
        invalid_ids = ["001", "event_001", "evt001", ""]
        for event_id in invalid_ids:
            data = base_event_data.copy()
            data["event_id"] = event_id
            with pytest.raises(ValueError, match="event_id must start with 'evt_'"):
                BaseEvent(**data)

    def test_session_id_validation_valid(self, base_event_data):
        """Test session_id validation with valid formats."""
        valid_ids = [
            "session_20251102_153000",
            "session_20240101_000000",
            "session_test_123",
        ]
        for session_id in valid_ids:
            data = base_event_data.copy()
            data["session_id"] = session_id
            event = BaseEvent(**data)
            assert event.session_id == session_id

    def test_session_id_validation_invalid(self, base_event_data):
        """Test session_id validation with invalid formats."""
        invalid_ids = ["20251102_153000", "sess_123", "test", ""]
        for session_id in invalid_ids:
            data = base_event_data.copy()
            data["session_id"] = session_id
            with pytest.raises(ValueError, match="session_id must start with 'session_'"):
                BaseEvent(**data)

    def test_parent_event_id_optional(self, base_event_data):
        """Test that parent_event_id is optional."""
        # Without parent_event_id
        event1 = BaseEvent(**base_event_data)
        assert event1.parent_event_id is None

        # With parent_event_id
        data = base_event_data.copy()
        data["parent_event_id"] = "evt_000"
        event2 = BaseEvent(**data)
        assert event2.parent_event_id == "evt_000"


# ============================================================================
# 2. Agent Invocation Event Tests
# ============================================================================

class TestAgentInvocationEvent:
    """Test agent invocation event schema."""

    def test_agent_invocation_started(self, agent_invocation_data):
        """Test agent invocation with 'started' status."""
        event = AgentInvocationEvent(**agent_invocation_data)
        assert event.event_type == "agent_invocation"
        assert event.agent == "orchestrator"
        assert event.invoked_by == "user"
        assert event.reason == "Start Phase 1"
        assert event.status == AgentStatus.STARTED

    def test_agent_invocation_completed(self, agent_invocation_data):
        """Test agent invocation with 'completed' status."""
        data = agent_invocation_data.copy()
        data.update({
            "status": "completed",
            "duration_ms": 5000,
            "tokens_consumed": 1500,
            "result": {"tasks_completed": 3, "files_created": 2},
        })
        event = AgentInvocationEvent(**data)
        assert event.status == AgentStatus.COMPLETED
        assert event.duration_ms == 5000
        assert event.tokens_consumed == 1500
        assert event.result["tasks_completed"] == 3

    def test_agent_invocation_failed(self, agent_invocation_data):
        """Test agent invocation with 'failed' status."""
        data = agent_invocation_data.copy()
        data.update({
            "status": "failed",
            "result": {"error": "Task failed due to timeout"},
        })
        event = AgentInvocationEvent(**data)
        assert event.status == AgentStatus.FAILED
        assert "error" in event.result

    def test_agent_invocation_with_context(self, agent_invocation_data):
        """Test agent invocation with additional context."""
        data = agent_invocation_data.copy()
        data["context"] = {"phase": 1, "task": "1.1", "priority": "critical"}
        event = AgentInvocationEvent(**data)
        assert event.context["phase"] == 1
        assert event.context["task"] == "1.1"


# ============================================================================
# 3. Tool Usage Event Tests
# ============================================================================

class TestToolUsageEvent:
    """Test tool usage event schema."""

    def test_tool_usage_success(self, base_event_data):
        """Test successful tool usage."""
        data = base_event_data.copy()
        data.update({
            "event_type": "tool_usage",
            "agent": "config-architect",
            "tool": "Write",
            "operation": "create_file",
            "parameters": {"file_path": "/path/to/file.py", "content": "# Code here"},
            "success": True,
            "duration_ms": 150,
        })
        event = ToolUsageEvent(**data)
        assert event.tool == "Write"
        assert event.success is True
        assert event.duration_ms == 150
        assert event.error_message is None

    def test_tool_usage_failure(self, base_event_data):
        """Test failed tool usage."""
        data = base_event_data.copy()
        data.update({
            "event_type": "tool_usage",
            "agent": "refactor-agent",
            "tool": "Edit",
            "success": False,
            "error_message": "File not found: /path/to/missing.py",
            "duration_ms": 50,
        })
        event = ToolUsageEvent(**data)
        assert event.success is False
        assert event.error_message == "File not found: /path/to/missing.py"

    def test_tool_usage_minimal(self, base_event_data):
        """Test tool usage with minimal required fields."""
        data = base_event_data.copy()
        data.update({
            "event_type": "tool_usage",
            "agent": "test-engineer",
            "tool": "Bash",
        })
        event = ToolUsageEvent(**data)
        assert event.tool == "Bash"
        assert event.success is True  # Default value
        assert event.parameters is None


# ============================================================================
# 4. File Operation Event Tests
# ============================================================================

class TestFileOperationEvent:
    """Test file operation event schema."""

    def test_file_create_operation(self, base_event_data):
        """Test file creation event."""
        data = base_event_data.copy()
        data.update({
            "event_type": "file_operation",
            "agent": "config-architect",
            "operation": "create",
            "file_path": "/src/core/schemas.py",
            "lines_changed": 300,
            "file_size_bytes": 15000,
            "language": "python",
        })
        event = FileOperationEvent(**data)
        assert event.operation == FileOperationType.CREATE
        assert event.file_path == "/src/core/schemas.py"
        assert event.lines_changed == 300
        assert event.language == "python"

    def test_file_modify_operation(self, base_event_data):
        """Test file modification event."""
        data = base_event_data.copy()
        data.update({
            "event_type": "file_operation",
            "agent": "refactor-agent",
            "operation": "modify",
            "file_path": "/src/core/config.py",
            "lines_changed": 15,
            "diff": "+Added new config option\n-Removed old option",
            "git_hash_before": "abc123",
            "git_hash_after": "def456",
        })
        event = FileOperationEvent(**data)
        assert event.operation == FileOperationType.MODIFY
        assert event.diff is not None
        assert event.git_hash_before == "abc123"

    def test_file_delete_operation(self, base_event_data):
        """Test file deletion event."""
        data = base_event_data.copy()
        data.update({
            "event_type": "file_operation",
            "agent": "refactor-agent",
            "operation": "delete",
            "file_path": "/src/old_module.py",
        })
        event = FileOperationEvent(**data)
        assert event.operation == FileOperationType.DELETE


# ============================================================================
# 5. Decision Event Tests
# ============================================================================

class TestDecisionEvent:
    """Test decision event schema."""

    def test_decision_basic(self, base_event_data):
        """Test basic decision event."""
        data = base_event_data.copy()
        data.update({
            "event_type": "decision",
            "agent": "orchestrator",
            "question": "Which agent should handle structured logging?",
            "options": ["config-architect", "refactor-agent", "doc-writer"],
            "selected": "config-architect",
            "rationale": "Best suited for infrastructure work",
        })
        event = DecisionEvent(**data)
        assert event.question == "Which agent should handle structured logging?"
        assert len(event.options) == 3
        assert event.selected == "config-architect"
        assert event.confidence is None

    def test_decision_with_confidence(self, base_event_data):
        """Test decision event with confidence score."""
        data = base_event_data.copy()
        data.update({
            "event_type": "decision",
            "agent": "orchestrator",
            "question": "Should we use MongoDB or SQLite?",
            "options": ["MongoDB", "SQLite"],
            "selected": "SQLite",
            "rationale": "Simpler for MVP phase",
            "confidence": 0.85,
            "alternative_considered": "MongoDB",
        })
        event = DecisionEvent(**data)
        assert event.confidence == 0.85
        assert event.alternative_considered == "MongoDB"

    def test_decision_confidence_validation(self, base_event_data):
        """Test confidence score validation (0.0-1.0)."""
        data = base_event_data.copy()
        data.update({
            "event_type": "decision",
            "agent": "orchestrator",
            "question": "Test question?",
            "options": ["A", "B"],
            "selected": "A",
            "rationale": "Testing",
            "confidence": 1.5,  # Invalid: > 1.0
        })
        with pytest.raises(ValueError):
            DecisionEvent(**data)


# ============================================================================
# 6. Error Event Tests
# ============================================================================

class TestErrorEvent:
    """Test error event schema."""

    def test_error_basic(self, base_event_data):
        """Test basic error event."""
        data = base_event_data.copy()
        data.update({
            "event_type": "error",
            "agent": "test-engineer",
            "error_type": "ImportError",
            "error_message": "No module named 'pydantic'",
            "context": {"file": "schemas.py", "line": 15, "operation": "import"},
        })
        event = ErrorEvent(**data)
        assert event.error_type == "ImportError"
        assert event.error_message == "No module named 'pydantic'"
        assert event.severity == ErrorSeverity.MEDIUM  # Default

    def test_error_with_fix_successful(self, base_event_data):
        """Test error event with successful fix."""
        data = base_event_data.copy()
        data.update({
            "event_type": "error",
            "agent": "config-architect",
            "error_type": "ValidationError",
            "error_message": "Invalid configuration format",
            "severity": "high",
            "context": {"config_key": "api_timeout", "invalid_value": "abc"},
            "attempted_fix": "Corrected value to numeric type",
            "fix_successful": True,
            "recovery_time_ms": 250,
        })
        event = ErrorEvent(**data)
        assert event.severity == ErrorSeverity.HIGH
        assert event.fix_successful is True
        assert event.recovery_time_ms == 250

    def test_error_with_stack_trace(self, base_event_data):
        """Test error event with stack trace."""
        data = base_event_data.copy()
        data.update({
            "event_type": "error",
            "agent": "performance-agent",
            "error_type": "TimeoutError",
            "error_message": "Operation timed out after 30s",
            "severity": "critical",
            "context": {"operation": "database_query", "timeout_seconds": 30},
            "stack_trace": "File 'db.py', line 45, in execute_query\n  result = conn.execute(query)",
        })
        event = ErrorEvent(**data)
        assert event.severity == ErrorSeverity.CRITICAL
        assert event.stack_trace is not None


# ============================================================================
# 7. Context Snapshot Event Tests
# ============================================================================

class TestContextSnapshotEvent:
    """Test context snapshot event schema."""

    def test_context_snapshot_basic(self, base_event_data):
        """Test basic context snapshot."""
        data = base_event_data.copy()
        data.update({
            "event_type": "context_snapshot",
            "tokens_before": 5000,
            "tokens_after": 8000,
            "tokens_consumed": 3000,
            "tokens_remaining": 192000,
            "files_in_context": ["/src/core/schemas.py", "/src/core/config.py"],
            "files_in_context_count": 2,
        })
        event = ContextSnapshotEvent(**data)
        assert event.tokens_consumed == 3000
        assert event.tokens_remaining == 192000
        assert len(event.files_in_context) == 2

    def test_context_snapshot_with_agent(self, base_event_data):
        """Test context snapshot associated with agent."""
        data = base_event_data.copy()
        data.update({
            "event_type": "context_snapshot",
            "tokens_before": 10000,
            "tokens_after": 15000,
            "tokens_consumed": 5000,
            "tokens_remaining": 185000,
            "files_in_context": ["/test.py"],
            "files_in_context_count": 1,
            "agent": "refactor-agent",
            "memory_mb": 128.5,
        })
        event = ContextSnapshotEvent(**data)
        assert event.agent == "refactor-agent"
        assert event.memory_mb == 128.5


# ============================================================================
# 8. Validation Event Tests
# ============================================================================

class TestValidationEvent:
    """Test validation event schema."""

    def test_validation_pass(self, base_event_data):
        """Test validation event with all checks passing."""
        data = base_event_data.copy()
        data.update({
            "event_type": "validation",
            "agent": "test-engineer",
            "task": "Task 1.1",
            "validation_type": "unit_test",
            "checks": {
                "test_schemas": "pass",
                "test_config": "pass",
                "test_logger": "pass",
            },
            "result": "pass",
            "metrics": {"test_coverage": 95, "tests_passed": 45, "tests_total": 45},
        })
        event = ValidationEvent(**data)
        assert event.result == ValidationStatus.PASS
        assert all(v == "pass" for v in event.checks.values())
        assert event.failures is None

    def test_validation_fail(self, base_event_data):
        """Test validation event with failures."""
        data = base_event_data.copy()
        data.update({
            "event_type": "validation",
            "agent": "test-engineer",
            "task": "Integration tests",
            "validation_type": "integration_test",
            "checks": {
                "test_backup": "pass",
                "test_recovery": "fail",
                "test_analytics": "pass",
            },
            "result": "fail",
            "failures": ["test_recovery: Snapshot restoration failed"],
        })
        event = ValidationEvent(**data)
        assert event.result == ValidationStatus.FAIL
        assert len(event.failures) == 1

    def test_validation_warning(self, base_event_data):
        """Test validation event with warnings."""
        data = base_event_data.copy()
        data.update({
            "event_type": "validation",
            "agent": "performance-agent",
            "task": "Performance benchmarks",
            "validation_type": "performance",
            "checks": {
                "logging_speed": "pass",
                "snapshot_speed": "warning",
            },
            "result": "warning",
            "warnings": ["Snapshot creation took 120ms (target: <100ms)"],
            "metrics": {"logging_ms": 0.8, "snapshot_ms": 120},
        })
        event = ValidationEvent(**data)
        assert event.result == ValidationStatus.WARNING
        assert len(event.warnings) == 1


# ============================================================================
# 9. Helper Function Tests
# ============================================================================

class TestHelperFunctions:
    """Test validate_event and serialize_event helper functions."""

    def test_validate_event_agent_invocation(self, agent_invocation_data):
        """Test validate_event with agent invocation data."""
        event = validate_event(agent_invocation_data)
        assert isinstance(event, AgentInvocationEvent)
        assert event.agent == "orchestrator"

    def test_validate_event_all_types(self, base_event_data):
        """Test validate_event with all event types."""
        for event_type, event_class in EVENT_TYPE_REGISTRY.items():
            data = base_event_data.copy()
            data["event_type"] = event_type

            # Add required fields for each type
            if event_type == "agent_invocation":
                data.update({"agent": "test", "invoked_by": "user", "reason": "test"})
            elif event_type == "tool_usage":
                data.update({"agent": "test", "tool": "Read"})
            elif event_type == "file_operation":
                data.update({"agent": "test", "operation": "create", "file_path": "/test.py"})
            elif event_type == "decision":
                data.update({
                    "agent": "test",
                    "question": "Test?",
                    "options": ["A", "B"],
                    "selected": "A",
                    "rationale": "Test",
                })
            elif event_type == "error":
                data.update({
                    "agent": "test",
                    "error_type": "TestError",
                    "error_message": "Test error",
                    "context": {"test": True},
                })
            elif event_type == "context_snapshot":
                data.update({
                    "tokens_before": 0,
                    "tokens_after": 100,
                    "tokens_consumed": 100,
                    "tokens_remaining": 199900,
                    "files_in_context": [],
                    "files_in_context_count": 0,
                })
            elif event_type == "validation":
                data.update({
                    "agent": "test",
                    "task": "Test",
                    "validation_type": "unit_test",
                    "checks": {"test": "pass"},
                    "result": "pass",
                })

            event = validate_event(data)
            assert isinstance(event, event_class)

    def test_validate_event_missing_type(self, base_event_data):
        """Test validate_event with missing event_type."""
        data = base_event_data.copy()
        del data["event_type"]
        with pytest.raises(ValueError, match="Event data must contain 'event_type' field"):
            validate_event(data)

    def test_validate_event_unknown_type(self, base_event_data):
        """Test validate_event with unknown event_type."""
        data = base_event_data.copy()
        data["event_type"] = "unknown_event_type"
        with pytest.raises(ValueError, match="Unknown event type"):
            validate_event(data)

    def test_serialize_event(self, agent_invocation_data):
        """Test serialize_event produces JSON-compatible dict."""
        event = AgentInvocationEvent(**agent_invocation_data)
        data = serialize_event(event)

        assert isinstance(data, dict)
        assert data["event_type"] == "agent_invocation"
        assert data["agent"] == "orchestrator"
        assert "status" in data

    def test_serialize_event_excludes_none(self, base_event_data):
        """Test serialize_event excludes None values."""
        data = base_event_data.copy()
        data.update({
            "event_type": "tool_usage",
            "agent": "test",
            "tool": "Read",
        })
        event = ToolUsageEvent(**data)
        serialized = serialize_event(event)

        # None values should be excluded
        assert "error_message" not in serialized
        assert "result_summary" not in serialized


# ============================================================================
# 10. Edge Cases and Error Conditions
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_extra_fields_allowed(self, base_event_data):
        """Test that extra fields are allowed (for future extensibility)."""
        data = base_event_data.copy()
        data["custom_field"] = "custom_value"
        event = BaseEvent(**data)
        # Pydantic v2 with extra='allow' should accept this
        assert hasattr(event, "custom_field")

    def test_string_whitespace_stripping(self, base_event_data):
        """Test that string fields are stripped of whitespace."""
        data = base_event_data.copy()
        data["event_type"] = "  test_event  "
        event = BaseEvent(**data)
        assert event.event_type == "test_event"  # Whitespace stripped

    def test_enum_values(self):
        """Test enum value definitions."""
        assert AgentStatus.STARTED.value == "started"
        assert FileOperationType.CREATE.value == "create"
        assert ErrorSeverity.HIGH.value == "high"
        assert ValidationStatus.PASS.value == "pass"

    def test_event_type_registry_complete(self):
        """Test that EVENT_TYPE_REGISTRY contains all event types."""
        expected_types = {
            "agent_invocation",
            "tool_usage",
            "file_operation",
            "decision",
            "error",
            "context_snapshot",
            "validation",
        }
        assert set(EVENT_TYPE_REGISTRY.keys()) == expected_types

    def test_missing_required_fields(self, base_event_data):
        """Test that missing required fields raise validation errors."""
        # AgentInvocationEvent requires: agent, invoked_by, reason
        data = base_event_data.copy()
        data["event_type"] = "agent_invocation"
        # Missing agent, invoked_by, reason
        with pytest.raises(ValueError):
            AgentInvocationEvent(**data)

    def test_roundtrip_serialization(self, agent_invocation_data):
        """Test that serialization and deserialization preserve data."""
        # Create event
        event1 = AgentInvocationEvent(**agent_invocation_data)

        # Serialize
        serialized = serialize_event(event1)

        # Deserialize
        event2 = validate_event(serialized)

        # Compare
        assert event1.event_id == event2.event_id
        assert event1.agent == event2.agent
        assert event1.reason == event2.reason


# ============================================================================
# Performance Tests (optional)
# ============================================================================

class TestPerformance:
    """Test schema validation performance."""

    def test_validation_performance(self, agent_invocation_data, benchmark=None):
        """Test that schema validation is fast (<1ms per event)."""
        if benchmark is None:
            pytest.skip("Benchmark not available (install pytest-benchmark)")

        def create_event():
            return AgentInvocationEvent(**agent_invocation_data)

        # Note: pytest-benchmark is optional, this test will skip if not installed
        # In a real run: benchmark(create_event)
        # For now, just verify it works quickly
        import time
        start = time.perf_counter()
        for _ in range(1000):
            create_event()
        elapsed_ms = (time.perf_counter() - start) * 1000
        avg_ms = elapsed_ms / 1000
        assert avg_ms < 1.0, f"Validation took {avg_ms:.3f}ms (target: <1ms)"
