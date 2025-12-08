"""
Custom Exception Hierarchy for SubAgent Tracking System

Provides structured exception handling with clear error categories and
better debugging information.

Usage:
    from src.core.exceptions import LogWriteError, SnapshotError

    try:
        write_to_log(data)
    except LogWriteError as e:
        logger.error(f"Failed to write log: {e}")
        # Handle gracefully or re-raise
"""

from typing import Optional, Dict, Any


# ============================================================================
# Base Exception
# ============================================================================

class SubAgentTrackingError(Exception):
    """Base exception for all SubAgent Tracking System errors.

    All custom exceptions in the system inherit from this base class,
    making it easy to catch all system-specific errors.

    Attributes:
        message: Human-readable error message
        context: Optional dictionary with additional error context
        original_error: Original exception if this wraps another error
    """

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        self.message = message
        self.context = context or {}
        self.original_error = original_error
        super().__init__(self.message)

    def __str__(self) -> str:
        """Format error with context for debugging."""
        error_str = self.message

        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            error_str = f"{error_str} ({context_str})"

        if self.original_error:
            error_str = f"{error_str} | Caused by: {str(self.original_error)}"

        return error_str


# ============================================================================
# Activity Logging Exceptions
# ============================================================================

class LogWriteError(SubAgentTrackingError):
    """Failed to write to activity log.

    Raised when the activity logger cannot write events to the log file.
    This is a critical error as it means we're losing observability.

    Example:
        >>> raise LogWriteError(
        ...     "Failed to write event",
        ...     context={"event_id": "evt_001", "session_id": "session_123"}
        ... )
    """
    pass


class LogRotationError(SubAgentTrackingError):
    """Failed to rotate or cleanup log files.

    Raised when log rotation or cleanup operations fail.
    """
    pass


# ============================================================================
# Snapshot Management Exceptions
# ============================================================================

class SnapshotError(SubAgentTrackingError):
    """Base exception for snapshot-related errors."""
    pass


class SnapshotCreationError(SnapshotError):
    """Failed to create a snapshot.

    Raised when snapshot creation fails due to I/O errors,
    serialization issues, or resource constraints.
    """
    pass


class SnapshotRestoreError(SnapshotError):
    """Failed to restore from a snapshot.

    Raised when a snapshot cannot be loaded or the data is corrupted.
    """
    pass


class SnapshotNotFoundError(SnapshotError):
    """Requested snapshot does not exist.

    Raised when trying to restore or access a non-existent snapshot.
    """
    pass


# ============================================================================
# Backup System Exceptions
# ============================================================================

class BackupError(SubAgentTrackingError):
    """Base exception for backup-related errors."""
    pass


class BackupAuthenticationError(BackupError):
    """Failed to authenticate with backup service.

    Raised when Google Drive or other backup service authentication fails.
    """
    pass


class BackupUploadError(BackupError):
    """Failed to upload backup to remote storage.

    Raised when file upload fails due to network issues, quota limits,
    or API errors.
    """
    pass


class BackupDownloadError(BackupError):
    """Failed to download backup from remote storage.

    Raised when backup retrieval fails.
    """
    pass


class BackupNotAvailableError(BackupError):
    """Backup service is not configured or available.

    Raised when trying to use backup features without proper configuration.
    """
    pass


# ============================================================================
# Validation Exceptions
# ============================================================================

class ValidationError(SubAgentTrackingError):
    """Base exception for validation errors."""
    pass


class EventValidationError(ValidationError):
    """Event payload validation failed.

    Raised when an event payload doesn't match its JSON schema or
    contains invalid data.

    Example:
        >>> raise EventValidationError(
        ...     "Invalid agent.invoked event",
        ...     context={"missing_field": "reason"}
        ... )
    """
    pass


class SchemaValidationError(ValidationError):
    """Schema validation failed.

    Raised when data doesn't conform to expected schema.
    """
    pass


# ============================================================================
# Configuration Exceptions
# ============================================================================

class ConfigurationError(SubAgentTrackingError):
    """Invalid configuration detected.

    Raised when configuration values are missing, invalid, or
    inconsistent.

    Example:
        >>> raise ConfigurationError(
        ...     "Token budget must be >= 1000",
        ...     context={"provided_value": 500}
        ... )
    """
    pass


class ConfigurationNotFoundError(ConfigurationError):
    """Required configuration is missing.

    Raised when a mandatory configuration value is not set.
    """
    pass


# ============================================================================
# Analytics Exceptions
# ============================================================================

class AnalyticsError(SubAgentTrackingError):
    """Base exception for analytics-related errors."""
    pass


class DatabaseError(AnalyticsError):
    """Database operation failed.

    Raised when SQLite operations fail (e.g., connection, query, insert).
    """
    pass


class QueryError(AnalyticsError):
    """Analytics query failed.

    Raised when a query cannot be executed or returns invalid results.
    """
    pass


# ============================================================================
# Event Bus Exceptions
# ============================================================================

class EventBusError(SubAgentTrackingError):
    """Base exception for event bus errors."""
    pass


class EventPublishError(EventBusError):
    """Failed to publish event to event bus.

    Raised when event publication fails.
    """
    pass


class EventHandlerError(EventBusError):
    """Event handler execution failed.

    Raised when a subscribed event handler throws an error.
    Contains information about which handler failed.
    """
    pass


# ============================================================================
# Session Management Exceptions
# ============================================================================

class SessionError(SubAgentTrackingError):
    """Base exception for session management errors."""
    pass


class SessionNotFoundError(SessionError):
    """Requested session does not exist.

    Raised when trying to access a non-existent session.
    """
    pass


class SessionInitializationError(SessionError):
    """Failed to initialize a new session.

    Raised when session creation fails.
    """
    pass


# ============================================================================
# Token Budget Exceptions
# ============================================================================

class TokenBudgetError(SubAgentTrackingError):
    """Base exception for token budget errors."""
    pass


class TokenLimitExceededError(TokenBudgetError):
    """Token budget limit exceeded.

    Raised when operation would exceed the configured token budget.
    """
    pass


class TokenCountError(TokenBudgetError):
    """Failed to count or track tokens.

    Raised when token counting logic fails.
    """
    pass


# ============================================================================
# Utility Functions
# ============================================================================

def wrap_exception(
    original_error: Exception,
    new_error_class: type,
    message: str,
    context: Optional[Dict[str, Any]] = None
) -> SubAgentTrackingError:
    """Wrap a generic exception in a system-specific exception.

    This helper function makes it easy to convert generic exceptions
    (like IOError, ValueError) into our custom exception hierarchy
    while preserving the original error information.

    Args:
        original_error: The original exception that was caught
        new_error_class: The custom exception class to wrap it in
        message: Custom error message
        context: Additional context information

    Returns:
        Instance of new_error_class with original error preserved

    Example:
        >>> try:
        ...     open('/nonexistent/file.json')
        ... except IOError as e:
        ...     raise wrap_exception(
        ...         e,
        ...         LogWriteError,
        ...         "Failed to open log file",
        ...         context={"path": "/nonexistent/file.json"}
        ...     )
    """
    return new_error_class(
        message=message,
        context=context,
        original_error=original_error
    )


# ============================================================================
# Exception Registry (for documentation/debugging)
# ============================================================================

ALL_EXCEPTIONS = [
    # Base
    SubAgentTrackingError,

    # Logging
    LogWriteError,
    LogRotationError,

    # Snapshots
    SnapshotError,
    SnapshotCreationError,
    SnapshotRestoreError,
    SnapshotNotFoundError,

    # Backups
    BackupError,
    BackupAuthenticationError,
    BackupUploadError,
    BackupDownloadError,
    BackupNotAvailableError,

    # Validation
    ValidationError,
    EventValidationError,
    SchemaValidationError,

    # Configuration
    ConfigurationError,
    ConfigurationNotFoundError,

    # Analytics
    AnalyticsError,
    DatabaseError,
    QueryError,

    # Event Bus
    EventBusError,
    EventPublishError,
    EventHandlerError,

    # Sessions
    SessionError,
    SessionNotFoundError,
    SessionInitializationError,

    # Token Budget
    TokenBudgetError,
    TokenLimitExceededError,
    TokenCountError,
]


__all__ = [exc.__name__ for exc in ALL_EXCEPTIONS] + ['wrap_exception']
