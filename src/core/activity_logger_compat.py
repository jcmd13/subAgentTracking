"""
Activity Logger - Backward Compatible Event Bus Integration

This module provides backward-compatible wrapper functions that maintain the
original activity_logger.py API while publishing events to the event bus.

Links Back To: Main Plan → Phase 1 → Task 1.3

Migration Strategy:
- Keep all original function signatures unchanged
- Internally publish events to event bus
- ActivityLoggerSubscriber catches events and writes to JSONL
- Performance: <1ms overhead maintained
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from contextlib import contextmanager
import asyncio
import time
import threading

from src.core.event_bus import Event, get_event_bus
from src.core.event_types import (
    AGENT_INVOKED, AGENT_COMPLETED, AGENT_FAILED,
    TOOL_USED, TOOL_ERROR,
    SNAPSHOT_CREATED, SNAPSHOT_RESTORED,
    SESSION_STARTED, SESSION_ENDED,
    COST_TRACKED,
    TASK_STARTED, TASK_STAGE_CHANGED, TASK_COMPLETED,
    TEST_RUN_STARTED, TEST_RUN_COMPLETED,
    SESSION_SUMMARY,
    REFERENCE_CHECK_TRIGGERED, REFERENCE_CHECK_COMPLETED
)

# ============================================================================
# Session and Event ID Management (Backward Compatible)
# ============================================================================

_session_id: Optional[str] = None
_event_counter = 0
_counter_lock = threading.Lock()
_trace_id_counter = 0
_trace_lock = threading.Lock()


def generate_session_id() -> str:
    """
    Generate session ID using timestamp format.

    Returns:
        Session ID (e.g., "session_20251115_153000")
    """
    return datetime.now().strftime("session_%Y%m%d_%H%M%S")


def get_iso_timestamp() -> str:
    """
    Get current timestamp in ISO format with timezone.

    Returns:
        ISO timestamp (e.g., "2025-11-15T15:30:45.123Z")
    """
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def generate_trace_id() -> str:
    """
    Generate unique trace ID for event correlation.

    Returns:
        Trace ID (e.g., "trace-00001")
    """
    global _trace_id_counter
    with _trace_lock:
        _trace_id_counter += 1
        return f"trace-{_trace_id_counter:05d}"


def next_event_id() -> str:
    """
    Generate next sequential event ID.

    Returns:
        Event ID (e.g., "evt_001")
    """
    global _event_counter
    with _counter_lock:
        _event_counter += 1
        return f"evt_{_event_counter:03d}"


def _ensure_session_id(session_id: Optional[str] = None) -> str:
    """Ensure a session ID exists and return it."""
    global _session_id
    if session_id:
        _session_id = session_id
    if _session_id is None:
        _session_id = generate_session_id()
    return _session_id


def _publish_event(event_type: str, payload: Dict[str, Any], session_id: Optional[str] = None) -> str:
    """Publish an event to the event bus with consistent metadata."""
    event_bus = get_event_bus()
    sid = _ensure_session_id(session_id)
    event_id = payload.get("event_id") or next_event_id()

    event_payload = {**payload, "event_id": event_id}
    event = Event(
        event_type=event_type,
        timestamp=datetime.now(timezone.utc),
        payload=event_payload,
        trace_id=generate_trace_id(),
        session_id=sid
    )

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(event_bus.publish_async(event))
    else:
        event_bus.publish(event)
    return event_id


# ============================================================================
# Initialization (Backward Compatible)
# ============================================================================

_initialized = False
_init_lock = threading.Lock()


def initialize(session_id: Optional[str] = None):
    """
    Initialize the activity logger.

    Creates session ID and prepares for logging.
    Now publishes SESSION_STARTED event to event bus.

    Args:
        session_id: Optional custom session ID (default: auto-generated)
    """
    global _session_id, _initialized

    with _init_lock:
        if _initialized:
            return

        # Generate or use provided session ID
        _session_id = session_id or generate_session_id()

        _publish_event(
            SESSION_STARTED,
            {"session_id": _session_id},
            session_id=_session_id
        )
        from src.core.session_summary import publish_session_summary
        publish_session_summary(
            summary_type="start",
            session_id=_session_id,
        )

        _initialized = True


def shutdown(session_id: Optional[str] = None):
    """
    Shutdown the activity logger.

    Publishes SESSION_ENDED event with session statistics.
    """
    global _initialized

    if not _initialized and session_id is None:
        return
    sid = _ensure_session_id(session_id)

    # Publish SESSION_ENDED event
    _publish_event(
        SESSION_ENDED,
        {
            "session_id": sid,
            "duration_minutes": 0.0,  # TODO: Track actual duration
            "total_tokens": 0,  # TODO: Track actual tokens
            "events_logged": _event_counter
        },
        session_id=sid
    )

    from src.core.session_summary import publish_session_summary
    publish_session_summary(
        summary_type="end",
        session_id=sid,
        summary_data_extra={
            "session_id": sid,
            "events_logged": _event_counter,
            "ended_at": get_iso_timestamp(),
        },
    )

    _initialized = False


def get_current_session_id() -> Optional[str]:
    """
    Get the current session ID.

    Returns:
        Current session ID or None if not initialized
    """
    return _session_id


def get_event_count() -> int:
    """
    Get the number of events logged in current session.

    Returns:
        Event count
    """
    return _event_counter


# ============================================================================
# Public Logging API (Backward Compatible - Now Event-Driven)
# ============================================================================

def log_agent_invocation(
    agent: str,
    invoked_by: str,
    reason: str,
    status: str = "started",
    context: Optional[Dict[str, Any]] = None,
    result: Optional[Dict[str, Any]] = None,
    duration_ms: Optional[int] = None,
    tokens_consumed: Optional[int] = None,
    **kwargs,
) -> str:
    """
    Log an agent invocation event.

    NOW PUBLISHES TO EVENT BUS (event type: AGENT_INVOKED or AGENT_COMPLETED)

    Args:
        agent: Name of agent being invoked
        invoked_by: Who invoked this agent
        reason: Reason for invocation
        status: Agent status ("started", "completed", "failed")
        context: Optional context dict
        result: Optional results from agent execution
        duration_ms: Optional duration in milliseconds
        tokens_consumed: Optional tokens consumed
        **kwargs: Additional fields

    Returns:
        Event ID
    """
    # Auto-initialize if needed
    if not _initialized:
        initialize()

    event_id = next_event_id()
    event_bus = get_event_bus()

    # Choose event type based on status
    if status == "completed":
        event_type = AGENT_COMPLETED
        payload = {
            "agent": agent,
            "duration_ms": duration_ms or 0,
            "tokens_used": tokens_consumed or 0,
            "exit_code": 0,
            "invoked_by": invoked_by,
            "reason": reason,
            "event_id": event_id
        }
        if result:
            payload["result_summary"] = str(result)

    elif status == "failed":
        event_type = AGENT_FAILED
        payload = {
            "agent": agent,
            "error_type": kwargs.get("error_type", "UnknownError"),
            "error_msg": kwargs.get("error_message", "Agent failed"),
            "invoked_by": invoked_by,
            "reason": reason,
            "event_id": event_id
        }

    else:  # "started" or other
        event_type = AGENT_INVOKED
        payload = {
            "agent": agent,
            "invoked_by": invoked_by,
            "reason": reason,
            "event_id": event_id
        }
        if context and "tokens_before" in context:
            payload["context_tokens"] = context.get("tokens_before", 0)

    # Add any extra kwargs
    payload.update(kwargs)

    # Publish event
    event = Event(
        event_type=event_type,
        timestamp=datetime.now(timezone.utc),
        payload=payload,
        trace_id=generate_trace_id(),
        session_id=_session_id
    )
    event_bus.publish(event)

    return event_id


def log_tool_usage(
    agent: str,
    tool: str,
    operation: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    duration_ms: Optional[int] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    result_summary: Optional[str] = None,
    **kwargs,
) -> str:
    """
    Log a tool usage event.

    NOW PUBLISHES TO EVENT BUS (event type: TOOL_USED or TOOL_ERROR)

    Args:
        agent: Name of agent using tool
        tool: Tool name
        operation: Optional specific operation
        parameters: Optional tool parameters
        duration_ms: Optional execution duration
        success: Whether tool execution succeeded
        error_message: Optional error message
        result_summary: Optional results summary
        **kwargs: Additional fields

    Returns:
        Event ID
    """
    # Auto-initialize if needed
    if not _initialized:
        initialize()

    event_id = next_event_id()
    event_bus = get_event_bus()

    # Choose event type based on success
    if success:
        event_type = TOOL_USED
        payload = {
            "agent": agent,
            "tool": tool,
            "success": True,
            "event_id": event_id
        }
        if duration_ms is not None:
            payload["duration_ms"] = duration_ms
        if operation:
            payload["operation"] = operation
        if result_summary:
            payload["result_summary"] = result_summary

    else:
        event_type = TOOL_ERROR
        payload = {
            "agent": agent,
            "tool": tool,
            "error_type": kwargs.get("error_type", "ToolError"),
            "event_id": event_id
        }
        if error_message:
            payload["error_msg"] = error_message
        if operation:
            payload["operation"] = operation

    # Add any extra kwargs
    payload.update(kwargs)

    # Publish event
    event = Event(
        event_type=event_type,
        timestamp=datetime.now(timezone.utc),
        payload=payload,
        trace_id=generate_trace_id(),
        session_id=_session_id
    )
    event_bus.publish(event)

    return event_id


def log_decision(
    agent: str,
    question: str,
    options: List[str],
    selected: str,
    rationale: str,
    confidence: Optional[float] = None,
    alternative_considered: Optional[str] = None,
    **kwargs,
) -> str:
    """
    Log a decision event.

    NOW PUBLISHES TO EVENT BUS (stored as generic event for now)

    Args:
        agent: Name of agent making decision
        question: Question being decided
        options: List of available options
        selected: Selected option
        rationale: Rationale for selection
        confidence: Optional confidence (0.0-1.0)
        alternative_considered: Optional main alternative
        **kwargs: Additional fields

    Returns:
        Event ID
    """
    # Auto-initialize if needed
    if not _initialized:
        initialize()

    event_id = next_event_id()
    event_bus = get_event_bus()

    # Use AGENT_INVOKED as generic wrapper for now
    # (decision events can be added to event_types.py later)
    payload = {
        "agent": agent,
        "invoked_by": "decision_maker",
        "reason": f"Decision: {question}",
        "event_id": event_id,
        "decision_question": question,
        "decision_options": options,
        "decision_selected": selected,
        "decision_rationale": rationale
    }

    if confidence is not None:
        payload["decision_confidence"] = confidence
    if alternative_considered:
        payload["decision_alternative"] = alternative_considered

    payload.update(kwargs)

    event = Event(
        event_type=AGENT_INVOKED,
        timestamp=datetime.now(timezone.utc),
        payload=payload,
        trace_id=generate_trace_id(),
        session_id=_session_id
    )
    event_bus.publish(event)

    return event_id


def log_error(
    agent: str,
    error_type: str,
    error_message: str,
    context: Dict[str, Any],
    severity: str = "medium",
    stack_trace: Optional[str] = None,
    attempted_fix: Optional[str] = None,
    fix_successful: Optional[bool] = None,
    recovery_time_ms: Optional[int] = None,
    **kwargs,
) -> str:
    """
    Log an error event.

    NOW PUBLISHES TO EVENT BUS (event type: AGENT_FAILED with error details)

    Args:
        agent: Name of agent encountering error
        error_type: Type of error
        error_message: Full error message
        context: Context where error occurred
        severity: Error severity
        stack_trace: Optional stack trace
        attempted_fix: Optional fix description
        fix_successful: Optional fix success status
        recovery_time_ms: Optional recovery time
        **kwargs: Additional fields

    Returns:
        Event ID
    """
    # Auto-initialize if needed
    if not _initialized:
        initialize()

    event_id = next_event_id()
    event_bus = get_event_bus()

    payload = {
        "agent": agent,
        "error_type": error_type,
        "error_msg": error_message,
        "event_id": event_id,
        "severity": severity,
        "context": context
    }

    if stack_trace:
        payload["stack_trace"] = stack_trace
    if attempted_fix:
        payload["attempted_fix"] = attempted_fix
    if fix_successful is not None:
        payload["fix_successful"] = fix_successful
    if recovery_time_ms is not None:
        payload["recovery_time_ms"] = recovery_time_ms

    payload.update(kwargs)

    event = Event(
        event_type=AGENT_FAILED,
        timestamp=datetime.now(timezone.utc),
        payload=payload,
        trace_id=generate_trace_id(),
        session_id=_session_id
    )
    event_bus.publish(event)

    return event_id


def log_validation(
    agent: str,
    task: str,
    validation_type: str,
    checks: Dict[str, str],
    result: str,
    failures: Optional[List[str]] = None,
    warnings: Optional[List[str]] = None,
    metrics: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> str:
    """
    Log a validation event.

    NOW PUBLISHES TO EVENT BUS (stored as generic event for now)

    Args:
        agent: Name of agent performing validation
        task: Task being validated
        validation_type: Type of validation
        checks: Individual checks and results
        result: Overall validation result
        failures: Optional list of failures
        warnings: Optional list of warnings
        metrics: Optional performance metrics
        **kwargs: Additional fields

    Returns:
        Event ID
    """
    # Auto-initialize if needed
    if not _initialized:
        initialize()

    event_id = next_event_id()
    event_bus = get_event_bus()

    payload = {
        "agent": agent,
        "invoked_by": "validator",
        "reason": f"Validation: {task}",
        "event_id": event_id,
        "validation_task": task,
        "validation_type": validation_type,
        "validation_checks": checks,
        "validation_result": result
    }

    if failures:
        payload["validation_failures"] = failures
    if warnings:
        payload["validation_warnings"] = warnings
    if metrics:
        payload["validation_metrics"] = metrics

    payload.update(kwargs)

    event = Event(
        event_type=AGENT_COMPLETED if result == "pass" else AGENT_FAILED,
        timestamp=datetime.now(timezone.utc),
        payload=payload,
        trace_id=generate_trace_id(),
        session_id=_session_id
    )
    event_bus.publish(event)

    return event_id


# Stub implementations for other log functions (minimal for backward compat)

def log_file_operation(agent: str, operation: str, file_path: str, **kwargs) -> str:
    """Log file operation (stub for backward compatibility)"""
    return log_tool_usage(agent=agent, tool="FileOp", operation=operation, parameters={"file_path": file_path}, **kwargs)


def log_context_snapshot(tokens_before: int, tokens_after: int, tokens_consumed: int,
                         tokens_remaining: int, files_in_context: List[str], **kwargs) -> str:
    """Log context snapshot (stub for backward compatibility)"""
    return log_tool_usage(
        agent=kwargs.get("agent", "system"),
        tool="ContextSnapshot",
        parameters={
            "tokens_before": tokens_before,
            "tokens_after": tokens_after,
            "tokens_consumed": tokens_consumed,
            "tokens_remaining": tokens_remaining,
            "files_count": len(files_in_context)
        }
    )


# ============================================================================
# Task and Test Events (Quick Wins)
# ============================================================================

def log_task_started(
    task_id: str,
    task_name: str,
    stage: str,
    summary: Optional[str] = None,
    eta_minutes: Optional[float] = None,
    owner: Optional[str] = None,
    session_id: Optional[str] = None,
    **kwargs,
) -> str:
    """Log task started event."""
    payload = {
        "task_id": task_id,
        "task_name": task_name,
        "stage": stage,
        "summary": summary,
        "eta_minutes": eta_minutes,
        "owner": owner,
    }
    payload.update(kwargs)
    return _publish_event(TASK_STARTED, payload, session_id=session_id)


def log_task_stage_changed(
    task_id: str,
    stage: str,
    task_name: Optional[str] = None,
    previous_stage: Optional[str] = None,
    summary: Optional[str] = None,
    progress_pct: Optional[float] = None,
    session_id: Optional[str] = None,
    **kwargs,
) -> str:
    """Log task stage change event."""
    payload = {
        "task_id": task_id,
        "task_name": task_name,
        "stage": stage,
        "previous_stage": previous_stage,
        "summary": summary,
        "progress_pct": progress_pct,
    }
    payload.update(kwargs)
    return _publish_event(TASK_STAGE_CHANGED, payload, session_id=session_id)


def log_task_completed(
    task_id: str,
    status: str,
    task_name: Optional[str] = None,
    summary: Optional[str] = None,
    duration_ms: Optional[int] = None,
    session_id: Optional[str] = None,
    **kwargs,
) -> str:
    """Log task completion event."""
    payload = {
        "task_id": task_id,
        "task_name": task_name,
        "status": status,
        "summary": summary,
        "duration_ms": duration_ms,
    }
    payload.update(kwargs)
    return _publish_event(TASK_COMPLETED, payload, session_id=session_id)


def log_test_run_started(
    test_suite: str,
    task_id: Optional[str] = None,
    command: Optional[str] = None,
    session_id: Optional[str] = None,
    **kwargs,
) -> str:
    """Log test run started event."""
    payload = {
        "test_suite": test_suite,
        "task_id": task_id,
        "command": command,
    }
    payload.update(kwargs)
    return _publish_event(TEST_RUN_STARTED, payload, session_id=session_id)


def log_test_run_completed(
    test_suite: str,
    status: str,
    task_id: Optional[str] = None,
    duration_ms: Optional[int] = None,
    passed: Optional[int] = None,
    failed: Optional[int] = None,
    summary: Optional[str] = None,
    session_id: Optional[str] = None,
    **kwargs,
) -> str:
    """Log test run completed event."""
    payload = {
        "test_suite": test_suite,
        "task_id": task_id,
        "status": status,
        "duration_ms": duration_ms,
        "passed": passed,
        "failed": failed,
        "summary": summary,
    }
    payload.update(kwargs)
    return _publish_event(TEST_RUN_COMPLETED, payload, session_id=session_id)


def log_session_summary(
    summary_type: str,
    summary_text: str,
    summary_data: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    **kwargs,
) -> str:
    """Log session summary event."""
    payload = {
        "summary_type": summary_type,
        "summary_text": summary_text,
        "summary_data": summary_data,
    }
    payload.update(kwargs)
    return _publish_event(SESSION_SUMMARY, payload, session_id=session_id)


def log_reference_check_triggered(
    trigger: str,
    agent_count: Optional[int] = None,
    token_count: Optional[int] = None,
    session_id: Optional[str] = None,
    **kwargs,
) -> str:
    """Log reference check triggered event."""
    payload = {
        "trigger": trigger,
        "agent_count": agent_count,
        "token_count": token_count,
    }
    payload.update(kwargs)
    return _publish_event(REFERENCE_CHECK_TRIGGERED, payload, session_id=session_id)


def log_reference_check_completed(
    agent: str,
    trigger: str,
    requirement_ids: List[str],
    context: Optional[str] = None,
    session_id: Optional[str] = None,
    **kwargs,
) -> str:
    """Log reference check completed event."""
    payload = {
        "agent": agent,
        "trigger": trigger,
        "requirement_count": len(requirement_ids),
        "requirement_ids": requirement_ids,
    }
    if context:
        payload["context"] = context
    payload.update(kwargs)
    return _publish_event(REFERENCE_CHECK_COMPLETED, payload, session_id=session_id)


# ============================================================================
# Context Manager Support (Backward Compatible)
# ============================================================================

@contextmanager
def tool_usage_context(agent: str, tool: str, operation: Optional[str] = None,
                      parameters: Optional[Dict[str, Any]] = None, **kwargs):
    """
    Context manager for tool usage logging with automatic duration tracking.

    NOW EVENT-DRIVEN: Publishes TOOL_USED event to event bus.

    Args:
        agent: Name of agent using tool
        tool: Tool name
        operation: Optional specific operation
        parameters: Optional tool parameters
        **kwargs: Additional fields

    Yields:
        Event ID
    """
    start_time = time.time()
    event_id = None
    success = True
    error_msg = None

    try:
        yield event_id
    except Exception as e:
        success = False
        error_msg = str(e)
        raise
    finally:
        duration_ms = int((time.time() - start_time) * 1000)

        event_id = log_tool_usage(
            agent=agent,
            tool=tool,
            operation=operation,
            parameters=parameters,
            duration_ms=duration_ms,
            success=success,
            error_message=error_msg,
            **kwargs
        )


@contextmanager
def agent_invocation_context(agent: str, invoked_by: str, reason: str,
                            context: Optional[Dict[str, Any]] = None, **kwargs):
    """
    Context manager for agent invocation logging.

    NOW EVENT-DRIVEN: Publishes AGENT_INVOKED event to event bus.

    Args:
        agent: Name of agent being invoked
        invoked_by: Who invoked this agent
        reason: Reason for invocation
        context: Optional context dict
        **kwargs: Additional fields

    Yields:
        Event ID
    """
    # Log invocation
    event_id = log_agent_invocation(
        agent=agent,
        invoked_by=invoked_by,
        reason=reason,
        context=context,
        **kwargs
    )

    try:
        yield event_id
    finally:
        pass  # Completion logged separately if needed
