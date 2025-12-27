"""Protocol interfaces to decouple core modules."""

from typing import Protocol, Optional, Dict, Any, List


class ActivityLogger(Protocol):
    """Minimal interface for activity logging."""

    def get_current_session_id(self) -> Optional[str]:
        ...

    def get_event_count(self) -> int:
        ...

    def log_decision(
        self,
        agent: str,
        question: str,
        options: List[str],
        selected: str,
        rationale: str,
        confidence: Optional[float] = None,
        alternative_considered: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        ...

    def log_agent_invocation(
        self,
        agent: str,
        invoked_by: str,
        reason: str,
        status: str = "started",
        context: Optional[Dict[str, Any]] = None,
        result: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        tokens_consumed: Optional[int] = None,
        **kwargs: Any,
    ) -> str:
        ...

    def log_error(
        self,
        agent: str,
        error_type: str,
        error_message: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        severity: str = "medium",
        stack_trace: Optional[str] = None,
        attempted_fix: Optional[str] = None,
        fix_successful: Optional[bool] = None,
        recovery_time_ms: Optional[int] = None,
        message: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        ...

    def log_validation(
        self,
        agent: str,
        task: str,
        validation_type: str,
        result: str,
        checks: Optional[Dict[str, Any]] = None,
        failures: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> str:
        ...

    def log_context_snapshot(
        self,
        tokens_before: Optional[int] = None,
        tokens_after: Optional[int] = None,
        tokens_consumed: Optional[int] = None,
        tokens_remaining: Optional[int] = None,
        files_in_context: Optional[List[str]] = None,
        tokens_total_budget: Optional[int] = None,
        memory_mb: Optional[float] = None,
        agent: Optional[str] = None,
        trigger: Optional[str] = None,
        snapshot: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> str:
        ...


class BackupIntegration(Protocol):
    """Interface for triggering backups from other components."""

    def backup_on_handoff(
        self, session_id: Optional[str] = None, reason: str = "handoff"
    ) -> Dict[str, Any]:
        ...
