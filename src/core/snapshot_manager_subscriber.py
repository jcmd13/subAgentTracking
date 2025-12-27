"""
Snapshot Manager Event Subscriber

Subscribes to event bus and automatically creates snapshots based on:
- Agent invocation count (every 10 invocations)
- Token consumption warnings (70%+ of budget)
- Manual snapshot requests

Links Back To: Main Plan → Phase 1 → Task 1.4

Migration Strategy:
- Event-driven snapshot triggers
- Maintains backward compatibility with take_snapshot()
- Performance: <100ms snapshot creation
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, Any
import logging

from src.core.event_bus import Event, EventHandler, get_event_bus
from src.core.event_types import (
    AGENT_INVOKED,
    SESSION_TOKEN_WARNING,
    SNAPSHOT_CREATED,
    SNAPSHOT_FAILED
)
from src.core.snapshot_manager import take_snapshot as create_snapshot_file
from src.core.config import get_config

logger = logging.getLogger(__name__)


class SnapshotManagerSubscriber(EventHandler):
    """
    Subscribes to events and creates snapshots automatically.

    Triggers:
    - Every 10 agent invocations
    - Token warning at 70% or higher
    - Manual snapshot events

    Performance: <100ms snapshot creation (non-blocking)
    """

    def __init__(self, snapshot_interval: int = 10):
        """
        Initialize snapshot manager subscriber.

        Args:
            snapshot_interval: Number of agent invocations between snapshots
        """
        self.snapshot_interval = snapshot_interval
        self._agent_count = 0
        self._token_count = 0
        self._tokens_remaining = 0
        self._last_snapshot_agent_count = 0
        self._snapshot_count = 0
        self._lock: Optional[asyncio.Lock] = None

        # Track files in context (approximate)
        self._files_in_context = set()

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def handle(self, event: Event) -> None:
        """
        Handle events and trigger snapshots when appropriate.

        Args:
            event: Event to process
        """
        try:
            if event.event_type == AGENT_INVOKED:
                await self._handle_agent_invoked(event)

            elif event.event_type == SESSION_TOKEN_WARNING:
                await self._handle_token_warning(event)

        except Exception as e:
            logger.error(f"Error in snapshot manager subscriber: {e}", exc_info=True)
            # Publish SNAPSHOT_FAILED event
            await self._publish_snapshot_failed(str(e))

    async def _handle_agent_invoked(self, event: Event) -> None:
        """
        Handle agent invocation event.

        Creates snapshot every N invocations.

        Args:
            event: AGENT_INVOKED event
        """
        async with self._get_lock():
            self._agent_count += 1

            # Check if we should create snapshot
            agents_since_last = self._agent_count - self._last_snapshot_agent_count

            if agents_since_last >= self.snapshot_interval:
                # Time for a snapshot
                await self._create_snapshot(
                    trigger=f"agent_count_{self.snapshot_interval}",
                    event=event
                )
                self._last_snapshot_agent_count = self._agent_count

    async def _handle_token_warning(self, event: Event) -> None:
        """
        Handle token warning event.

        Creates snapshot when token usage reaches 70% or higher.

        Args:
            event: SESSION_TOKEN_WARNING event
        """
        payload = event.payload
        percent = payload.get("percent", 0)

        # Create snapshot at 70% threshold
        if percent >= 70:
            await self._create_snapshot(
                trigger=f"token_limit_{int(percent)}pct",
                event=event
            )

            # Update token tracking
            async with self._get_lock():
                self._tokens_remaining = payload.get("tokens_limit", 200000) - payload.get("tokens_used", 0)
                self._token_count = payload.get("tokens_used", 0)

    async def _create_snapshot(self, trigger: str, event: Event) -> None:
        """
        Create a snapshot file and publish SNAPSHOT_CREATED event.

        Args:
            trigger: Reason for snapshot
            event: Triggering event
        """
        try:
            # Run snapshot creation in executor (I/O bound)
            loop = asyncio.get_running_loop()

            snapshot_id = await loop.run_in_executor(
                None,
                create_snapshot_file,
                trigger,
                self._agent_count,
                self._token_count,
                self._tokens_remaining,
                list(self._files_in_context),
                None  # agent_context
            )

            self._snapshot_count += 1

            # Publish SNAPSHOT_CREATED event
            await self._publish_snapshot_created(snapshot_id, trigger)

            logger.info(f"Snapshot created: {snapshot_id} (trigger: {trigger})")

        except Exception as e:
            logger.error(f"Failed to create snapshot: {e}", exc_info=True)
            await self._publish_snapshot_failed(str(e))

    async def _publish_snapshot_created(self, snapshot_id: str, trigger: str) -> None:
        """
        Publish SNAPSHOT_CREATED event to event bus.

        Args:
            snapshot_id: ID of created snapshot
            trigger: What triggered the snapshot
        """
        event_bus = get_event_bus()
        event = Event(
            event_type=SNAPSHOT_CREATED,
            timestamp=datetime.now(timezone.utc),
            payload={
                "snapshot_id": snapshot_id,
                "trigger": trigger,
                "size_bytes": 0,  # TODO: Get actual size
                "agent_count": self._agent_count,
                "token_count": self._token_count
            },
            trace_id=f"snapshot-{snapshot_id}",
            session_id=snapshot_id.split("_")[0] if "_" in snapshot_id else "unknown"
        )
        event_bus.publish(event)

    async def _publish_snapshot_failed(self, error_msg: str) -> None:
        """
        Publish SNAPSHOT_FAILED event to event bus.

        Args:
            error_msg: Error message
        """
        event_bus = get_event_bus()
        event = Event(
            event_type=SNAPSHOT_FAILED,
            timestamp=datetime.now(timezone.utc),
            payload={
                "trigger": "auto",
                "error_msg": error_msg,
                "agent_count": self._agent_count
            },
            trace_id=f"snapshot-failed-{self._snapshot_count}",
            session_id="unknown"
        )
        event_bus.publish(event)

    def subscribe_to_events(self, event_bus=None) -> None:
        """
        Subscribe to snapshot trigger events on the event bus.

        Args:
            event_bus: EventBus instance (default: global bus)
        """
        if event_bus is None:
            event_bus = get_event_bus()

        # Subscribe to agent invocations
        event_bus.subscribe(AGENT_INVOKED, self.handle)

        # Subscribe to token warnings
        event_bus.subscribe(SESSION_TOKEN_WARNING, self.handle)

        logger.info("Snapshot manager subscribed to trigger events")

    def get_stats(self) -> dict:
        """
        Get snapshot manager statistics.

        Returns:
            Dict with agent_count, snapshot_count, etc.
        """
        return {
            "agent_invocations": self._agent_count,
            "snapshots_created": self._snapshot_count,
            "last_snapshot_at_agent": self._last_snapshot_agent_count,
            "tokens_consumed": self._token_count,
            "tokens_remaining": self._tokens_remaining
        }


# Global subscriber instance
_global_subscriber: Optional[SnapshotManagerSubscriber] = None


def get_snapshot_manager_subscriber() -> Optional[SnapshotManagerSubscriber]:
    """
    Get the global snapshot manager subscriber instance.

    Returns:
        SnapshotManagerSubscriber or None if not initialized
    """
    return _global_subscriber


def initialize_snapshot_manager_subscriber(
    snapshot_interval: int = 10
) -> SnapshotManagerSubscriber:
    """
    Initialize the global snapshot manager subscriber.

    Creates subscriber and connects to event bus.

    Args:
        snapshot_interval: Number of agent invocations between snapshots

    Returns:
        SnapshotManagerSubscriber instance
    """
    global _global_subscriber

    if _global_subscriber is not None:
        logger.warning("Snapshot manager subscriber already initialized")
        return _global_subscriber

    # Create subscriber
    _global_subscriber = SnapshotManagerSubscriber(
        snapshot_interval=snapshot_interval
    )

    # Subscribe to events
    _global_subscriber.subscribe_to_events()

    logger.info(f"Snapshot manager initialized (interval: {snapshot_interval} agents)")

    return _global_subscriber


def shutdown_snapshot_manager_subscriber() -> None:
    """
    Shutdown the global snapshot manager subscriber.
    """
    global _global_subscriber
    _global_subscriber = None
    logger.info("Snapshot manager subscriber shutdown complete")
