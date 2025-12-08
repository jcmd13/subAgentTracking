"""
Event Schema Definitions for SubAgent Tracking System

This module defines Pydantic models for all 7 event types used in the tracking system:
1. AgentInvocationEvent - Agent start/completion
2. ToolUsageEvent - Tool invocation with duration
3. FileOperationEvent - File create/modify/delete with diffs
4. DecisionEvent - Decision with rationale and alternatives
5. ErrorEvent - Error with context and fix attempts
6. ContextSnapshotEvent - Token usage and state checkpoint
7. ValidationEvent - Validation check results

All events share common fields and are validated using Pydantic for type safety.

Usage:
    from src.core.schemas import AgentInvocationEvent

    event = AgentInvocationEvent(
        event_type="agent_invocation",
        timestamp="2025-11-02T15:30:00Z",
        session_id="session_20251102_153000",
        event_id="evt_001",
        agent="orchestrator",
        invoked_by="user",
        reason="Start Phase 1"
    )
"""

from datetime import datetime
from typing import Optional, Dict, Any, List, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict
from enum import Enum


# ============================================================================
# Base Event Model
# ============================================================================


class BaseEvent(BaseModel):
    """
    Base model for all tracking events.

    All events inherit these common fields for consistency and correlation.
    """

    model_config = ConfigDict(extra="allow", str_strip_whitespace=True)

    event_type: str = Field(
        ..., description="Type of event (e.g., 'agent_invocation', 'tool_usage')"
    )
    timestamp: str = Field(..., description="ISO 8601 timestamp when event occurred")
    session_id: str = Field(..., description="Session ID (e.g., 'session_20251102_153000')")
    event_id: str = Field(..., description="Unique event ID within session (e.g., 'evt_001')")
    parent_event_id: Optional[str] = Field(None, description="Parent event ID for nested events")

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, v: str) -> str:
        """Validate that timestamp is in valid ISO 8601 format with time component."""
        # Check that the timestamp contains both date and time
        # ISO 8601 format requires 'T' separator or space between date and time
        if "T" not in v and " " not in v:
            raise ValueError(f"Invalid ISO 8601 timestamp: {v} (missing time component)")

        try:
            parsed = datetime.fromisoformat(v.replace("Z", "+00:00"))
            return v
        except (ValueError, AttributeError, TypeError) as e:
            raise ValueError(f"Invalid ISO 8601 timestamp: {v}")

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, v: str) -> str:
        """Validate event_id format (evt_NNN)."""
        if not v.startswith("evt_"):
            raise ValueError(f"event_id must start with 'evt_': {v}")
        return v

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: str) -> str:
        """Validate session_id format (session_YYYYMMDD_HHMMSS)."""
        if not v.startswith("session_"):
            raise ValueError(f"session_id must start with 'session_': {v}")
        return v


# ============================================================================
# Event Type 1: Agent Invocation
# ============================================================================


class AgentStatus(str, Enum):
    """Status of agent invocation."""

    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentInvocationEvent(BaseEvent):
    """
    Tracks agent invocations (start and completion).

    Used to log when agents are invoked, why they were invoked,
    and their execution results.
    """

    event_type: Literal["agent_invocation"] = "agent_invocation"
    agent: str = Field(
        ..., description="Name of the agent (e.g., 'orchestrator', 'config-architect')"
    )
    invoked_by: str = Field(..., description="Who invoked the agent (e.g., 'user', 'orchestrator')")
    reason: str = Field(
        ..., description="Reason for invocation (e.g., 'Task 1.1: Implement event schema')"
    )
    status: AgentStatus = Field(
        AgentStatus.STARTED, description="Agent status (started/completed/failed)"
    )
    context: Optional[Dict[str, Any]] = Field(
        None, description="Additional context about the invocation"
    )
    result: Optional[Dict[str, Any]] = Field(
        None, description="Results from agent execution (if completed)"
    )
    duration_ms: Optional[int] = Field(None, description="Duration in milliseconds (if completed)")
    tokens_consumed: Optional[int] = Field(
        None, description="Tokens consumed by agent (if completed)"
    )


# ============================================================================
# Event Type 2: Tool Usage
# ============================================================================


class ToolUsageEvent(BaseEvent):
    """
    Tracks tool usage by agents.

    Records when tools (Read, Write, Edit, Bash, etc.) are used,
    their parameters, duration, and success status.
    """

    event_type: Literal["tool_usage"] = "tool_usage"
    agent: str = Field(..., description="Agent using the tool")
    tool: str = Field(..., description="Tool name (e.g., 'Read', 'Write', 'Edit', 'Bash')")
    operation: Optional[str] = Field(
        None, description="Specific operation (e.g., 'create_file', 'edit_file')"
    )
    parameters: Optional[Dict[str, Any]] = Field(
        None, description="Tool parameters (e.g., file_path, command)"
    )
    success: bool = Field(True, description="Whether tool execution succeeded")
    duration_ms: Optional[int] = Field(None, description="Duration in milliseconds")
    error_message: Optional[str] = Field(None, description="Error message if tool failed")
    result_summary: Optional[str] = Field(None, description="Brief summary of results")


# ============================================================================
# Event Type 3: File Operation
# ============================================================================


class FileOperationType(str, Enum):
    """Type of file operation."""

    CREATE = "create"
    MODIFY = "modify"
    DELETE = "delete"
    RENAME = "rename"
    READ = "read"


class FileOperationEvent(BaseEvent):
    """
    Tracks file operations performed by agents.

    Records file creates, modifications, deletes with diffs and git hashes
    for complete change tracking.
    """

    event_type: Literal["file_operation"] = "file_operation"
    agent: str = Field(..., description="Agent performing the operation")
    operation: FileOperationType = Field(..., description="Type of file operation")
    file_path: str = Field(..., description="Path to the file")
    lines_changed: Optional[int] = Field(None, description="Number of lines changed (for modify)")
    diff: Optional[str] = Field(None, description="Diff of changes (for modify)")
    git_hash_before: Optional[str] = Field(
        None, description="Git hash before change (if in git repo)"
    )
    git_hash_after: Optional[str] = Field(
        None, description="Git hash after change (if in git repo)"
    )
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")
    language: Optional[str] = Field(
        None, description="Programming language (e.g., 'python', 'javascript')"
    )


# ============================================================================
# Event Type 4: Decision
# ============================================================================


class DecisionEvent(BaseEvent):
    """
    Tracks decision points in agent workflows.

    Records when agents make decisions, the options considered,
    the choice made, and the rationale.
    """

    event_type: Literal["decision"] = "decision"
    agent: str = Field(..., description="Agent making the decision")
    question: str = Field(..., description="Decision question being asked")
    options: List[str] = Field(..., description="Available options to choose from")
    selected: str = Field(..., description="Option that was selected")
    rationale: str = Field(..., description="Explanation for why this option was chosen")
    confidence: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Confidence in decision (0.0-1.0)"
    )
    alternative_considered: Optional[str] = Field(
        None, description="Main alternative that was considered"
    )


# ============================================================================
# Event Type 5: Error
# ============================================================================


class ErrorSeverity(str, Enum):
    """Severity level of error."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorEvent(BaseEvent):
    """
    Tracks errors encountered by agents.

    Records error type, context, attempted fixes, and whether
    the fix was successful for error pattern analysis.
    """

    event_type: Literal["error"] = "error"
    agent: str = Field(..., description="Agent that encountered the error")
    error_type: str = Field(
        ..., description="Type/category of error (e.g., 'ImportError', 'ValidationError')"
    )
    error_message: str = Field(..., description="Full error message")
    severity: ErrorSeverity = Field(ErrorSeverity.MEDIUM, description="Severity of the error")
    context: Dict[str, Any] = Field(
        ..., description="Context where error occurred (file, line, operation)"
    )
    stack_trace: Optional[str] = Field(None, description="Stack trace if available")
    attempted_fix: Optional[str] = Field(None, description="Description of fix attempt")
    fix_successful: Optional[bool] = Field(None, description="Whether the fix resolved the error")
    recovery_time_ms: Optional[int] = Field(
        None, description="Time to recover from error (if successful)"
    )


# ============================================================================
# Event Type 6: Context Snapshot
# ============================================================================


class ContextSnapshotEvent(BaseEvent):
    """
    Tracks token usage and context state at checkpoints.

    Records token consumption, files in context, and memory usage
    for optimization and tracking toward token limits.
    """

    event_type: Literal["context_snapshot"] = "context_snapshot"
    tokens_before: int = Field(..., description="Token count before this operation")
    tokens_after: int = Field(..., description="Token count after this operation")
    tokens_consumed: int = Field(..., description="Tokens consumed by this operation")
    tokens_remaining: int = Field(..., description="Tokens remaining in budget")
    tokens_total_budget: int = Field(200000, description="Total token budget for session (from config)")
    files_in_context: List[str] = Field(..., description="List of files currently in context")
    files_in_context_count: int = Field(..., description="Number of files in context")
    memory_mb: Optional[float] = Field(None, description="Memory usage in MB")
    agent: Optional[str] = Field(None, description="Agent associated with this snapshot")


# ============================================================================
# Event Type 7: Validation
# ============================================================================


class ValidationStatus(str, Enum):
    """Result of validation check."""

    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIPPED = "skipped"


class ValidationEvent(BaseEvent):
    """
    Tracks validation checks performed by agents.

    Records task validation, test results, performance checks,
    and acceptance criteria verification.
    """

    event_type: Literal["validation"] = "validation"
    agent: str = Field(..., description="Agent performing validation")
    task: str = Field(..., description="Task being validated (e.g., 'Task 1.1', 'Unit tests')")
    validation_type: str = Field(
        ..., description="Type of validation (e.g., 'unit_test', 'performance', 'acceptance')"
    )
    checks: Dict[str, ValidationStatus] = Field(
        ..., description="Individual checks and their results"
    )
    result: ValidationStatus = Field(..., description="Overall validation result")
    failures: Optional[List[str]] = Field(None, description="List of failed checks")
    warnings: Optional[List[str]] = Field(None, description="List of warning messages")
    metrics: Optional[Dict[str, Any]] = Field(
        None, description="Performance metrics (e.g., test_coverage: 85%)"
    )


# ============================================================================
# Event Type Registry
# ============================================================================

# Map of event types to their corresponding Pydantic models
EVENT_TYPE_REGISTRY: Dict[str, type[BaseEvent]] = {
    "agent_invocation": AgentInvocationEvent,
    "tool_usage": ToolUsageEvent,
    "file_operation": FileOperationEvent,
    "decision": DecisionEvent,
    "error": ErrorEvent,
    "context_snapshot": ContextSnapshotEvent,
    "validation": ValidationEvent,
}


def validate_event(event_data: Dict[str, Any]) -> BaseEvent:
    """
    Validate and parse event data into the appropriate event model.

    Args:
        event_data: Dictionary containing event data with 'event_type' field

    Returns:
        Validated event model instance

    Raises:
        ValueError: If event_type is unknown or validation fails

    Example:
        >>> event_data = {
        ...     "event_type": "agent_invocation",
        ...     "timestamp": "2025-11-02T15:30:00Z",
        ...     "session_id": "session_20251102_153000",
        ...     "event_id": "evt_001",
        ...     "agent": "orchestrator",
        ...     "invoked_by": "user",
        ...     "reason": "Start Phase 1"
        ... }
        >>> event = validate_event(event_data)
        >>> assert isinstance(event, AgentInvocationEvent)
    """
    event_type = event_data.get("event_type")

    if not event_type:
        raise ValueError("Event data must contain 'event_type' field")

    event_class = EVENT_TYPE_REGISTRY.get(event_type)
    if not event_class:
        raise ValueError(f"Unknown event type: {event_type}")

    return event_class(**event_data)


def serialize_event(event: BaseEvent) -> Dict[str, Any]:
    """
    Serialize event model to dictionary (JSON-compatible).

    Args:
        event: Event model instance

    Returns:
        Dictionary representation of event

    Example:
        >>> event = AgentInvocationEvent(...)
        >>> data = serialize_event(event)
        >>> assert isinstance(data, dict)
    """
    return event.model_dump(mode="json", exclude_none=True)


__all__ = [
    "BaseEvent",
    "AgentInvocationEvent",
    "AgentStatus",
    "ToolUsageEvent",
    "FileOperationEvent",
    "FileOperationType",
    "DecisionEvent",
    "ErrorEvent",
    "ErrorSeverity",
    "ContextSnapshotEvent",
    "ValidationEvent",
    "ValidationStatus",
    "EVENT_TYPE_REGISTRY",
    "validate_event",
    "serialize_event",
]
