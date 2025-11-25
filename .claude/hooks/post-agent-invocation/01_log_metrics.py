"""
Post-Hook: Log Metrics

Logs agent invocation metrics after execution.

This is an example hook demonstrating post-execution hooks.
"""

from src.core.hooks_manager import HookContext, HookResult


def execute(context: HookContext) -> HookResult:
    """
    Log metrics after agent invocation.

    Args:
        context: Hook context with event data

    Returns:
        ALLOW (post-hooks don't block)
    """
    # Extract event payload
    payload = context.event.payload

    agent_name = payload.get("agent", "unknown")
    invoked_by = payload.get("invoked_by", "unknown")
    reason = payload.get("reason", "")

    # Log invocation
    context.logger.info(
        f"Agent '{agent_name}' invoked by '{invoked_by}' - Reason: {reason}"
    )

    # Could add more sophisticated logging here:
    # - Send to monitoring dashboard
    # - Update real-time metrics
    # - Trigger alerts based on patterns

    return HookResult.ALLOW
