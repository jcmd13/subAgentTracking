"""
Test suite for Event Type Definitions & Schema Validation

Links Back To: Main Plan → Phase 1 → Task 1.2 → Testing Requirements
Coverage Target: 100% on event_types module

Test Categories:
1. Valid Payload Tests (20 tests - one per event type)
2. Invalid Payload Tests (40 tests - 2 per event type)
3. Schema Utility Functions (6 tests)
4. Edge Cases (4 tests)
"""

import pytest
from src.core.event_types import (
    # Event type constants
    AGENT_INVOKED, AGENT_COMPLETED, AGENT_FAILED, AGENT_TIMEOUT, AGENT_HANDOFF,
    TOOL_USED, TOOL_ERROR, TOOL_PERFORMANCE, TOOL_QUOTA_EXCEEDED,
    SNAPSHOT_CREATED, SNAPSHOT_RESTORED, SNAPSHOT_FAILED, SNAPSHOT_CLEANUP,
    SESSION_STARTED, SESSION_TOKEN_WARNING, SESSION_HANDOFF_REQUIRED, SESSION_ENDED,
    COST_TRACKED, COST_BUDGET_WARNING, COST_OPTIMIZATION_OPPORTUNITY,
    ALL_EVENT_TYPES,
    # Validation functions
    validate_event_payload, get_schema, get_all_event_types,
    is_valid_event_type, get_required_fields, get_optional_fields,
    EventValidationError
)


# ============================================================================
# Category 1: Valid Payload Tests (20 tests - one per event type)
# ============================================================================

def test_agent_invoked_valid():
    """Test valid AGENT_INVOKED payload"""
    payload = {
        "agent": "refactor-agent",
        "invoked_by": "orchestrator",
        "reason": "Task 1.1: Refactor event bus for better performance"
    }
    assert validate_event_payload(AGENT_INVOKED, payload) is True


def test_agent_invoked_valid_with_optional():
    """Test valid AGENT_INVOKED payload with optional fields"""
    payload = {
        "agent": "refactor-agent",
        "invoked_by": "user",
        "reason": "Refactoring needed",
        "model_tier": "base",
        "context_tokens": 50000
    }
    assert validate_event_payload(AGENT_INVOKED, payload) is True


def test_agent_completed_valid():
    """Test valid AGENT_COMPLETED payload"""
    payload = {
        "agent": "refactor-agent",
        "duration_ms": 15000,
        "tokens_used": 25000,
        "exit_code": 0
    }
    assert validate_event_payload(AGENT_COMPLETED, payload) is True


def test_agent_completed_valid_with_optional():
    """Test valid AGENT_COMPLETED payload with optional fields"""
    payload = {
        "agent": "test-engineer",
        "duration_ms": 30000,
        "tokens_used": 45000,
        "input_tokens": 40000,
        "output_tokens": 5000,
        "exit_code": 0,
        "model": "claude-sonnet-4",
        "result_summary": "All tests passing"
    }
    assert validate_event_payload(AGENT_COMPLETED, payload) is True


def test_agent_failed_valid():
    """Test valid AGENT_FAILED payload"""
    payload = {
        "agent": "ui-builder",
        "error_type": "ValidationError",
        "error_msg": "Invalid component structure"
    }
    assert validate_event_payload(AGENT_FAILED, payload) is True


def test_agent_timeout_valid():
    """Test valid AGENT_TIMEOUT payload"""
    payload = {
        "agent": "performance-agent",
        "timeout_ms": 60000
    }
    assert validate_event_payload(AGENT_TIMEOUT, payload) is True


def test_agent_handoff_valid():
    """Test valid AGENT_HANDOFF payload"""
    payload = {
        "from_agent": "orchestrator-agent",
        "to_agent": "refactor-agent",
        "context_summary": "Need to refactor the event bus architecture for better modularity"
    }
    assert validate_event_payload(AGENT_HANDOFF, payload) is True


def test_tool_used_valid():
    """Test valid TOOL_USED payload"""
    payload = {
        "agent": "refactor-agent",
        "tool": "Read",
        "success": True
    }
    assert validate_event_payload(TOOL_USED, payload) is True


def test_tool_error_valid():
    """Test valid TOOL_ERROR payload"""
    payload = {
        "agent": "doc-writer",
        "tool": "Write",
        "error_type": "PermissionError"
    }
    assert validate_event_payload(TOOL_ERROR, payload) is True


def test_tool_performance_valid():
    """Test valid TOOL_PERFORMANCE payload"""
    payload = {
        "tool": "Grep",
        "duration_ms": 250
    }
    assert validate_event_payload(TOOL_PERFORMANCE, payload) is True


def test_tool_quota_exceeded_valid():
    """Test valid TOOL_QUOTA_EXCEEDED payload"""
    payload = {
        "tool": "WebSearch",
        "quota_type": "api_calls",
        "limit": 100,
        "current": 105
    }
    assert validate_event_payload(TOOL_QUOTA_EXCEEDED, payload) is True


def test_snapshot_created_valid():
    """Test valid SNAPSHOT_CREATED payload"""
    payload = {
        "snapshot_id": "snap_20251115_123456",
        "trigger": "agent_count_10",
        "size_bytes": 1024000
    }
    assert validate_event_payload(SNAPSHOT_CREATED, payload) is True


def test_snapshot_restored_valid():
    """Test valid SNAPSHOT_RESTORED payload"""
    payload = {
        "snapshot_id": "snap_20251115_123456",
        "restore_strategy": "full"
    }
    assert validate_event_payload(SNAPSHOT_RESTORED, payload) is True


def test_snapshot_failed_valid():
    """Test valid SNAPSHOT_FAILED payload"""
    payload = {
        "trigger": "token_limit_70pct",
        "error_msg": "Disk full"
    }
    assert validate_event_payload(SNAPSHOT_FAILED, payload) is True


def test_snapshot_cleanup_valid():
    """Test valid SNAPSHOT_CLEANUP payload"""
    payload = {
        "deleted_count": 5,
        "space_freed_bytes": 5120000
    }
    assert validate_event_payload(SNAPSHOT_CLEANUP, payload) is True


def test_session_started_valid():
    """Test valid SESSION_STARTED payload"""
    payload = {
        "session_id": "session_20251115_123456"
    }
    assert validate_event_payload(SESSION_STARTED, payload) is True


def test_session_token_warning_valid():
    """Test valid SESSION_TOKEN_WARNING payload"""
    payload = {
        "session_id": "session_20251115_123456",
        "tokens_used": 105000,
        "tokens_limit": 150000,
        "percent": 70.0
    }
    assert validate_event_payload(SESSION_TOKEN_WARNING, payload) is True


def test_session_handoff_required_valid():
    """Test valid SESSION_HANDOFF_REQUIRED payload"""
    payload = {
        "session_id": "session_20251115_123456",
        "reason": "token_limit"
    }
    assert validate_event_payload(SESSION_HANDOFF_REQUIRED, payload) is True


def test_session_ended_valid():
    """Test valid SESSION_ENDED payload"""
    payload = {
        "session_id": "session_20251115_123456",
        "duration_minutes": 45.5,
        "total_tokens": 125000
    }
    assert validate_event_payload(SESSION_ENDED, payload) is True


def test_cost_tracked_valid():
    """Test valid COST_TRACKED payload"""
    payload = {
        "model": "claude-sonnet-4",
        "tokens": 25000,
        "cost_usd": 0.75
    }
    assert validate_event_payload(COST_TRACKED, payload) is True


def test_cost_budget_warning_valid():
    """Test valid COST_BUDGET_WARNING payload"""
    payload = {
        "budget_type": "daily",
        "spent": 7.50,
        "limit": 10.00,
        "percent": 75.0
    }
    assert validate_event_payload(COST_BUDGET_WARNING, payload) is True


def test_cost_optimization_opportunity_valid():
    """Test valid COST_OPTIMIZATION_OPPORTUNITY payload"""
    payload = {
        "recommendation": "Use Haiku for simple log analysis tasks",
        "potential_savings": 5.25
    }
    assert validate_event_payload(COST_OPTIMIZATION_OPPORTUNITY, payload) is True


# ============================================================================
# Category 2: Invalid Payload Tests (40 tests - 2 per event type)
# ============================================================================

def test_agent_invoked_missing_required():
    """Test AGENT_INVOKED with missing required field"""
    payload = {
        "agent": "test-agent",
        "invoked_by": "user"
        # Missing 'reason'
    }
    with pytest.raises(EventValidationError, match="reason"):
        validate_event_payload(AGENT_INVOKED, payload)


def test_agent_invoked_short_reason():
    """Test AGENT_INVOKED with reason too short"""
    payload = {
        "agent": "test-agent",
        "invoked_by": "user",
        "reason": "short"  # Less than 10 chars
    }
    with pytest.raises(EventValidationError):
        validate_event_payload(AGENT_INVOKED, payload)


def test_agent_completed_missing_duration():
    """Test AGENT_COMPLETED missing duration_ms"""
    payload = {
        "agent": "test-agent",
        "tokens_used": 1000,
        "exit_code": 0
    }
    with pytest.raises(EventValidationError, match="duration_ms"):
        validate_event_payload(AGENT_COMPLETED, payload)


def test_agent_completed_negative_tokens():
    """Test AGENT_COMPLETED with negative tokens"""
    payload = {
        "agent": "test-agent",
        "duration_ms": 1000,
        "tokens_used": -100,  # Negative not allowed
        "exit_code": 0
    }
    with pytest.raises(EventValidationError):
        validate_event_payload(AGENT_COMPLETED, payload)


def test_agent_failed_missing_error_type():
    """Test AGENT_FAILED missing error_type"""
    payload = {
        "agent": "test-agent",
        "error_msg": "Something went wrong"
    }
    with pytest.raises(EventValidationError, match="error_type"):
        validate_event_payload(AGENT_FAILED, payload)


def test_agent_failed_wrong_type():
    """Test AGENT_FAILED with wrong field type"""
    payload = {
        "agent": "test-agent",
        "error_type": "ValidationError",
        "error_msg": 12345  # Should be string, not int
    }
    with pytest.raises(EventValidationError):
        validate_event_payload(AGENT_FAILED, payload)


def test_agent_timeout_missing_timeout():
    """Test AGENT_TIMEOUT missing timeout_ms"""
    payload = {
        "agent": "test-agent"
    }
    with pytest.raises(EventValidationError, match="timeout_ms"):
        validate_event_payload(AGENT_TIMEOUT, payload)


def test_agent_timeout_negative_timeout():
    """Test AGENT_TIMEOUT with negative timeout"""
    payload = {
        "agent": "test-agent",
        "timeout_ms": -1000
    }
    with pytest.raises(EventValidationError):
        validate_event_payload(AGENT_TIMEOUT, payload)


def test_agent_handoff_short_summary():
    """Test AGENT_HANDOFF with summary too short"""
    payload = {
        "from_agent": "agent1",
        "to_agent": "agent2",
        "context_summary": "short"  # Less than 20 chars
    }
    with pytest.raises(EventValidationError):
        validate_event_payload(AGENT_HANDOFF, payload)


def test_agent_handoff_missing_to_agent():
    """Test AGENT_HANDOFF missing to_agent"""
    payload = {
        "from_agent": "agent1",
        "context_summary": "This is a long enough summary for the handoff"
    }
    with pytest.raises(EventValidationError, match="to_agent"):
        validate_event_payload(AGENT_HANDOFF, payload)


def test_tool_used_missing_success():
    """Test TOOL_USED missing success field"""
    payload = {
        "agent": "test-agent",
        "tool": "Read"
    }
    with pytest.raises(EventValidationError, match="success"):
        validate_event_payload(TOOL_USED, payload)


def test_tool_used_wrong_success_type():
    """Test TOOL_USED with wrong type for success"""
    payload = {
        "agent": "test-agent",
        "tool": "Write",
        "success": "yes"  # Should be boolean
    }
    with pytest.raises(EventValidationError):
        validate_event_payload(TOOL_USED, payload)


def test_tool_error_missing_tool():
    """Test TOOL_ERROR missing tool field"""
    payload = {
        "agent": "test-agent",
        "error_type": "FileNotFoundError"
    }
    with pytest.raises(EventValidationError, match="tool"):
        validate_event_payload(TOOL_ERROR, payload)


def test_tool_error_empty_agent():
    """Test TOOL_ERROR with empty agent"""
    payload = {
        "agent": "",
        "tool": "Read",
        "error_type": "Error"
    }
    # Empty string is still a string, so this should pass schema validation
    # (business logic validation would catch this separately)
    assert validate_event_payload(TOOL_ERROR, payload) is True


def test_tool_performance_missing_duration():
    """Test TOOL_PERFORMANCE missing duration_ms"""
    payload = {
        "tool": "Grep"
    }
    with pytest.raises(EventValidationError, match="duration_ms"):
        validate_event_payload(TOOL_PERFORMANCE, payload)


def test_tool_performance_negative_duration():
    """Test TOOL_PERFORMANCE with negative duration"""
    payload = {
        "tool": "Grep",
        "duration_ms": -100
    }
    with pytest.raises(EventValidationError):
        validate_event_payload(TOOL_PERFORMANCE, payload)


def test_tool_quota_exceeded_missing_limit():
    """Test TOOL_QUOTA_EXCEEDED missing limit"""
    payload = {
        "tool": "WebSearch",
        "quota_type": "api_calls",
        "current": 105
    }
    with pytest.raises(EventValidationError, match="limit"):
        validate_event_payload(TOOL_QUOTA_EXCEEDED, payload)


def test_tool_quota_exceeded_negative_current():
    """Test TOOL_QUOTA_EXCEEDED with negative current"""
    payload = {
        "tool": "WebSearch",
        "quota_type": "api_calls",
        "limit": 100,
        "current": -5
    }
    with pytest.raises(EventValidationError):
        validate_event_payload(TOOL_QUOTA_EXCEEDED, payload)


def test_snapshot_created_missing_trigger():
    """Test SNAPSHOT_CREATED missing trigger"""
    payload = {
        "snapshot_id": "snap_123",
        "size_bytes": 1000
    }
    with pytest.raises(EventValidationError, match="trigger"):
        validate_event_payload(SNAPSHOT_CREATED, payload)


def test_snapshot_created_negative_size():
    """Test SNAPSHOT_CREATED with negative size"""
    payload = {
        "snapshot_id": "snap_123",
        "trigger": "manual",
        "size_bytes": -1000
    }
    with pytest.raises(EventValidationError):
        validate_event_payload(SNAPSHOT_CREATED, payload)


def test_snapshot_restored_invalid_strategy():
    """Test SNAPSHOT_RESTORED with invalid restore_strategy"""
    payload = {
        "snapshot_id": "snap_123",
        "restore_strategy": "invalid_strategy"  # Not in enum
    }
    with pytest.raises(EventValidationError):
        validate_event_payload(SNAPSHOT_RESTORED, payload)


def test_snapshot_restored_missing_snapshot_id():
    """Test SNAPSHOT_RESTORED missing snapshot_id"""
    payload = {
        "restore_strategy": "full"
    }
    with pytest.raises(EventValidationError, match="snapshot_id"):
        validate_event_payload(SNAPSHOT_RESTORED, payload)


def test_snapshot_failed_missing_error_msg():
    """Test SNAPSHOT_FAILED missing error_msg"""
    payload = {
        "trigger": "manual"
    }
    with pytest.raises(EventValidationError, match="error_msg"):
        validate_event_payload(SNAPSHOT_FAILED, payload)


def test_snapshot_failed_wrong_type():
    """Test SNAPSHOT_FAILED with wrong type for partial_data"""
    payload = {
        "trigger": "manual",
        "error_msg": "Disk full",
        "partial_data": "yes"  # Should be boolean
    }
    with pytest.raises(EventValidationError):
        validate_event_payload(SNAPSHOT_FAILED, payload)


def test_snapshot_cleanup_missing_deleted_count():
    """Test SNAPSHOT_CLEANUP missing deleted_count"""
    payload = {
        "space_freed_bytes": 1000
    }
    with pytest.raises(EventValidationError, match="deleted_count"):
        validate_event_payload(SNAPSHOT_CLEANUP, payload)


def test_snapshot_cleanup_negative_space():
    """Test SNAPSHOT_CLEANUP with negative space_freed"""
    payload = {
        "deleted_count": 5,
        "space_freed_bytes": -1000
    }
    with pytest.raises(EventValidationError):
        validate_event_payload(SNAPSHOT_CLEANUP, payload)


def test_session_started_missing_session_id():
    """Test SESSION_STARTED missing session_id"""
    payload = {
        "phase": 1
    }
    with pytest.raises(EventValidationError, match="session_id"):
        validate_event_payload(SESSION_STARTED, payload)


def test_session_started_negative_phase():
    """Test SESSION_STARTED with negative phase"""
    payload = {
        "session_id": "session_123",
        "phase": -1
    }
    with pytest.raises(EventValidationError):
        validate_event_payload(SESSION_STARTED, payload)


def test_session_token_warning_missing_percent():
    """Test SESSION_TOKEN_WARNING missing percent"""
    payload = {
        "session_id": "session_123",
        "tokens_used": 100000,
        "tokens_limit": 150000
    }
    with pytest.raises(EventValidationError, match="percent"):
        validate_event_payload(SESSION_TOKEN_WARNING, payload)


def test_session_token_warning_percent_out_of_range():
    """Test SESSION_TOKEN_WARNING with percent > 100"""
    payload = {
        "session_id": "session_123",
        "tokens_used": 150000,
        "tokens_limit": 100000,
        "percent": 150.0  # Can't exceed 100%
    }
    with pytest.raises(EventValidationError):
        validate_event_payload(SESSION_TOKEN_WARNING, payload)


def test_session_handoff_required_invalid_reason():
    """Test SESSION_HANDOFF_REQUIRED with invalid reason"""
    payload = {
        "session_id": "session_123",
        "reason": "invalid_reason"  # Not in enum
    }
    with pytest.raises(EventValidationError):
        validate_event_payload(SESSION_HANDOFF_REQUIRED, payload)


def test_session_handoff_required_missing_session_id():
    """Test SESSION_HANDOFF_REQUIRED missing session_id"""
    payload = {
        "reason": "token_limit"
    }
    with pytest.raises(EventValidationError, match="session_id"):
        validate_event_payload(SESSION_HANDOFF_REQUIRED, payload)


def test_session_ended_missing_total_tokens():
    """Test SESSION_ENDED missing total_tokens"""
    payload = {
        "session_id": "session_123",
        "duration_minutes": 45.5
    }
    with pytest.raises(EventValidationError, match="total_tokens"):
        validate_event_payload(SESSION_ENDED, payload)


def test_session_ended_negative_duration():
    """Test SESSION_ENDED with negative duration"""
    payload = {
        "session_id": "session_123",
        "duration_minutes": -10,
        "total_tokens": 100000
    }
    with pytest.raises(EventValidationError):
        validate_event_payload(SESSION_ENDED, payload)


def test_cost_tracked_missing_cost():
    """Test COST_TRACKED missing cost_usd"""
    payload = {
        "model": "claude-sonnet-4",
        "tokens": 25000
    }
    with pytest.raises(EventValidationError, match="cost_usd"):
        validate_event_payload(COST_TRACKED, payload)


def test_cost_tracked_negative_cost():
    """Test COST_TRACKED with negative cost"""
    payload = {
        "model": "claude-sonnet-4",
        "tokens": 25000,
        "cost_usd": -1.50
    }
    with pytest.raises(EventValidationError):
        validate_event_payload(COST_TRACKED, payload)


def test_cost_budget_warning_invalid_budget_type():
    """Test COST_BUDGET_WARNING with invalid budget_type"""
    payload = {
        "budget_type": "yearly",  # Not in enum
        "spent": 50.0,
        "limit": 100.0,
        "percent": 50.0
    }
    with pytest.raises(EventValidationError):
        validate_event_payload(COST_BUDGET_WARNING, payload)


def test_cost_budget_warning_missing_spent():
    """Test COST_BUDGET_WARNING missing spent"""
    payload = {
        "budget_type": "daily",
        "limit": 10.0,
        "percent": 75.0
    }
    with pytest.raises(EventValidationError, match="spent"):
        validate_event_payload(COST_BUDGET_WARNING, payload)


def test_cost_optimization_opportunity_missing_recommendation():
    """Test COST_OPTIMIZATION_OPPORTUNITY missing recommendation"""
    payload = {
        "potential_savings": 5.25
    }
    with pytest.raises(EventValidationError, match="recommendation"):
        validate_event_payload(COST_OPTIMIZATION_OPPORTUNITY, payload)


def test_cost_optimization_opportunity_negative_savings():
    """Test COST_OPTIMIZATION_OPPORTUNITY with negative savings"""
    payload = {
        "recommendation": "Use cheaper model",
        "potential_savings": -5.25
    }
    with pytest.raises(EventValidationError):
        validate_event_payload(COST_OPTIMIZATION_OPPORTUNITY, payload)


# ============================================================================
# Category 3: Schema Utility Functions (6 tests)
# ============================================================================

def test_get_all_event_types():
    """Test get_all_event_types returns all 20 event types"""
    event_types = get_all_event_types()
    assert len(event_types) == 20
    assert AGENT_INVOKED in event_types
    assert COST_OPTIMIZATION_OPPORTUNITY in event_types


def test_is_valid_event_type():
    """Test is_valid_event_type correctly identifies valid/invalid types"""
    assert is_valid_event_type(AGENT_INVOKED) is True
    assert is_valid_event_type("invalid.event") is False
    assert is_valid_event_type("") is False


def test_get_schema():
    """Test get_schema returns correct schema"""
    schema = get_schema(AGENT_INVOKED)
    assert "required" in schema
    assert "agent" in schema["required"]
    assert "properties" in schema


def test_get_schema_unknown_type():
    """Test get_schema raises KeyError for unknown type"""
    with pytest.raises(KeyError):
        get_schema("unknown.event")


def test_get_required_fields():
    """Test get_required_fields returns correct fields"""
    required = get_required_fields(AGENT_INVOKED)
    assert "agent" in required
    assert "invoked_by" in required
    assert "reason" in required
    assert len(required) == 3


def test_get_optional_fields():
    """Test get_optional_fields returns correct fields"""
    optional = get_optional_fields(AGENT_INVOKED)
    assert "model_tier" in optional
    assert "context_tokens" in optional
    # Required fields should not be in optional
    assert "agent" not in optional
    assert "reason" not in optional


# ============================================================================
# Category 4: Edge Cases (4 tests)
# ============================================================================

def test_validate_unknown_event_type():
    """Test validating unknown event type raises error"""
    with pytest.raises(EventValidationError, match="Unknown event type"):
        validate_event_payload("unknown.event", {})


def test_validate_empty_payload():
    """Test validating empty payload for event with required fields"""
    with pytest.raises(EventValidationError):
        validate_event_payload(AGENT_INVOKED, {})


def test_validate_with_extra_fields():
    """Test validation allows extra fields (additionalProperties: True)"""
    payload = {
        "agent": "test-agent",
        "invoked_by": "user",
        "reason": "Testing with extra fields",
        "custom_field": "custom_value",  # Extra field
        "another_custom": 123
    }
    # Should pass - schemas allow additional properties
    assert validate_event_payload(AGENT_INVOKED, payload) is True


def test_all_event_types_have_schemas():
    """Test all event types in ALL_EVENT_TYPES have schemas"""
    for event_type in ALL_EVENT_TYPES:
        # Should not raise exception
        schema = get_schema(event_type)
        assert schema is not None
        assert "properties" in schema
