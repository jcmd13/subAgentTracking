"""
Activity Logger - Core Event Logging System for SubAgent Tracking

Provides comprehensive event logging for all agent activities including:
- Agent invocations
- Tool usage
- File operations
- Decisions
- Errors
- Context snapshots
- Validation checks

Events are logged asynchronously to JSONL format with optional gzip compression.
Performance target: <1ms overhead per event.

Usage:
    from src.core.activity_logger import log_agent_invocation, initialize, shutdown

    # Initialize logger (call once at startup)
    initialize()

    # Log events
    event_id = log_agent_invocation(
        agent="orchestrator",
        invoked_by="user",
        reason="Start Phase 1"
    )

    # Shutdown logger (call at program exit)
    shutdown()
"""

import json
import gzip
import threading
import queue
import contextvars
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from contextlib import contextmanager
import time
import atexit

from src.core.config import get_config
from src.core.schemas import (
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
    BaseEvent,
    serialize_event,
    validate_event,
)


# ============================================================================
# Session and Event ID Management
# ============================================================================


class EventCounter:
    """Thread-safe sequential event ID generator."""

    def __init__(self):
        self._lock = threading.Lock()
        self._counter = 0

    def next_id(self) -> str:
        """
        Generate next sequential event ID.

        Returns:
            Event ID in format "evt_001", "evt_002", etc.
        """
        with self._lock:
            self._counter += 1
            return f"evt_{self._counter:03d}"

    def get_count(self) -> int:
        """Get current event count."""
        with self._lock:
            return self._counter

    def reset(self):
        """Reset counter (for new session)."""
        with self._lock:
            self._counter = 0


def generate_session_id() -> str:
    """
    Generate session ID using configured format.

    Returns:
        Session ID (e.g., "session_20251102_153000")
    """
    config = get_config()
    return datetime.now().strftime(config.session_id_format)


def get_iso_timestamp() -> str:
    """
    Get current timestamp in ISO format with timezone.

    Returns:
        ISO timestamp (e.g., "2025-11-02T15:30:45.123Z")
    """
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


# ============================================================================
# Schema Validation (using Pydantic from Task 1.1)
# ============================================================================
# Validation is now handled by Pydantic schemas in src.core.schemas
# Use validate_event() and serialize_event() from schemas module


# ============================================================================
# Thread-based JSONL Writer
# ============================================================================


class ThreadedJSONLWriter:
    """
    Thread-based JSONL file writer with queue buffering.

    Writes events to JSONL file (one JSON object per line) with optional
    gzip compression. Uses threading.Queue for non-blocking writes.
    """

    def __init__(self, file_path: Path, use_compression: bool = False):
        """
        Initialize threaded writer.

        Args:
            file_path: Path to JSONL file
            use_compression: Enable gzip compression
        """
        self.file_path = file_path
        self.use_compression = use_compression
        self.event_queue: queue.Queue = queue.Queue()
        self.writer_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

    def start(self):
        """Start the writer background thread."""
        with self._lock:
            if self._running:
                return

            self._running = True
            self.writer_thread = threading.Thread(
                target=self._writer_loop, daemon=True, name="ActivityLoggerWriter"
            )
            self.writer_thread.start()

    def write_event(self, event: dict):
        """
        Queue event for writing (non-blocking).

        Args:
            event: Event dictionary to write
        """
        if not self._running:
            self.start()

        # Put event in queue (non-blocking for small queue)
        self.event_queue.put(event)

    def _writer_loop(self):
        """Background thread that writes queued events to file."""
        # Ensure parent directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        # Open file with appropriate compression
        if self.use_compression:
            file_handle = gzip.open(self.file_path, "at", encoding="utf-8")
        else:
            file_handle = open(self.file_path, "a", encoding="utf-8")

        try:
            while self._running:
                try:
                    # Wait for event with timeout to check _running flag
                    event = self.event_queue.get(timeout=0.1)

                    if event is None:  # Shutdown signal
                        break

                    # Write event as single line JSON
                    json_line = json.dumps(event, ensure_ascii=False)
                    file_handle.write(json_line + "\n")
                    file_handle.flush()

                except queue.Empty:
                    # No event available, continue loop
                    continue
                except Exception as e:
                    # Log error but keep running
                    import sys

                    print(f"Error writing event: {e}", file=sys.stderr)
        finally:
            # Flush any remaining events
            while not self.event_queue.empty():
                try:
                    event = self.event_queue.get_nowait()
                    if event is not None:
                        json_line = json.dumps(event, ensure_ascii=False)
                        file_handle.write(json_line + "\n")
                except queue.Empty:
                    break
                except Exception:
                    break

            file_handle.close()

    def shutdown(self):
        """Shutdown writer, flush queue, and close file."""
        with self._lock:
            if not self._running:
                return

            self._running = False

        # Send shutdown signal
        self.event_queue.put(None)

        # Wait for writer thread to complete
        if self.writer_thread and self.writer_thread.is_alive():
            self.writer_thread.join(timeout=5.0)
            if self.writer_thread.is_alive():
                import sys

                print("Warning: Writer thread shutdown timeout", file=sys.stderr)


# ============================================================================
# Global State
# ============================================================================

_writer: Optional[ThreadedJSONLWriter] = None
_session_id: Optional[str] = None
_event_counter: Optional[EventCounter] = None
# Thread-safe parent event tracking using ContextVars
_parent_event_var: contextvars.ContextVar[List[str]] = contextvars.ContextVar(
    'parent_event_stack'
)
_initialized = False
_init_lock = threading.Lock()


def _get_parent_stack() -> List[str]:
    """Get the parent event stack for the current context (thread-safe)."""
    try:
        stack = _parent_event_var.get()
    except LookupError:
        # First access in this context, create a new stack
        stack = []
        _parent_event_var.set(stack)
    return stack


# ============================================================================
# Log Rotation and Cleanup
# ============================================================================


def list_log_files() -> List[Dict[str, Any]]:
    """
    List all log files in the logs directory.

    Returns:
        List of dicts containing file metadata:
        - file_path: Path to log file
        - session_id: Session ID extracted from filename
        - file_size_bytes: File size in bytes
        - creation_time: File creation timestamp
        - is_compressed: Whether file is gzip compressed

    Example:
        >>> files = list_log_files()
        >>> for f in files:
        ...     print(f"{f['session_id']}: {f['file_size_bytes']} bytes")
    """
    config = get_config()
    log_files = []

    if not config.logs_dir.exists():
        return log_files

    # Find all .jsonl and .jsonl.gz files
    for file_path in config.logs_dir.iterdir():
        if not file_path.is_file():
            continue

        # Check if it's a log file
        is_compressed = file_path.suffix == ".gz"
        if is_compressed:
            # .jsonl.gz file
            if not file_path.stem.endswith(".jsonl"):
                continue
            session_id = file_path.stem.replace(".jsonl", "")
        elif file_path.suffix == ".jsonl":
            # .jsonl file
            session_id = file_path.stem
        else:
            # Not a log file
            continue

        # Validate session ID format (should start with "session_" and follow pattern)
        # Expected format: session_YYYYMMDD_HHMMSS
        if not session_id.startswith("session_"):
            continue

        # Check that the part after "session_" looks like a date/time
        # (at minimum, should be session_ followed by digits and underscores)
        session_suffix = session_id.replace("session_", "", 1)
        if not session_suffix:  # Empty after removing prefix
            continue

        # Basic validation: should contain at least one digit
        # This filters out "session_invalid" but allows "session_20251103_120000"
        if not any(c.isdigit() for c in session_suffix):
            continue

        # Get file stats
        stat = file_path.stat()

        log_files.append(
            {
                "file_path": file_path,
                "session_id": session_id,
                "file_size_bytes": stat.st_size,
                "creation_time": stat.st_ctime,
                "is_compressed": is_compressed,
            }
        )

    # Sort by creation time (newest first)
    log_files.sort(key=lambda f: f["creation_time"], reverse=True)

    return log_files


def get_log_file_stats() -> Dict[str, Any]:
    """
    Get statistics about log files.

    Returns:
        Dict containing:
        - total_files: Total number of log files
        - total_size_bytes: Total size of all log files
        - oldest_session: Oldest session ID (or None)
        - newest_session: Newest session ID (or None)
        - current_session: Current active session ID (or None)

    Example:
        >>> stats = get_log_file_stats()
        >>> print(f"Total: {stats['total_files']} files, {stats['total_size_bytes']} bytes")
    """
    log_files = list_log_files()

    if not log_files:
        return {
            "total_files": 0,
            "total_size_bytes": 0,
            "oldest_session": None,
            "newest_session": None,
            "current_session": get_current_session_id(),
        }

    total_size = sum(f["file_size_bytes"] for f in log_files)

    return {
        "total_files": len(log_files),
        "total_size_bytes": total_size,
        "oldest_session": log_files[-1]["session_id"],  # Last in sorted list
        "newest_session": log_files[0]["session_id"],  # First in sorted list
        "current_session": get_current_session_id(),
    }


def rotate_logs(retention_count: Optional[int] = None) -> Dict[str, Any]:
    """
    Rotate log files, keeping only the most recent sessions.

    Deletes old log files based on retention policy, keeping the current
    active session plus N-1 previous sessions.

    Args:
        retention_count: Number of sessions to keep (default: from config)
                        Includes current session + previous sessions

    Returns:
        Dict containing:
        - files_deleted: Number of files deleted
        - files_kept: Number of files kept
        - bytes_freed: Bytes freed by deletion
        - sessions_deleted: List of deleted session IDs
        - errors: List of error messages (if any)

    Example:
        >>> result = rotate_logs(retention_count=3)
        >>> print(f"Deleted {result['files_deleted']} files, freed {result['bytes_freed']} bytes")
    """
    config = get_config()

    # Get retention count from config if not provided
    if retention_count is None:
        retention_count = config.activity_log_retention_count

    # Get all log files
    log_files = list_log_files()

    if not log_files:
        return {
            "files_deleted": 0,
            "files_kept": 0,
            "bytes_freed": 0,
            "sessions_deleted": [],
            "errors": [],
        }

    # Get current session (never delete this)
    current_session = get_current_session_id()

    # Separate current session from other files
    files_to_evaluate = []
    current_session_files = []

    for file_info in log_files:
        if file_info["session_id"] == current_session:
            current_session_files.append(file_info)
        else:
            files_to_evaluate.append(file_info)

    # Determine how many previous sessions to keep
    # If there's a current session, keep N-1 previous (total = N including current)
    # If no current session, keep N previous (total = N)
    if current_session and len(current_session_files) > 0:
        keep_count = max(0, retention_count - 1)
    else:
        keep_count = retention_count

    files_to_keep = files_to_evaluate[:keep_count]
    files_to_delete = files_to_evaluate[keep_count:]

    # Delete old files
    deleted_count = 0
    bytes_freed = 0
    sessions_deleted = []
    errors = []

    for file_info in files_to_delete:
        try:
            file_path = file_info["file_path"]
            file_size = file_info["file_size_bytes"]
            session_id = file_info["session_id"]

            file_path.unlink()

            deleted_count += 1
            bytes_freed += file_size
            sessions_deleted.append(session_id)

        except Exception as e:
            error_msg = f"Failed to delete {file_path}: {str(e)}"
            errors.append(error_msg)
            import sys

            print(f"Warning: {error_msg}", file=sys.stderr)

    # Calculate files kept (current + kept previous sessions)
    files_kept = len(current_session_files) + len(files_to_keep)

    return {
        "files_deleted": deleted_count,
        "files_kept": files_kept,
        "bytes_freed": bytes_freed,
        "sessions_deleted": sessions_deleted,
        "errors": errors,
    }


# ============================================================================
# Lifecycle Functions
# ============================================================================


def initialize(session_id: Optional[str] = None):
    """
    Initialize the activity logger.

    Creates threaded writer, generates session ID, and prepares for logging.
    Safe to call multiple times (idempotent).

    Args:
        session_id: Optional custom session ID (default: auto-generated)
    """
    global _writer, _session_id, _event_counter, _initialized

    with _init_lock:
        if _initialized:
            return

        config = get_config()

        # Always create session ID and event counter (even if logging disabled)
        _session_id = session_id or generate_session_id()
        _event_counter = EventCounter()

        # Create writer only if logging enabled
        if config.activity_log_enabled:
            # Create log file path
            log_path = config.logs_dir / f"{_session_id}.jsonl"
            if config.activity_log_compression:
                log_path = log_path.with_suffix(".jsonl.gz")

            # Create threaded writer
            _writer = ThreadedJSONLWriter(log_path, use_compression=config.activity_log_compression)
            _writer.start()

            # Register shutdown handler
            atexit.register(shutdown)

            # Rotate old logs on startup (cleanup before new session)
            try:
                rotate_logs()
            except Exception as e:
                import sys

                print(f"Warning: Log rotation on startup failed: {e}", file=sys.stderr)

        _initialized = True


def shutdown():
    """
    Shutdown the activity logger.

    Flushes all queued events and closes log file.
    Triggers automatic backup if enabled.
    """
    global _writer, _initialized

    if not _initialized:
        return

    # Trigger automatic backup before shutdown (if enabled)
    try:
        from src.core.backup_integration import backup_on_shutdown

        backup_on_shutdown()
    except ImportError:
        # Backup integration not available, continue with shutdown
        pass
    except Exception:
        # Backup failed, but continue with shutdown
        pass

    if _writer:
        _writer.shutdown()
        _writer = None

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
        Event count (0 if not initialized)
    """
    return _event_counter.get_count() if _event_counter else 0


# ============================================================================
# Internal Event Writing
# ============================================================================


def _write_event(event: dict, event_type: str) -> str:
    """
    Internal function to write event to log.

    Args:
        event: Event dictionary
        event_type: Event type for validation

    Returns:
        Event ID
    """
    # Auto-initialize if needed
    if not _initialized:
        initialize()

    config = get_config()

    # Skip if logging disabled
    if not config.activity_log_enabled or not _writer:
        return event.get("event_id", "evt_000")

    # Validate schema using Pydantic if enabled
    if config.validate_event_schemas:
        try:
            # Validate and convert to Pydantic model
            validated_event = validate_event(event)
            # Serialize back to dict for JSONL writing
            event = serialize_event(validated_event)
        except Exception as e:
            error_msg = f"Pydantic validation failed: {str(e)}"
            if config.strict_mode:
                raise ValueError(error_msg)
            else:
                import sys

                print(f"Warning: {error_msg}", file=sys.stderr)

    # Write event (non-blocking queue operation)
    _writer.write_event(event)

    return event["event_id"]


# ============================================================================
# Public Logging API
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

    Records when an agent is invoked, who invoked it, and why.

    Args:
        agent: Name of agent being invoked
        invoked_by: Who invoked this agent (e.g., "user", "orchestrator")
        reason: Reason for invocation
        status: Agent status ("started", "completed", "failed")
        context: Optional context dict (tokens, files, etc.)
        result: Optional results from agent execution (if completed)
        duration_ms: Optional duration in milliseconds (if completed)
        tokens_consumed: Optional tokens consumed by agent (if completed)
        **kwargs: Additional fields to include in event

    Returns:
        Event ID

    Example:
        >>> event_id = log_agent_invocation(
        ...     agent="config-architect",
        ...     invoked_by="orchestrator",
        ...     reason="Implement structured logging",
        ...     context={"tokens_before": 5000}
        ... )
    """
    if not _event_counter or not _session_id:
        initialize()

    event_id = _event_counter.next_id()
    parent_id = _get_parent_stack()[-1] if _get_parent_stack() else None

    # Build event matching AgentInvocationEvent schema (flat structure)
    event = {
        "event_type": "agent_invocation",
        "timestamp": get_iso_timestamp(),
        "session_id": _session_id,
        "event_id": event_id,
        "parent_event_id": parent_id,
        "agent": agent,
        "invoked_by": invoked_by,
        "reason": reason,
        "status": status,
    }

    # Add optional fields
    if context:
        event["context"] = context
    if result:
        event["result"] = result
    if duration_ms is not None:
        event["duration_ms"] = duration_ms
    if tokens_consumed is not None:
        event["tokens_consumed"] = tokens_consumed

    # Add any additional fields from kwargs
    for key, value in kwargs.items():
        if key not in event:
            event[key] = value

    return _write_event(event, "agent_invocation")


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

    Records when an agent uses a tool (Read, Write, Edit, Bash, etc.).

    Args:
        agent: Name of agent using tool
        tool: Tool name (e.g., "Read", "Write", "Edit")
        operation: Optional specific operation (e.g., "create_file", "edit_file")
        parameters: Optional tool parameters
        duration_ms: Optional execution duration in milliseconds
        success: Whether tool execution succeeded
        error_message: Optional error message if failed
        result_summary: Optional brief summary of results
        **kwargs: Additional fields to include in event

    Returns:
        Event ID

    Example:
        >>> event_id = log_tool_usage(
        ...     agent="config-architect",
        ...     tool="Write",
        ...     operation="create_file",
        ...     duration_ms=45,
        ...     success=True
        ... )
    """
    if not _event_counter or not _session_id:
        initialize()

    event_id = _event_counter.next_id()
    parent_id = _get_parent_stack()[-1] if _get_parent_stack() else None

    # Build event matching ToolUsageEvent schema (flat structure)
    event = {
        "event_type": "tool_usage",
        "timestamp": get_iso_timestamp(),
        "session_id": _session_id,
        "event_id": event_id,
        "parent_event_id": parent_id,
        "agent": agent,
        "tool": tool,
        "success": success,
    }

    # Add optional fields
    if operation:
        event["operation"] = operation
    if parameters:
        event["parameters"] = parameters
    if duration_ms is not None:
        event["duration_ms"] = duration_ms
    if error_message:
        event["error_message"] = error_message
    if result_summary:
        event["result_summary"] = result_summary

    # Add any additional fields from kwargs
    for key, value in kwargs.items():
        if key not in event:
            event[key] = value

    return _write_event(event, "tool_usage")


def log_file_operation(
    agent: str,
    operation: str,
    file_path: str,
    lines_changed: Optional[int] = None,
    diff: Optional[str] = None,
    git_hash_before: Optional[str] = None,
    git_hash_after: Optional[str] = None,
    file_size_bytes: Optional[int] = None,
    language: Optional[str] = None,
    **kwargs,
) -> str:
    """
    Log a file operation event.

    Records file read/write/edit/delete operations.

    Args:
        agent: Name of agent performing operation
        operation: Operation type ("create", "modify", "delete", "rename", "read")
        file_path: Path to file being operated on
        lines_changed: Optional number of lines changed (for modify)
        diff: Optional diff of changes (for modify)
        git_hash_before: Optional git hash before change (if in git repo)
        git_hash_after: Optional git hash after change (if in git repo)
        file_size_bytes: Optional file size in bytes
        language: Optional programming language (e.g., 'python', 'javascript')
        **kwargs: Additional fields to include in event

    Returns:
        Event ID

    Example:
        >>> event_id = log_file_operation(
        ...     agent="config-architect",
        ...     operation="create",
        ...     file_path="src/core/logger.py",
        ...     file_size_bytes=3456,
        ...     language="python"
        ... )
    """
    if not _event_counter or not _session_id:
        initialize()

    event_id = _event_counter.next_id()
    parent_id = _get_parent_stack()[-1] if _get_parent_stack() else None

    # Build event matching FileOperationEvent schema (flat structure)
    event = {
        "event_type": "file_operation",
        "timestamp": get_iso_timestamp(),
        "session_id": _session_id,
        "event_id": event_id,
        "parent_event_id": parent_id,
        "agent": agent,
        "operation": operation,
        "file_path": file_path,
    }

    # Add optional fields
    if lines_changed is not None:
        event["lines_changed"] = lines_changed
    if diff:
        event["diff"] = diff
    if git_hash_before:
        event["git_hash_before"] = git_hash_before
    if git_hash_after:
        event["git_hash_after"] = git_hash_after
    if file_size_bytes is not None:
        event["file_size_bytes"] = file_size_bytes
    if language:
        event["language"] = language

    # Add any additional fields from kwargs
    for key, value in kwargs.items():
        if key not in event:
            event[key] = value

    return _write_event(event, "file_operation")


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

    Records when an agent makes a decision between multiple options.

    Args:
        agent: Name of agent making decision
        question: Question being decided
        options: List of available options to choose from
        selected: Selected option
        rationale: Rationale for selection
        confidence: Optional confidence in decision (0.0-1.0)
        alternative_considered: Optional main alternative that was considered
        **kwargs: Additional fields to include in event

    Returns:
        Event ID

    Example:
        >>> event_id = log_decision(
        ...     agent="orchestrator",
        ...     question="Which agent for logging?",
        ...     options=["config-architect", "refactor-agent"],
        ...     selected="config-architect",
        ...     rationale="Best match for infrastructure",
        ...     confidence=0.95
        ... )
    """
    if not _event_counter or not _session_id:
        initialize()

    event_id = _event_counter.next_id()
    parent_id = _get_parent_stack()[-1] if _get_parent_stack() else None

    # Build event matching DecisionEvent schema (flat structure)
    event = {
        "event_type": "decision",
        "timestamp": get_iso_timestamp(),
        "session_id": _session_id,
        "event_id": event_id,
        "parent_event_id": parent_id,
        "agent": agent,
        "question": question,
        "options": options,
        "selected": selected,
        "rationale": rationale,
    }

    # Add optional fields
    if confidence is not None:
        event["confidence"] = confidence
    if alternative_considered:
        event["alternative_considered"] = alternative_considered

    # Add any additional fields from kwargs
    for key, value in kwargs.items():
        if key not in event:
            event[key] = value

    return _write_event(event, "decision")


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

    Records errors, warnings, and recovery attempts.

    Args:
        agent: Name of agent encountering error
        error_type: Type of error (e.g., "ImportError", "ValidationError")
        error_message: Full error message
        context: Context where error occurred (file, line, operation)
        severity: Error severity ("low", "medium", "high", "critical")
        stack_trace: Optional stack trace if available
        attempted_fix: Optional description of fix attempt
        fix_successful: Optional whether fix succeeded
        recovery_time_ms: Optional time to recover from error (if successful)
        **kwargs: Additional fields to include in event

    Returns:
        Event ID

    Example:
        >>> event_id = log_error(
        ...     agent="config-architect",
        ...     error_type="PerformanceError",
        ...     error_message="Latency budget exceeded",
        ...     context={"file": "logger.py", "measured": 450, "target": 200},
        ...     severity="medium",
        ...     attempted_fix="Switched to orjson",
        ...     fix_successful=True
        ... )
    """
    if not _event_counter or not _session_id:
        initialize()

    event_id = _event_counter.next_id()
    parent_id = _get_parent_stack()[-1] if _get_parent_stack() else None

    # Build event matching ErrorEvent schema (flat structure)
    event = {
        "event_type": "error",
        "timestamp": get_iso_timestamp(),
        "session_id": _session_id,
        "event_id": event_id,
        "parent_event_id": parent_id,
        "agent": agent,
        "error_type": error_type,
        "error_message": error_message,
        "severity": severity,
        "context": context,
    }

    # Add optional fields
    if stack_trace:
        event["stack_trace"] = stack_trace
    if attempted_fix:
        event["attempted_fix"] = attempted_fix
    if fix_successful is not None:
        event["fix_successful"] = fix_successful
    if recovery_time_ms is not None:
        event["recovery_time_ms"] = recovery_time_ms

    # Add any additional fields from kwargs
    for key, value in kwargs.items():
        if key not in event:
            event[key] = value

    return _write_event(event, "error")


def log_context_snapshot(
    tokens_before: int,
    tokens_after: int,
    tokens_consumed: int,
    tokens_remaining: int,
    files_in_context: List[str],
    tokens_total_budget: Optional[int] = None,
    memory_mb: Optional[float] = None,
    agent: Optional[str] = None,
    **kwargs,
) -> str:
    """
    Log a context snapshot event.

    Records periodic snapshots of current context (tokens, files, memory usage).

    Args:
        tokens_before: Token count before this operation
        tokens_after: Token count after this operation
        tokens_consumed: Tokens consumed by this operation
        tokens_remaining: Tokens remaining in budget
        files_in_context: List of files currently in context
        tokens_total_budget: Total token budget for session (default: from config.default_token_budget)
        memory_mb: Optional memory usage in MB
        agent: Optional agent associated with this snapshot
        **kwargs: Additional fields to include in event

    Returns:
        Event ID

    Example:
        >>> event_id = log_context_snapshot(
        ...     tokens_before=40000,
        ...     tokens_after=45000,
        ...     tokens_consumed=5000,
        ...     tokens_remaining=155000,
        ...     files_in_context=["src/core/logger.py", "src/core/config.py"],
        ...     agent="orchestrator"
        ... )
    """
    if not _event_counter or not _session_id:
        initialize()

    # Get token budget from config if not provided
    if tokens_total_budget is None:
        cfg = get_config()
        tokens_total_budget = cfg.default_token_budget

    event_id = _event_counter.next_id()

    # Build event matching ContextSnapshotEvent schema (flat structure)
    event = {
        "event_type": "context_snapshot",
        "timestamp": get_iso_timestamp(),
        "session_id": _session_id,
        "event_id": event_id,
        "parent_event_id": None,  # Snapshots are top-level
        "tokens_before": tokens_before,
        "tokens_after": tokens_after,
        "tokens_consumed": tokens_consumed,
        "tokens_remaining": tokens_remaining,
        "tokens_total_budget": tokens_total_budget,
        "files_in_context": files_in_context,
        "files_in_context_count": len(files_in_context),
    }

    # Add optional fields
    if memory_mb is not None:
        event["memory_mb"] = memory_mb
    if agent:
        event["agent"] = agent

    # Add any additional fields from kwargs
    for key, value in kwargs.items():
        if key not in event:
            event[key] = value

    return _write_event(event, "context_snapshot")


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

    Records validation checks (performance, tests, quality, etc.).

    Args:
        agent: Name of agent performing validation
        task: Task being validated (e.g., "Task 1.1", "Unit tests")
        validation_type: Type of validation (e.g., "unit_test", "performance", "acceptance")
        checks: Individual checks and their results (dict mapping check name to status)
        result: Overall validation result ("pass", "fail", "warning", "skipped")
        failures: Optional list of failed checks
        warnings: Optional list of warning messages
        metrics: Optional performance metrics (e.g., test_coverage: 85%)
        **kwargs: Additional fields to include in event

    Returns:
        Event ID

    Example:
        >>> event_id = log_validation(
        ...     agent="orchestrator",
        ...     task="Task 1.1",
        ...     validation_type="unit_test",
        ...     checks={"schema_validation": "pass", "performance": "pass"},
        ...     result="pass",
        ...     metrics={"test_coverage": 100}
        ... )
    """
    if not _event_counter or not _session_id:
        initialize()

    event_id = _event_counter.next_id()
    parent_id = _get_parent_stack()[-1] if _get_parent_stack() else None

    # Build event matching ValidationEvent schema (flat structure)
    event = {
        "event_type": "validation",
        "timestamp": get_iso_timestamp(),
        "session_id": _session_id,
        "event_id": event_id,
        "parent_event_id": parent_id,
        "agent": agent,
        "task": task,
        "validation_type": validation_type,
        "checks": checks,
        "result": result,
    }

    # Add optional fields
    if failures:
        event["failures"] = failures
    if warnings:
        event["warnings"] = warnings
    if metrics:
        event["metrics"] = metrics

    # Add any additional fields from kwargs
    for key, value in kwargs.items():
        if key not in event:
            event[key] = value

    return _write_event(event, "validation")


# ============================================================================
# Context Manager Support
# ============================================================================


@contextmanager
def tool_usage_context(
    agent: str,
    tool: str,
    operation: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    **kwargs,
):
    """
    Context manager for tool usage logging with automatic duration tracking.

    Logs tool start, tracks duration, and logs completion with success/failure.
    Also manages parent event stack for nested events.

    Args:
        agent: Name of agent using tool
        tool: Tool name
        operation: Optional specific operation (e.g., "create_file", "edit_file")
        parameters: Optional tool parameters
        **kwargs: Additional fields to pass to log_tool_usage

    Yields:
        Event ID of the tool usage event

    Example:
        >>> with tool_usage_context("agent", "Read", operation="read_file") as event_id:
        ...     # Tool operation here
        ...     data = read_file("config.py")
    """
    start_time = time.time()
    event_id = None
    success = True
    error_msg = None

    try:
        # Push event onto parent stack (will be filled in after logging)
        placeholder_idx = len(_get_parent_stack())
        _get_parent_stack().append(None)

        yield event_id  # Yield before logging (event_id not yet created)

    except Exception as e:
        success = False
        error_msg = str(e)
        raise

    finally:
        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)

        # Log tool usage with duration
        event_id = log_tool_usage(
            agent=agent,
            tool=tool,
            operation=operation,
            parameters=parameters,
            duration_ms=duration_ms,
            success=success,
            error_message=error_msg,
            **kwargs,
        )

        # Update parent stack with actual event ID
        if placeholder_idx < len(_get_parent_stack()):
            _get_parent_stack()[placeholder_idx] = event_id

            # Pop from stack
            _get_parent_stack().pop()


@contextmanager
def agent_invocation_context(
    agent: str, invoked_by: str, reason: str, context: Optional[Dict[str, Any]] = None, **kwargs
):
    """
    Context manager for agent invocation logging.

    Logs agent invocation and manages parent event stack for nested events.

    Args:
        agent: Name of agent being invoked
        invoked_by: Who invoked this agent
        reason: Reason for invocation
        context: Optional context dict
        **kwargs: Additional fields to pass to log_agent_invocation

    Yields:
        Event ID of the agent invocation event

    Example:
        >>> with agent_invocation_context("orchestrator", "user", "Start Phase 1") as event_id:
        ...     # Agent work here
        ...     orchestrate_phase_1()
    """
    # Log invocation
    event_id = log_agent_invocation(
        agent=agent, invoked_by=invoked_by, reason=reason, context=context, **kwargs
    )

    # Push onto parent stack
    _get_parent_stack().append(event_id)

    try:
        yield event_id
    finally:
        # Pop from parent stack
        if _get_parent_stack() and _get_parent_stack()[-1] == event_id:
            _get_parent_stack().pop()
