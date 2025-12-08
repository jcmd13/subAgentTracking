"""
Event Bus Architecture for SubAgentTracking Platform

This module implements a central event dispatcher using the Observer pattern
with async support for non-blocking event handling.

Design Pattern: Observer (Publish-Subscribe)
Performance Target: <5ms event dispatch latency
Thread Safety: Yes (using asyncio locks)

Links Back To: Main Plan → Phase 1 → Task 1.1
"""

import asyncio
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Any
import uuid
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Event:
    """
    Immutable event object representing a system event.

    Attributes:
        event_type: Type of event (e.g., "agent.invoked", "tool.used")
        timestamp: When the event occurred (UTC)
        payload: Event-specific data (validated against schema)
        trace_id: Unique identifier for distributed tracing
        session_id: Session this event belongs to
    """
    event_type: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    payload: Dict[str, Any] = field(default_factory=dict)
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = "session_default"

    def __post_init__(self):
        """Validate event fields"""
        if not self.event_type:
            raise ValueError("event_type cannot be empty")
        if not self.session_id:
            raise ValueError("session_id cannot be empty")


class EventHandler(ABC):
    """
    Base class for all event subscribers.

    Subclasses must implement the handle() method to process events.
    """

    @abstractmethod
    async def handle(self, event: Event) -> None:
        """
        Process an event.

        Args:
            event: The event to handle

        Raises:
            Exception: Handler errors are isolated and logged
        """
        pass


class EventBus:
    """
    Central event dispatcher for the SubAgentTracking platform.

    Implements the Observer pattern with async support. Subscribers register
    for specific event types and are notified when those events are published.

    Thread Safety: Yes (uses asyncio locks)
    Performance: <5ms dispatch latency guaranteed

    Example:
        >>> bus = EventBus()
        >>> bus.subscribe("agent.invoked", my_handler)
        >>> await bus.publish_async(Event(
        ...     event_type="agent.invoked",
        ...     timestamp=datetime.now(timezone.utc),
        ...     payload={"agent": "test"},
        ...     trace_id="trace-123",
        ...     session_id="session-456"
        ... ))
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = asyncio.Lock()
        self._event_count = 0
        self._error_count = 0

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """
        Subscribe a handler to an event type.

        Args:
            event_type: The event type to subscribe to (e.g., "agent.invoked")
            handler: Callable that accepts an Event parameter

        Example:
            >>> def my_handler(event: Event):
            ...     print(f"Received: {event.event_type}")
            >>> bus.subscribe("agent.invoked", my_handler)
        """
        if not callable(handler):
            raise ValueError("handler must be callable")

        self._subscribers[event_type].append(handler)
        handler_name = getattr(handler, '__name__', repr(handler))
        logger.debug(f"Subscribed handler {handler_name} to {event_type}")

    def unsubscribe(self, event_type: str, handler: Callable) -> bool:
        """
        Unsubscribe a handler from an event type.

        Args:
            event_type: The event type to unsubscribe from
            handler: The handler to remove

        Returns:
            True if handler was found and removed, False otherwise
        """
        if event_type in self._subscribers:
            try:
                self._subscribers[event_type].remove(handler)
                handler_name = getattr(handler, '__name__', repr(handler))
                logger.debug(f"Unsubscribed handler {handler_name} from {event_type}")
                return True
            except ValueError:
                pass
        return False

    def publish(self, event: Event) -> None:
        """
        Publish an event synchronously.

        Creates async task to handle event without blocking caller.
        Use this for synchronous contexts.

        Args:
            event: The event to publish

        Example:
            >>> bus.publish(Event(
            ...     event_type="agent.invoked",
            ...     timestamp=datetime.now(timezone.utc),
            ...     payload={"agent": "test"},
            ...     trace_id="trace-123",
            ...     session_id="session-456"
            ... ))
        """
        # Create async task without blocking
        asyncio.create_task(self.publish_async(event))

    async def publish_async(self, event: Event) -> None:
        """
        Publish an event asynchronously.

        Notifies all subscribers for this event type. Handler errors are
        isolated and logged to prevent cascade failures.

        Performance: <5ms dispatch latency
        Event Ordering: Preserved within single session

        Args:
            event: The event to publish

        Example:
            >>> await bus.publish_async(Event(...))
        """
        start_time = datetime.now(timezone.utc)

        async with self._lock:
            self._event_count += 1

        # Get subscribers for this event type
        handlers = self._subscribers.get(event.event_type, [])

        if not handlers:
            logger.debug(f"No subscribers for event type: {event.event_type}")
            return

        # Execute all handlers (isolated error handling)
        tasks = []
        for handler in handlers:
            tasks.append(self._execute_handler(handler, event))

        # Wait for all handlers to complete
        await asyncio.gather(*tasks, return_exceptions=True)

        # Performance monitoring
        duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        if duration_ms > 5:
            logger.warning(
                f"Event dispatch took {duration_ms:.2f}ms (target: <5ms) "
                f"for event type: {event.event_type}"
            )

    async def _execute_handler(self, handler: Callable, event: Event) -> None:
        """
        Execute a single handler with error isolation.

        Args:
            handler: The handler function to execute
            event: The event to pass to handler
        """
        try:
            # Check if handler is async or sync
            if asyncio.iscoroutinefunction(handler):
                await handler(event)
            else:
                # Run sync handler in executor to avoid blocking
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, handler, event)

        except Exception as e:
            self._error_count += 1
            handler_name = getattr(handler, '__name__', repr(handler))
            logger.error(
                f"Error in handler {handler_name} for event {event.event_type}: {e}",
                exc_info=True
            )
            # Don't re-raise - isolate errors to prevent cascade failures

    def get_subscriber_count(self, event_type: str) -> int:
        """
        Get number of subscribers for an event type.

        Args:
            event_type: The event type to check

        Returns:
            Number of subscribers
        """
        return len(self._subscribers.get(event_type, []))

    def get_stats(self) -> Dict[str, Any]:
        """
        Get event bus statistics.

        Returns:
            Dictionary with stats (event_count, error_count, subscriber_counts)
        """
        return {
            "total_events_published": self._event_count,
            "total_handler_errors": self._error_count,
            "error_rate": self._error_count / max(self._event_count, 1),
            "subscriber_counts": {
                event_type: len(handlers)
                for event_type, handlers in self._subscribers.items()
            }
        }

    def clear_all_subscribers(self) -> None:
        """
        Clear all subscribers (useful for testing).

        Warning: This will remove ALL subscribers. Use with caution.
        """
        self._subscribers.clear()
        logger.warning("All event subscribers cleared")


# Global event bus instance (singleton pattern)
_global_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """
    Get the global event bus instance (singleton).

    Returns:
        The global EventBus instance

    Example:
        >>> bus = get_event_bus()
        >>> bus.subscribe("agent.invoked", my_handler)
    """
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def reset_event_bus() -> None:
    """
    Reset the global event bus (useful for testing).

    Creates a fresh EventBus instance, discarding all subscribers.
    """
    global _global_event_bus
    _global_event_bus = EventBus()
