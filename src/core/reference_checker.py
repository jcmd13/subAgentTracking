"""
Reference Checker - Periodic PRD Reference Check System

This module handles periodic reference checks against PRD requirements to ensure
agents stay aligned with original objectives throughout a project.

Key Components:
- ReferenceChecker class with configurable intervals
- Trigger detection (agent count, token count, manual)
- Relevant requirement selection
- Reference prompt generation
- Reference event logging

Usage:
    from src.core.reference_checker import get_reference_checker, initialize_reference_checker

    # Initialize with custom intervals
    checker = initialize_reference_checker(agent_interval=5, token_interval=15000)

    # Check if reference check is needed
    should_check, reason = checker.should_reference_check(agent_count=10)

    # Get relevant requirements
    if should_check:
        requirements = checker.get_relevant_requirements()
        prompt = checker.generate_reference_prompt(requirements, reason)
"""

import logging
import threading
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional, Set

from src.core import config
from src.core.prd_state import (
    load_prd,
    get_incomplete_items,
    get_completion_stats,
    increment_reference_count,
    prd_exists,
)
from src.core.prd_schemas import PRDDocument, RequirementStatus, Priority

logger = logging.getLogger(__name__)


# ============================================================================
# Reference Checker Class
# ============================================================================


class ReferenceChecker:
    """
    Manages periodic reference checks against PRD requirements.

    Triggers reference checks based on:
    - Agent invocation count (default: every 5 agents)
    - Token consumption (default: every 15k tokens)
    - Manual request
    - Before major decisions
    """

    def __init__(
        self,
        agent_interval: int = 5,
        token_interval: int = 15000,
    ):
        """
        Initialize the reference checker.

        Args:
            agent_interval: Check every N agent invocations
            token_interval: Check every N tokens consumed
        """
        self.agent_interval = agent_interval
        self.token_interval = token_interval

        # Tracking state
        self._last_agent_count = 0
        self._last_token_count = 0
        self._reference_history: List[str] = []  # Track recently referenced item IDs
        self._history_max_size = 50  # Keep last 50 referenced items
        self._total_reference_checks = 0

        # Thread safety
        self._lock = threading.Lock()

        logger.debug(
            "ReferenceChecker initialized: agent_interval=%d, token_interval=%d",
            agent_interval,
            token_interval,
        )

    def should_reference_check(
        self,
        agent_count: Optional[int] = None,
        token_count: Optional[int] = None,
        force: bool = False,
    ) -> Tuple[bool, str]:
        """
        Determine if a reference check should be triggered.

        Args:
            agent_count: Current agent invocation count (optional)
            token_count: Current token count (optional)
            force: Force a reference check regardless of intervals

        Returns:
            Tuple of (should_check, trigger_reason)

        Example:
            >>> should_check, reason = checker.should_reference_check(agent_count=10)
            >>> if should_check:
            ...     print(f"Reference check triggered: {reason}")
        """
        # Check if PRD exists first
        if not prd_exists():
            return False, "no_prd"

        if force:
            return True, "manual"

        with self._lock:
            # Check agent count trigger
            if agent_count is not None:
                agents_since_last = agent_count - self._last_agent_count
                if agents_since_last >= self.agent_interval:
                    self._last_agent_count = agent_count
                    return True, f"agent_count_{self.agent_interval}"

            # Check token count trigger
            if token_count is not None:
                tokens_since_last = token_count - self._last_token_count
                if tokens_since_last >= self.token_interval:
                    self._last_token_count = token_count
                    return True, f"token_count_{self.token_interval}"

        return False, "not_due"

    def get_relevant_requirements(
        self,
        current_context: Optional[str] = None,
        max_items: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Get requirements most relevant to current work context.

        Prioritizes:
        1. High priority incomplete items
        2. Items not recently referenced
        3. Context-matched items (if context provided)

        Args:
            current_context: Optional description of current work
            max_items: Maximum items to return

        Returns:
            List of requirement dicts with id, type, description, priority
        """
        # Get all incomplete items
        incomplete = get_incomplete_items()

        if not incomplete:
            return []

        # Sort by priority (high first) and filter out recently referenced
        with self._lock:
            recently_referenced = set(self._reference_history[-20:])

        # Score items
        scored_items = []
        for item in incomplete:
            score = 0

            # Priority scoring
            priority = item.get("priority", "medium")
            if priority == "high":
                score += 100
            elif priority == "medium":
                score += 50
            elif priority == "low":
                score += 10

            # Item type scoring (features and stories more important)
            item_type = item.get("type", "")
            if item_type == "feature":
                score += 30
            elif item_type == "story":
                score += 20
            elif item_type == "criterion":
                score += 10
            elif item_type == "task":
                score += 5

            # Penalty for recently referenced
            if item["id"] in recently_referenced:
                score -= 40

            # Context matching (simple keyword matching)
            if current_context:
                description = item.get("description", "").lower()
                context_lower = current_context.lower()
                # Simple word overlap
                description_words = set(description.split())
                context_words = set(context_lower.split())
                overlap = len(description_words & context_words)
                score += overlap * 15

            scored_items.append((score, item))

        # Sort by score descending
        scored_items.sort(key=lambda x: x[0], reverse=True)

        # Return top items
        return [item for _, item in scored_items[:max_items]]

    def generate_reference_prompt(
        self,
        requirements: List[Dict[str, Any]],
        trigger: str,
        include_stats: bool = True,
    ) -> str:
        """
        Generate a formatted reference check prompt.

        Args:
            requirements: List of requirement dicts to include
            trigger: What triggered this check (e.g., "agent_count_5")
            include_stats: Include overall completion statistics

        Returns:
            Markdown formatted prompt for display
        """
        lines = []

        # Header
        lines.append("## PRD Reference Check")
        lines.append("")
        lines.append(f"**Trigger**: {trigger}")
        lines.append(f"**Time**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        lines.append("")

        # Stats if requested
        if include_stats:
            stats = get_completion_stats()
            if stats:
                overall = stats.get("overall_percentage", 0)
                lines.append(f"**Overall Progress**: {overall:.0f}% complete")
                lines.append("")

        # Requirements section
        if requirements:
            lines.append("### Relevant Requirements to Keep in Mind")
            lines.append("")

            # Group by type
            by_type: Dict[str, List[Dict[str, Any]]] = {}
            for req in requirements:
                req_type = req.get("type", "other")
                if req_type not in by_type:
                    by_type[req_type] = []
                by_type[req_type].append(req)

            # Type labels
            type_labels = {
                "feature": "Features",
                "story": "User Stories",
                "criterion": "Acceptance Criteria",
                "task": "Tasks",
            }

            for req_type in ["feature", "story", "criterion", "task"]:
                if req_type in by_type:
                    lines.append(f"**{type_labels.get(req_type, req_type.title())}:**")
                    for req in by_type[req_type]:
                        priority_emoji = ""
                        if req.get("priority") == "high":
                            priority_emoji = " [HIGH]"
                        checkbox = "[ ]" if req.get("status") != "complete" else "[x]"
                        lines.append(
                            f"- {req['id']}: {checkbox} {req['description']}{priority_emoji}"
                        )
                    lines.append("")
        else:
            lines.append("*No incomplete requirements found - project may be complete!*")
            lines.append("")

        # Reminder
        lines.append("---")
        lines.append("")
        lines.append(
            "**Reminder**: These requirements should guide your current work. "
            "Are you addressing these items? If not, consider whether you should be."
        )
        lines.append("")
        lines.append("*[Reference: PRD.md]*")

        return "\n".join(lines)

    def log_reference(
        self,
        requirement_ids: List[str],
        agent: str,
        trigger: str,
        context: Optional[str] = None,
    ) -> Optional[str]:
        """
        Log a reference check event to activity logger.

        Args:
            requirement_ids: IDs of requirements that were referenced
            agent: Agent performing the reference check
            trigger: What triggered this check
            context: Optional current work context

        Returns:
            Event ID if logged, None otherwise
        """
        # Update reference history
        with self._lock:
            self._reference_history.extend(requirement_ids)
            # Trim history if too long
            if len(self._reference_history) > self._history_max_size:
                self._reference_history = self._reference_history[-self._history_max_size:]
            self._total_reference_checks += 1

        # Update PRD reference count
        increment_reference_count()

        # Log to activity logger
        try:
            from src.core.activity_logger_compat import log_reference_check_completed

            event_id = log_reference_check_completed(
                agent=agent,
                trigger=trigger,
                requirement_ids=requirement_ids,
                context=context,
            )
            logger.info(
                "Logged reference check: %d requirements, trigger=%s",
                len(requirement_ids),
                trigger,
            )
            return event_id
        except Exception:
            pass

        try:
            from src.core.activity_logger import log_requirement_reference

            event_id = log_requirement_reference(
                agent=agent,
                trigger=trigger,
                requirement_ids=requirement_ids,
                context=context,
            )
            logger.info(
                "Logged reference check via activity_logger: %d requirements, trigger=%s",
                len(requirement_ids),
                trigger,
            )
            return event_id
        except ImportError:
            logger.debug("Activity logger not available for reference logging")
            return None
        except Exception as e:
            logger.warning("Failed to log reference check: %s", e, exc_info=True)
            return None

    def perform_reference_check(
        self,
        agent: str,
        agent_count: Optional[int] = None,
        token_count: Optional[int] = None,
        current_context: Optional[str] = None,
        force: bool = False,
    ) -> Optional[str]:
        """
        Perform a complete reference check if triggered.

        Combines should_reference_check, get_relevant_requirements,
        generate_reference_prompt, and log_reference into one call.

        Args:
            agent: Agent performing the check
            agent_count: Current agent invocation count
            token_count: Current token count
            current_context: Optional description of current work
            force: Force a reference check regardless of intervals

        Returns:
            Reference prompt if check was triggered, None otherwise
        """
        should_check, trigger = self.should_reference_check(
            agent_count=agent_count,
            token_count=token_count,
            force=force,
        )

        if not should_check:
            return None

        # Get relevant requirements
        requirements = self.get_relevant_requirements(
            current_context=current_context,
            max_items=5,
        )

        # Generate prompt
        prompt = self.generate_reference_prompt(requirements, trigger)

        # Log the reference
        requirement_ids = [req["id"] for req in requirements]
        self.log_reference(
            requirement_ids=requirement_ids,
            agent=agent,
            trigger=trigger,
            context=current_context,
        )

        return prompt

    def get_stats(self) -> Dict[str, Any]:
        """Get reference checker statistics."""
        with self._lock:
            return {
                "agent_interval": self.agent_interval,
                "token_interval": self.token_interval,
                "last_agent_count": self._last_agent_count,
                "last_token_count": self._last_token_count,
                "total_reference_checks": self._total_reference_checks,
                "recently_referenced_count": len(self._reference_history),
            }

    def reset(self):
        """Reset reference checker state (for testing)."""
        with self._lock:
            self._last_agent_count = 0
            self._last_token_count = 0
            self._reference_history = []
            self._total_reference_checks = 0


# ============================================================================
# Global Instance Management
# ============================================================================

_reference_checker: Optional[ReferenceChecker] = None
_checker_lock = threading.Lock()


def get_reference_checker() -> Optional[ReferenceChecker]:
    """
    Get global ReferenceChecker instance.

    Returns None if not initialized or if PRD reference checking is disabled.

    Returns:
        ReferenceChecker instance or None
    """
    cfg = config.get_config()
    if not cfg.prd_reference_check_enabled:
        return None

    global _reference_checker
    with _checker_lock:
        if _reference_checker is None:
            _reference_checker = ReferenceChecker(
                agent_interval=cfg.prd_reference_agent_interval,
                token_interval=cfg.prd_reference_token_interval,
            )
    return _reference_checker


def initialize_reference_checker(
    agent_interval: Optional[int] = None,
    token_interval: Optional[int] = None,
) -> ReferenceChecker:
    """
    Initialize the reference checker with custom intervals.

    Args:
        agent_interval: Check every N agent invocations (default: from config)
        token_interval: Check every N tokens (default: from config)

    Returns:
        Initialized ReferenceChecker instance
    """
    global _reference_checker

    cfg = config.get_config()

    with _checker_lock:
        _reference_checker = ReferenceChecker(
            agent_interval=agent_interval or cfg.prd_reference_agent_interval,
            token_interval=token_interval or cfg.prd_reference_token_interval,
        )

    return _reference_checker


def reset_reference_checker():
    """Reset the global reference checker (for testing)."""
    global _reference_checker
    with _checker_lock:
        if _reference_checker is not None:
            _reference_checker.reset()
        _reference_checker = None


__all__ = [
    "ReferenceChecker",
    "get_reference_checker",
    "initialize_reference_checker",
    "reset_reference_checker",
]
