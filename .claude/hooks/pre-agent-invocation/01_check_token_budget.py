"""
Pre-Hook: Check Token Budget

Checks if token budget allows this invocation.
Blocks invocation if budget exceeded (>90%).

This is an example hook demonstrating the hooks system.
"""

from src.core.hooks_manager import HookContext, HookResult


def execute(context: HookContext) -> HookResult:
    """
    Check token budget before agent invocation.

    Args:
        context: Hook context with event data

    Returns:
        ALLOW if budget OK, DENY if exceeded, WARN if approaching limit
    """
    # Get current token usage from event
    current_tokens = context.get_token_usage()

    # Get budget from config (default: 150k for safety margin)
    budget = context.config.get("token_budget", 150000)

    # Calculate percentage used
    percent_used = (current_tokens / budget) * 100 if budget > 0 else 0

    # Decision logic
    if percent_used >= 90:
        # 90%+ of budget used - DENY and force handoff
        context.send_notification(
            f"Token budget 90% exceeded: {current_tokens}/{budget} ({percent_used:.1f}%)",
            channel="log"
        )
        context.logger.error(f"Agent invocation DENIED - token budget exceeded")
        return HookResult.DENY

    elif percent_used >= 70:
        # 70-90% - WARN but allow
        context.send_notification(
            f"Token budget warning: {current_tokens}/{budget} ({percent_used:.1f}%)",
            channel="log"
        )
        # Create safety snapshot
        context.create_snapshot(trigger="token_budget_70pct")
        return HookResult.WARN

    else:
        # <70% - all good
        return HookResult.ALLOW
