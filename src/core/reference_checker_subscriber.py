"""
Reference Checker Event Subscriber

Subscribes to event bus and triggers PRD reference checks based on:
- Agent invocation count (every 5 invocations by default)
- Token consumption (every 15k tokens by default)
- Manual reference check requests

This ensures agents regularly see reminders about original requirements
to prevent requirement drift during project execution.

Usage:
    from src.core.reference_checker_subscriber import initialize_reference_checker_subscriber

    # Initialize and connect to event bus
    subscriber = initialize_reference_checker_subscriber()

    # Subscriber will now automatically trigger reference checks
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional, Callable
import logging

from src.core.event_bus import Event, EventHandler, get_event_bus
from src.core.event_types import AGENT_INVOKED, SESSION_TOKEN_WARNING
from src.core.reference_checker import (
    get_reference_checker,
    initialize_reference_checker,
    ReferenceChecker,
)
from src.core.config import get_config

logger = logging.getLogger(__name__)


# Custom event types for reference checking
REFERENCE_CHECK_TRIGGERED = "reference_check.triggered"
REFERENCE_CHECK_COMPLETED = "reference_check.completed"


class ReferenceCheckerSubscriber(EventHandler):
    """
    Subscribes to events and triggers PRD reference checks.

    Triggers:
    - Every N agent invocations (configurable, default 5)
    - Every M tokens consumed (configurable, default 15k)
    - Manual reference check events

    Performance: <5ms reference check (non-blocking prompt generation)
    """

    def __init__(
        self,
        agent_interval: Optional[int] = None,
        token_interval: Optional[int] = None,
        on_reference_check: Optional[Callable[[str], None]] = None,
    ):
        """
        Initialize reference checker subscriber.

        Args:
            agent_interval: Agent invocations between checks (default: from config)
            token_interval: Tokens consumed between checks (default: from config)
            on_reference_check: Optional callback when reference check occurs
        """
        cfg = get_config()

        self.agent_interval = agent_interval or cfg.prd_reference_agent_interval
        self.token_interval = token_interval or cfg.prd_reference_token_interval
        self.on_reference_check = on_reference_check

        self._agent_count = 0
        self._token_count = 0
        self._reference_count = 0
        self._last_check_agent_count = 0
        self._last_check_token_count = 0
        self._lock = asyncio.Lock()

        # Get or create reference checker
        self._checker = get_reference_checker()
        if self._checker is None:
            self._checker = initialize_reference_checker(
                agent_interval=self.agent_interval,
                token_interval=self.token_interval,
            )

        logger.debug(
            "ReferenceCheckerSubscriber initialized: agent_interval=%d, token_interval=%d",
            self.agent_interval,
            self.token_interval,
        )

    async def handle(self, event: Event) -> None:
        """
        Handle events and trigger reference checks when appropriate.

        Args:
            event: Event to process
        """
        try:
            if event.event_type == AGENT_INVOKED:
                await self._handle_agent_invoked(event)

            elif event.event_type == SESSION_TOKEN_WARNING:
                await self._handle_token_warning(event)

        except Exception as e:
            logger.error("Error in reference checker subscriber: %s", e, exc_info=True)

    async def _handle_agent_invoked(self, event: Event) -> None:
        """
        Handle agent invocation event.

        Checks if reference check should be triggered based on agent count.

        Args:
            event: AGENT_INVOKED event
        """
        async with self._lock:
            self._agent_count += 1

            # Get agent name from event payload
            agent_name = event.payload.get("agent", "unknown")

            # Check if reference check should be triggered
            should_check, trigger = self._checker.should_reference_check(
                agent_count=self._agent_count
            )

            if should_check:
                await self._perform_reference_check(
                    agent=agent_name,
                    trigger=trigger,
                    event=event,
                )
                self._last_check_agent_count = self._agent_count

    async def _handle_token_warning(self, event: Event) -> None:
        """
        Handle token warning event.

        May trigger reference check based on token consumption.

        Args:
            event: SESSION_TOKEN_WARNING event
        """
        payload = event.payload
        tokens_used = payload.get("tokens_used", 0)

        async with self._lock:
            self._token_count = tokens_used

            # Check if reference check should be triggered
            should_check, trigger = self._checker.should_reference_check(
                token_count=tokens_used
            )

            if should_check:
                await self._perform_reference_check(
                    agent="system",
                    trigger=trigger,
                    event=event,
                )
                self._last_check_token_count = tokens_used

    async def _perform_reference_check(
        self,
        agent: str,
        trigger: str,
        event: Event,
    ) -> None:
        """
        Perform the reference check and surface requirements.

        Args:
            agent: Agent that triggered the check
            trigger: Trigger reason
            event: Triggering event
        """
        try:
            # Publish check triggered event
            await self._publish_reference_triggered(trigger)

            # Get relevant requirements
            requirements = self._checker.get_relevant_requirements(max_items=5)

            # Generate prompt
            prompt = self._checker.generate_reference_prompt(requirements, trigger)

            # Log the reference
            requirement_ids = [req["id"] for req in requirements]
            self._checker.log_reference(
                requirement_ids=requirement_ids,
                agent=agent,
                trigger=trigger,
            )

            self._reference_count += 1

            # Call callback if provided
            if self.on_reference_check:
                self.on_reference_check(prompt)

            # Publish check completed event
            await self._publish_reference_completed(
                trigger=trigger,
                requirement_count=len(requirements),
                prompt=prompt,
            )

            logger.info(
                "Reference check completed: trigger=%s, requirements=%d",
                trigger,
                len(requirements),
            )

        except Exception as e:
            logger.error("Failed to perform reference check: %s", e, exc_info=True)

    async def _publish_reference_triggered(self, trigger: str) -> None:
        """
        Publish REFERENCE_CHECK_TRIGGERED event to event bus.

        Args:
            trigger: What triggered the check
        """
        event_bus = get_event_bus()
        event = Event(
            event_type=REFERENCE_CHECK_TRIGGERED,
            timestamp=datetime.now(timezone.utc),
            payload={
                "trigger": trigger,
                "agent_count": self._agent_count,
                "token_count": self._token_count,
            },
            trace_id=f"refcheck-{self._reference_count}",
            session_id="unknown",  # Will be filled by event bus if available
        )
        event_bus.publish(event)

    async def _publish_reference_completed(
        self,
        trigger: str,
        requirement_count: int,
        prompt: str,
    ) -> None:
        """
        Publish REFERENCE_CHECK_COMPLETED event to event bus.

        Args:
            trigger: What triggered the check
            requirement_count: Number of requirements surfaced
            prompt: The generated reference prompt
        """
        event_bus = get_event_bus()
        event = Event(
            event_type=REFERENCE_CHECK_COMPLETED,
            timestamp=datetime.now(timezone.utc),
            payload={
                "trigger": trigger,
                "requirement_count": requirement_count,
                "prompt_length": len(prompt),
                "reference_number": self._reference_count,
            },
            trace_id=f"refcheck-{self._reference_count}",
            session_id="unknown",
        )
        event_bus.publish(event)

    def subscribe_to_events(self, event_bus=None) -> None:
        """
        Subscribe to reference check trigger events on the event bus.

        Args:
            event_bus: EventBus instance (default: global bus)
        """
        if event_bus is None:
            event_bus = get_event_bus()

        # Subscribe to agent invocations
        event_bus.subscribe(AGENT_INVOKED, self.handle)

        # Subscribe to token warnings
        event_bus.subscribe(SESSION_TOKEN_WARNING, self.handle)

        logger.info("Reference checker subscribed to trigger events")

    def get_stats(self) -> dict:
        """
        Get reference checker subscriber statistics.

        Returns:
            Dict with agent_count, reference_count, etc.
        """
        return {
            "agent_invocations": self._agent_count,
            "reference_checks": self._reference_count,
            "last_check_at_agent": self._last_check_agent_count,
            "last_check_at_token": self._last_check_token_count,
            "agent_interval": self.agent_interval,
            "token_interval": self.token_interval,
        }

    async def force_reference_check(self, agent: str = "user") -> Optional[str]:
        """
        Force a reference check regardless of intervals.

        Args:
            agent: Agent name for logging

        Returns:
            Reference prompt if PRD exists, None otherwise
        """
        requirements = self._checker.get_relevant_requirements(max_items=5)
        if not requirements:
            return None

        prompt = self._checker.generate_reference_prompt(requirements, "manual")

        requirement_ids = [req["id"] for req in requirements]
        self._checker.log_reference(
            requirement_ids=requirement_ids,
            agent=agent,
            trigger="manual",
        )

        self._reference_count += 1

        if self.on_reference_check:
            self.on_reference_check(prompt)

        return prompt


# ============================================================================
# Global Instance Management
# ============================================================================

_global_subscriber: Optional[ReferenceCheckerSubscriber] = None


def get_reference_checker_subscriber() -> Optional[ReferenceCheckerSubscriber]:
    """
    Get the global reference checker subscriber instance.

    Returns:
        ReferenceCheckerSubscriber or None if not initialized
    """
    return _global_subscriber


def initialize_reference_checker_subscriber(
    agent_interval: Optional[int] = None,
    token_interval: Optional[int] = None,
    on_reference_check: Optional[Callable[[str], None]] = None,
) -> ReferenceCheckerSubscriber:
    """
    Initialize the global reference checker subscriber.

    Creates subscriber and connects to event bus.

    Args:
        agent_interval: Agent invocations between checks
        token_interval: Tokens consumed between checks
        on_reference_check: Callback when reference check occurs

    Returns:
        ReferenceCheckerSubscriber instance
    """
    global _global_subscriber

    cfg = get_config()

    # Check if reference checking is enabled
    if not cfg.prd_reference_check_enabled:
        logger.info("PRD reference checking is disabled in config")
        return None

    if _global_subscriber is not None:
        logger.warning("Reference checker subscriber already initialized")
        return _global_subscriber

    # Create subscriber
    _global_subscriber = ReferenceCheckerSubscriber(
        agent_interval=agent_interval,
        token_interval=token_interval,
        on_reference_check=on_reference_check,
    )

    # Subscribe to events
    _global_subscriber.subscribe_to_events()

    logger.info(
        "Reference checker initialized (agent_interval=%d, token_interval=%d)",
        _global_subscriber.agent_interval,
        _global_subscriber.token_interval,
    )

    return _global_subscriber


def shutdown_reference_checker_subscriber() -> None:
    """
    Shutdown the global reference checker subscriber.
    """
    global _global_subscriber
    _global_subscriber = None
    logger.info("Reference checker subscriber shutdown complete")


__all__ = [
    "ReferenceCheckerSubscriber",
    "get_reference_checker_subscriber",
    "initialize_reference_checker_subscriber",
    "shutdown_reference_checker_subscriber",
    "REFERENCE_CHECK_TRIGGERED",
    "REFERENCE_CHECK_COMPLETED",
]
