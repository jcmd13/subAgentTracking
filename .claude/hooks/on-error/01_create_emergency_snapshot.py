"""
On-Error Hook: Create Emergency Snapshot

Creates emergency snapshot when error detected for easy recovery.

This is an example hook demonstrating error handling hooks.
"""

from src.core.hooks_manager import HookContext, HookResult


def execute(context: HookContext) -> HookResult:
    """
    Create emergency snapshot on error.

    Args:
        context: Hook context with event data

    Returns:
        ALLOW (always, errors don't block)
    """
    # Extract error information
    payload = context.event.payload

    agent_name = payload.get("agent", "unknown")
    error_type = payload.get("error_type", "UnknownError")
    error_msg = payload.get("error_msg", "")

    # Log error
    context.logger.error(
        f"ERROR in agent '{agent_name}': {error_type} - {error_msg}"
    )

    # Create emergency snapshot for recovery
    snapshot_id = context.create_snapshot(trigger=f"error_{error_type}")

    if snapshot_id:
        context.logger.info(
            f"Emergency snapshot created: {snapshot_id} (can restore from this point)"
        )
        context.send_notification(
            f"Emergency snapshot {snapshot_id} created after error in {agent_name}",
            channel="log"
        )

    return HookResult.ALLOW
