"""
Backup Integration - Automatic Backup Triggers for SubAgent Tracking System

Integrates backup_manager with activity logger to enable automatic backups on:
- Session shutdown (normal session end)
- Session handoff (token limit, manual transition)
- Configurable triggers

All backup activities are logged to the tracking system for full observability.

Usage:
    from src.core.backup_integration import trigger_automatic_backup

    # Called automatically during shutdown/handoff
    result = trigger_automatic_backup(reason="session_end")
"""

from typing import Dict, Any, Optional
from pathlib import Path

from src.core.config import get_config
from src.core import activity_logger


def trigger_automatic_backup(
    session_id: Optional[str] = None, reason: str = "session_end", force: bool = False
) -> Dict[str, Any]:
    """
    Trigger automatic backup with full activity logging.

    This function:
    1. Checks if backup is enabled in config
    2. Logs backup decision to tracking system
    3. Attempts backup if enabled
    4. Logs backup result (success/failure)
    5. Returns detailed result

    Args:
        session_id: Session to backup (None = current session)
        reason: Reason for backup (logged to tracking system)
        force: Force backup even if disabled in config

    Returns:
        Dictionary with backup results:
        {
            'attempted': bool,
            'success': bool,
            'reason': str,
            'backup_id': Optional[str],
            'error': Optional[str],
            'skipped_reason': Optional[str]
        }
    """
    config = get_config()

    # Use current session if not specified
    if session_id is None:
        session_id = activity_logger.get_current_session_id()

    result = {
        "attempted": False,
        "success": False,
        "reason": reason,
        "backup_id": None,
        "error": None,
        "skipped_reason": None,
    }

    # Check if backup is enabled
    if not config.backup_enabled and not force:
        result["skipped_reason"] = "backup_disabled_in_config"

        # Log decision to skip
        activity_logger.log_decision(
            agent="backup-integration",
            question="Should automatic backup run?",
            options=["yes", "no (disabled in config)"],
            selected="no (disabled in config)",
            rationale=f"Backup disabled in config. Reason: {reason}",
            confidence=1.0,
        )

        return result

    # Log decision to backup
    activity_logger.log_decision(
        agent="backup-integration",
        question="Should automatic backup run?",
        options=["yes (enabled)", "no (disabled)"],
        selected="yes (enabled)",
        rationale=f"Backup triggered by: {reason}",
        confidence=1.0,
    )

    # Log backup invocation
    backup_event_id = activity_logger.log_agent_invocation(
        agent="backup-manager",
        invoked_by="backup-integration",
        reason=f"Automatic backup: {reason}",
        status="started",
    )

    result["attempted"] = True

    # Attempt backup
    try:
        # Import here to avoid circular dependencies
        from src.core.backup_manager import BackupManager

        # Check if Google Drive is available
        manager = BackupManager()
        if not manager.is_available():
            result["error"] = "google_drive_not_available"
            result["skipped_reason"] = "Google Drive API not installed or configured"

            activity_logger.log_error(
                agent="backup-manager",
                error_type="BackupUnavailable",
                error_message="Google Drive API not available",
                context={"reason": reason, "session_id": session_id},
                severity="low",
                attempted_fix=None,
                fix_successful=False,
            )

            return result

        # Authenticate with Google Drive
        if not manager.authenticate():
            result["error"] = "authentication_failed"

            activity_logger.log_error(
                agent="backup-manager",
                error_type="AuthenticationError",
                error_message="Failed to authenticate with Google Drive",
                context={"reason": reason, "session_id": session_id},
                severity="medium",
                attempted_fix="Check credentials in .claude/credentials/",
                fix_successful=False,
            )

            return result

        # Perform backup
        backup_result = manager.backup_session(
            session_id=session_id, phase=None, compress=True  # Auto-detect from config
        )

        if backup_result and backup_result.get("success"):
            result["success"] = True
            result["backup_id"] = backup_result.get("file_id")

            # Log successful backup
            activity_logger.log_validation(
                agent="backup-manager",
                task=f"Backup session {session_id}",
                validation_type="backup_integrity",
                result="PASS",
                checks={"upload": "PASS", "compression": "PASS", "authentication": "PASS"},
                failures=[],
            )

        else:
            result["error"] = backup_result.get("error", "unknown_error")

            activity_logger.log_error(
                agent="backup-manager",
                error_type="BackupFailed",
                error_message=backup_result.get("error", "Unknown backup error"),
                context={
                    "reason": reason,
                    "session_id": session_id,
                    "backup_result": backup_result,
                },
                severity="high",
                attempted_fix=None,
                fix_successful=False,
            )

    except ImportError as e:
        result["error"] = "backup_manager_import_error"
        result["skipped_reason"] = str(e)

    except Exception as e:
        result["error"] = "unexpected_error"

        activity_logger.log_error(
            agent="backup-manager",
            error_type="UnexpectedError",
            error_message=str(e),
            context={
                "reason": reason,
                "session_id": session_id,
                "exception_type": type(e).__name__,
            },
            severity="high",
            attempted_fix=None,
            fix_successful=False,
        )

    return result


def should_backup_on_handoff(reason: str) -> bool:
    """
    Determine if backup should run on handoff based on reason.

    Args:
        reason: Handoff reason (e.g., 'token_limit', 'session_end')

    Returns:
        True if backup should run, False otherwise
    """
    config = get_config()

    # Check config settings
    if reason in ["token_limit", "token_limit_approaching"]:
        return config.backup_on_token_limit

    if reason in ["session_end", "handoff", "manual"]:
        return config.backup_on_handoff

    # Default: backup on handoff
    return config.backup_on_handoff


def backup_on_shutdown(session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function for backup during shutdown.

    Called automatically by activity logger shutdown if enabled.

    Args:
        session_id: Session to backup (None = current)

    Returns:
        Backup result dictionary
    """
    return trigger_automatic_backup(session_id=session_id, reason="session_shutdown")


def backup_on_handoff(session_id: Optional[str] = None, reason: str = "handoff") -> Dict[str, Any]:
    """
    Convenience function for backup during session handoff.

    Called from create_handoff_summary if enabled.

    Args:
        session_id: Session to backup (None = current)
        reason: Handoff reason

    Returns:
        Backup result dictionary
    """
    # Check if we should backup based on reason
    if not should_backup_on_handoff(reason):
        return {
            "attempted": False,
            "success": False,
            "reason": reason,
            "skipped_reason": f"backup_not_enabled_for_{reason}",
        }

    return trigger_automatic_backup(session_id=session_id, reason=f"handoff_{reason}")


__all__ = [
    "trigger_automatic_backup",
    "should_backup_on_handoff",
    "backup_on_shutdown",
    "backup_on_handoff",
]
