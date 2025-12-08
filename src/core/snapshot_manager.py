"""
Snapshot Manager for SubAgent Tracking System

Provides state checkpoint functionality for instant session recovery.

Key Functions:
- take_snapshot(): Create snapshot of current session state
- restore_snapshot(): Load and restore from a previous snapshot
- create_handoff_summary(): Generate markdown handoff summary for session transitions

Triggers:
- Manual: Explicit call to take_snapshot()
- Agent count: Every N agent invocations (default: 10)
- Token count: Every N tokens consumed (default: 20k)
- Token limit warning: When approaching token budget limit

Performance Target: <100ms snapshot creation, <50ms snapshot load

Usage:
    from src.core.snapshot_manager import take_snapshot, restore_snapshot

    # Create checkpoint before risky operation
    snapshot_id = take_snapshot(trigger="before_refactor")

    # Later, if needed
    state = restore_snapshot(snapshot_id)
"""

import json
import gzip
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple
import subprocess

from src.core import config, activity_logger


# ============================================================================
# Module State
# ============================================================================

_snapshot_counter: int = 0
_last_agent_count: int = 0
_last_token_count: int = 0


# ============================================================================
# Snapshot Trigger Detection
# ============================================================================


def should_take_snapshot(
    agent_count: Optional[int] = None,
    token_count: Optional[int] = None,
) -> Tuple[bool, str]:
    """
    Check if snapshot should be triggered based on agent or token thresholds.

    Args:
        agent_count: Current agent invocation count
        token_count: Current token consumption count

    Returns:
        Tuple of (should_trigger, reason)
    """
    global _last_agent_count, _last_token_count

    cfg = config.get_config()

    # Check agent count trigger
    if agent_count is not None:
        agent_threshold = cfg.snapshot_trigger_agent_count
        agents_since_last = agent_count - _last_agent_count

        if agents_since_last >= agent_threshold:
            return True, f"agent_count_threshold_{agent_threshold}"

    # Check token count trigger
    if token_count is not None:
        token_threshold = cfg.snapshot_trigger_token_count
        tokens_since_last = token_count - _last_token_count

        if tokens_since_last >= token_threshold:
            return True, f"token_count_threshold_{token_threshold}"

    return False, ""


# ============================================================================
# Git Integration
# ============================================================================


def get_git_state() -> Dict[str, Any]:
    """
    Get current git repository state.

    Returns:
        Dictionary with git state information, or empty dict if not a git repo
    """
    cfg = config.get_config()
    project_root = cfg.project_root

    try:
        # Check if we're in a git repository
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=project_root,
            capture_output=True,
            check=True,
            timeout=2,
        )

        # Get current branch
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=2,
        )
        current_branch = (
            branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"
        )

        # Get latest commit hash
        commit_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=2,
        )
        latest_commit = commit_result.stdout.strip() if commit_result.returncode == 0 else "unknown"

        # Check for uncommitted changes
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=2,
        )
        uncommitted_changes = (
            bool(status_result.stdout.strip()) if status_result.returncode == 0 else False
        )

        # Get modified files
        modified_files = []
        if uncommitted_changes:
            modified_files = [
                line.strip().split(maxsplit=1)[1]
                for line in status_result.stdout.strip().split("\n")
                if line.strip()
            ]

        return {
            "current_branch": current_branch,
            "latest_commit": latest_commit,
            "uncommitted_changes": uncommitted_changes,
            "modified_files": modified_files,
            "is_git_repo": True,
        }

    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        # Not a git repo or git not available
        return {
            "is_git_repo": False,
        }


# ============================================================================
# Snapshot Creation
# ============================================================================


def take_snapshot(
    trigger: str = "manual",
    agent_count: Optional[int] = None,
    token_count: Optional[int] = None,
    tokens_remaining: Optional[int] = None,
    files_in_context: Optional[List[str]] = None,
    agent_context: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> str:
    """
    Create a snapshot of current session state.

    Args:
        trigger: Reason for snapshot (manual|agent_count|token_count|token_limit_warning)
        agent_count: Current agent invocation count
        token_count: Current token consumption count
        tokens_remaining: Tokens remaining in budget
        files_in_context: List of files currently in context
        agent_context: Additional agent context (current agent, tasks, etc.)
        **kwargs: Additional metadata to include in snapshot

    Returns:
        Snapshot ID (e.g., 'snap_001')

    Example:
        >>> snapshot_id = take_snapshot(
        ...     trigger="manual",
        ...     agent_count=10,
        ...     token_count=20000,
        ...     files_in_context=["src/core/activity_logger.py"]
        ... )
        >>> print(snapshot_id)
        'snap_001'
    """
    global _snapshot_counter, _last_agent_count, _last_token_count

    start_time = time.time()

    cfg = config.get_config()
    session_id = activity_logger.get_current_session_id()

    # If session_id is None, use a default
    if session_id is None:
        session_id = "session_default"

    # Increment snapshot counter
    _snapshot_counter += 1
    snapshot_number = _snapshot_counter
    snapshot_id = f"snap_{snapshot_number:03d}"

    # Update last counts for trigger detection
    if agent_count is not None:
        _last_agent_count = agent_count
    if token_count is not None:
        _last_token_count = token_count

    # Get current timestamp
    timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    # Get total event count
    total_events = activity_logger.get_event_count()

    # Calculate session duration (estimate based on session_id if available)
    elapsed_time_seconds = 0
    try:
        # Parse session_id to get start time (format: session_YYYYMMDD_HHMMSS)
        if session_id.startswith("session_"):
            date_str = session_id.replace("session_", "")
            start_dt = datetime.strptime(date_str, "%Y%m%d_%H%M%S").replace(tzinfo=timezone.utc)
            now_dt = datetime.now(timezone.utc)
            elapsed_time_seconds = int((now_dt - start_dt).total_seconds())
    except (ValueError, AttributeError):
        pass

    # Get git state
    git_state = get_git_state()

    # Build snapshot data structure
    snapshot_data = {
        "metadata": {
            "snapshot_id": snapshot_id,
            "session_id": session_id,
            "timestamp": timestamp,
            "trigger": trigger,
            "snapshot_number": snapshot_number,
            "created_by": "snapshot_manager",
        },
        "session_state": {
            "agent_invocation_count": agent_count or 0,
            "total_events": total_events,
            "token_usage": {
                "tokens_consumed": token_count or 0,
                "tokens_remaining": tokens_remaining or 0,
                "tokens_total": 200000,  # Default budget
            },
            "elapsed_time_seconds": elapsed_time_seconds,
        },
        "agent_context": agent_context or {},
        "file_operations": {
            "files_in_context": files_in_context or [],
            "files_in_context_count": len(files_in_context or []),
        },
        "git_state": git_state,
    }

    # Add any additional kwargs to metadata
    if kwargs:
        snapshot_data["additional_metadata"] = kwargs

    # Get snapshot file path
    snapshot_path = cfg.get_snapshot_path(session_id, snapshot_number)

    # Write snapshot to file
    try:
        if cfg.snapshot_compression:
            # Write compressed JSON
            with gzip.open(str(snapshot_path) + ".gz", "wt", encoding="utf-8") as f:
                json.dump(snapshot_data, f, indent=2, ensure_ascii=False)
        else:
            # Write uncompressed JSON
            with open(snapshot_path, "w", encoding="utf-8") as f:
                json.dump(snapshot_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        import sys

        print(f"Error writing snapshot {snapshot_id}: {e}", file=sys.stderr)
        return snapshot_id  # Return ID even if write failed

    # Calculate duration
    duration_ms = int((time.time() - start_time) * 1000)

    # Log context snapshot event to activity log
    if token_count is not None and tokens_remaining is not None:
        activity_logger.log_context_snapshot(
            tokens_before=tokens_remaining + (token_count or 0),
            tokens_after=(tokens_remaining or 0),
            tokens_consumed=token_count or 0,
            tokens_remaining=tokens_remaining or 0,
            files_in_context=files_in_context or [],
            agent=agent_context.get("current_agent") if agent_context else None,
        )

    # Check performance budget
    if duration_ms > cfg.snapshot_creation_max_latency_ms:
        import sys

        print(
            f"Warning: Snapshot creation took {duration_ms}ms "
            f"(budget: {cfg.snapshot_creation_max_latency_ms}ms)",
            file=sys.stderr,
        )

    return snapshot_id


# ============================================================================
# Snapshot Restoration
# ============================================================================


def restore_snapshot(snapshot_id: str) -> Dict[str, Any]:
    """
    Restore session state from a snapshot.

    Args:
        snapshot_id: Snapshot ID to restore (e.g., 'snap_001')

    Returns:
        Snapshot data dictionary

    Raises:
        FileNotFoundError: If snapshot file doesn't exist
        json.JSONDecodeError: If snapshot file is corrupted

    Example:
        >>> state = restore_snapshot('snap_001')
        >>> print(state['metadata']['snapshot_id'])
        'snap_001'
    """
    start_time = time.time()

    cfg = config.get_config()
    session_id = activity_logger.get_current_session_id()

    # Parse snapshot number from ID
    try:
        snapshot_number = int(snapshot_id.replace("snap_", ""))
    except ValueError:
        raise ValueError(f"Invalid snapshot_id format: {snapshot_id}")

    # Get snapshot file path
    snapshot_path = cfg.get_snapshot_path(session_id, snapshot_number)

    # Try to load compressed version first
    compressed_path = Path(str(snapshot_path) + ".gz")
    if compressed_path.exists():
        with gzip.open(compressed_path, "rt", encoding="utf-8") as f:
            snapshot_data = json.load(f)
    elif snapshot_path.exists():
        with open(snapshot_path, "r", encoding="utf-8") as f:
            snapshot_data = json.load(f)
    else:
        raise FileNotFoundError(
            f"Snapshot not found: {snapshot_id} " f"(tried {snapshot_path} and {compressed_path})"
        )

    # Calculate duration
    duration_ms = int((time.time() - start_time) * 1000)

    # Check performance target (50ms for load)
    if duration_ms > 50:
        import sys

        print(f"Warning: Snapshot load took {duration_ms}ms (target: <50ms)", file=sys.stderr)

    return snapshot_data


# ============================================================================
# Snapshot Listing and Cleanup
# ============================================================================


def list_snapshots(session_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    List all snapshots for a session.

    Args:
        session_id: Session ID to list snapshots for (default: current session)

    Returns:
        List of snapshot metadata dictionaries
    """
    cfg = config.get_config()

    if session_id is None:
        session_id = activity_logger.get_current_session_id()

    # Find all snapshot files for this session
    state_dir = cfg.state_dir
    pattern = f"{session_id}_snap*.json*"

    snapshots = []
    for snapshot_file in state_dir.glob(pattern):
        try:
            # Load just the metadata
            if snapshot_file.suffix == ".gz":
                with gzip.open(snapshot_file, "rt", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                with open(snapshot_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

            snapshots.append(
                {
                    "snapshot_id": data["metadata"]["snapshot_id"],
                    "timestamp": data["metadata"]["timestamp"],
                    "trigger": data["metadata"]["trigger"],
                    "file_path": str(snapshot_file),
                    "file_size_bytes": snapshot_file.stat().st_size,
                }
            )
        except (json.JSONDecodeError, KeyError) as e:
            # Skip corrupted snapshots
            import sys

            print(f"Warning: Skipping corrupted snapshot {snapshot_file}: {e}", file=sys.stderr)
            continue

    # Sort by snapshot number
    snapshots.sort(key=lambda s: s["snapshot_id"])

    return snapshots


def cleanup_old_snapshots(retention_days: Optional[int] = None) -> int:
    """
    Clean up old snapshots based on retention policy.

    Args:
        retention_days: Number of days to retain snapshots (default: from config)

    Returns:
        Number of snapshots deleted
    """
    cfg = config.get_config()

    if retention_days is None:
        retention_days = cfg.snapshot_retention_days

    state_dir = cfg.state_dir
    now = datetime.now(timezone.utc)
    deleted_count = 0

    # Find all snapshot files
    for snapshot_file in state_dir.glob("session_*_snap*.json*"):
        try:
            # Check file age
            file_age_seconds = now.timestamp() - snapshot_file.stat().st_mtime
            file_age_days = file_age_seconds / (24 * 3600)

            if file_age_days > retention_days:
                snapshot_file.unlink()
                deleted_count += 1
        except OSError as e:
            import sys

            print(f"Warning: Failed to delete {snapshot_file}: {e}", file=sys.stderr)

    return deleted_count


# ============================================================================
# Handoff Summary Generation
# ============================================================================


def create_handoff_summary(
    session_id: Optional[str] = None,
    reason: str = "session_end",
    include_latest_snapshot: bool = True,
) -> str:
    """
    Create a markdown handoff summary for session transition.

    This generates a human-readable summary that can be used to brief
    a new session or agent about the current state.

    Args:
        session_id: Session ID to create handoff for (default: current session)
        reason: Reason for handoff (e.g., 'token_limit', 'session_end')
        include_latest_snapshot: Include latest snapshot metadata in summary

    Returns:
        Path to handoff markdown file

    Example:
        >>> handoff_path = create_handoff_summary(
        ...     reason="token_limit_approaching"
        ... )
        >>> print(f"Handoff summary: {handoff_path}")
    """
    cfg = config.get_config()

    if session_id is None:
        session_id = activity_logger.get_current_session_id()

    timestamp = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

    # Get latest snapshot
    latest_snapshot = None
    if include_latest_snapshot:
        snapshots = list_snapshots(session_id)
        if snapshots:
            latest_snapshot_id = snapshots[-1]["snapshot_id"]
            try:
                latest_snapshot = restore_snapshot(latest_snapshot_id)
            except (FileNotFoundError, json.JSONDecodeError):
                pass

    # Build handoff markdown
    lines = [
        f"# Session Handoff Summary",
        f"",
        f"**Session ID:** `{session_id}`  ",
        f"**Handoff Reason:** {reason}  ",
        f"**Timestamp:** {timestamp}  ",
        f"",
        f"## Session Overview",
        f"",
    ]

    if latest_snapshot:
        session_state = latest_snapshot.get("session_state", {})
        token_usage = session_state.get("token_usage", {})
        git_state = latest_snapshot.get("git_state", {})

        lines.extend(
            [
                f"- **Total Events:** {session_state.get('total_events', 0)}",
                f"- **Agent Invocations:** {session_state.get('agent_invocation_count', 0)}",
                f"- **Tokens Consumed:** {token_usage.get('tokens_consumed', 0):,}",
                f"- **Tokens Remaining:** {token_usage.get('tokens_remaining', 0):,}",
                f"- **Session Duration:** {session_state.get('elapsed_time_seconds', 0)} seconds",
                f"",
            ]
        )

        # Git state
        if git_state.get("is_git_repo"):
            lines.extend(
                [
                    f"## Git State",
                    f"",
                    f"- **Branch:** `{git_state.get('current_branch', 'unknown')}`",
                    f"- **Commit:** `{git_state.get('latest_commit', 'unknown')}`",
                    f"- **Uncommitted Changes:** {git_state.get('uncommitted_changes', False)}",
                    f"",
                ]
            )

            if git_state.get("modified_files"):
                lines.extend(
                    [
                        f"### Modified Files",
                        f"",
                    ]
                )
                for file in git_state["modified_files"]:
                    lines.append(f"- `{file}`")
                lines.append("")

        # Files in context
        file_ops = latest_snapshot.get("file_operations", {})
        if file_ops.get("files_in_context"):
            lines.extend(
                [
                    f"## Files in Context",
                    f"",
                ]
            )
            for file in file_ops["files_in_context"]:
                lines.append(f"- `{file}`")
            lines.append("")

        # Agent context
        agent_ctx = latest_snapshot.get("agent_context", {})
        if agent_ctx:
            lines.extend(
                [
                    f"## Agent Context",
                    f"",
                    f"```json",
                    json.dumps(agent_ctx, indent=2),
                    f"```",
                    f"",
                ]
            )
    else:
        lines.extend(
            [
                f"*No snapshot available for this session*",
                f"",
            ]
        )

    # Snapshots section
    snapshots = list_snapshots(session_id)
    if snapshots:
        lines.extend(
            [
                f"## Available Snapshots",
                f"",
            ]
        )
        for snap in snapshots:
            lines.append(
                f"- **{snap['snapshot_id']}** " f"({snap['trigger']}) - {snap['timestamp']}"
            )
        lines.append("")

    # Recovery instructions
    lines.extend(
        [
            f"## Recovery Instructions",
            f"",
            f"To resume this session in a new context:",
            f"",
            f"```python",
            f"from src.core.snapshot_manager import restore_snapshot",
            f"",
            f"# Restore latest state",
            f"state = restore_snapshot('{latest_snapshot['metadata']['snapshot_id'] if latest_snapshot else 'snap_001'}')",
            f"",
            f"# Review session state",
            f"print(state['session_state'])",
            f"```",
            f"",
            f'Or simply say: **"Resume from session `{session_id}`"**',
            f"",
        ]
    )

    # Trigger automatic backup on handoff (if enabled)
    try:
        from src.core.backup_integration import backup_on_handoff

        backup_result = backup_on_handoff(session_id=session_id, reason=reason)

        # Add backup status to handoff summary if attempted
        if backup_result.get("attempted"):
            lines.extend(
                [
                    f"",
                    f"## Backup Status",
                    f"",
                ]
            )
            if backup_result.get("success"):
                lines.append(
                    f"✅ **Session backed up to Google Drive** (ID: `{backup_result.get('backup_id')}`)"
                )
            else:
                error = backup_result.get("error", "unknown")
                lines.append(f"⚠️ **Backup failed:** {error}")
            lines.append(f"")
    except ImportError:
        # Backup integration not available
        pass
    except Exception:
        # Backup failed, but continue with handoff
        pass

    # Write handoff file
    handoff_path = cfg.get_handoff_path(session_id)
    with open(handoff_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return str(handoff_path)


# ============================================================================
# Module Initialization
# ============================================================================


def reset_snapshot_counter():
    """Reset snapshot counter (primarily for testing)."""
    global _snapshot_counter, _last_agent_count, _last_token_count
    _snapshot_counter = 0
    _last_agent_count = 0
    _last_token_count = 0


__all__ = [
    "take_snapshot",
    "restore_snapshot",
    "list_snapshots",
    "cleanup_old_snapshots",
    "create_handoff_summary",
    "should_take_snapshot",
    "get_git_state",
    "reset_snapshot_counter",
]
