"""
Analytics Database Event Subscriber

Subscribes to event bus and populates SQLite analytics database automatically.
Provides real-time analytics aggregation from event stream.

Links Back To: Main Plan → Phase 1 → Task 1.5

Migration Strategy:
- Event-driven database updates
- Batch inserts for performance (<2ms per event)
- Maintains backward compatibility with existing analytics_db.py
- Async processing to avoid blocking event bus
"""

import asyncio
import sqlite3
from datetime import datetime
from typing import Optional, List
import logging
import json

from src.core.event_bus import Event, EventHandler, get_event_bus
from src.core.event_types import (
    AGENT_INVOKED, AGENT_COMPLETED, AGENT_FAILED,
    TOOL_USED, TOOL_ERROR,
    SESSION_STARTED, SESSION_ENDED,
    COST_TRACKED,
    ALL_EVENT_TYPES
)
from src.core.analytics_db import AnalyticsDB

logger = logging.getLogger(__name__)


class AnalyticsDBSubscriber(EventHandler):
    """
    Subscribes to all events and updates analytics database.

    Features:
    - Real-time event ingestion
    - Batch inserts for performance (100 events at a time)
    - Automatic aggregate updates (counts, averages, etc.)
    - Non-blocking async processing

    Performance: <2ms per event (batched)
    """

    def __init__(self, db: AnalyticsDB, batch_size: int = 100):
        """
        Initialize analytics database subscriber.

        Args:
            db: AnalyticsDB instance
            batch_size: Number of events to batch before flush
        """
        self.db = db
        self.batch_size = batch_size

        # Event buffers for batch processing
        self._agent_perf_buffer: List[tuple] = []
        self._tool_usage_buffer: List[tuple] = []
        self._error_buffer: List[tuple] = []
        self._session_buffer: List[tuple] = []

        self._lock = asyncio.Lock()
        self._event_count = 0
        self._insert_count = 0
        self._error_count = 0

        # Session tracking (in-memory cache)
        self._active_sessions = {}

    async def handle(self, event: Event) -> None:
        """
        Handle events and update analytics database.

        Args:
            event: Event to process
        """
        try:
            self._event_count += 1

            # Route to appropriate handler
            if event.event_type in [AGENT_INVOKED, AGENT_COMPLETED, AGENT_FAILED]:
                await self._handle_agent_event(event)

            elif event.event_type in [TOOL_USED, TOOL_ERROR]:
                await self._handle_tool_event(event)

            elif event.event_type == SESSION_STARTED:
                await self._handle_session_started(event)

            elif event.event_type == SESSION_ENDED:
                await self._handle_session_ended(event)

            elif event.event_type == COST_TRACKED:
                await self._handle_cost_event(event)

            # Check if we should flush buffers
            async with self._lock:
                total_buffered = (
                    len(self._agent_perf_buffer) +
                    len(self._tool_usage_buffer) +
                    len(self._error_buffer)
                )

                if total_buffered >= self.batch_size:
                    await self._flush_buffers()

        except Exception as e:
            self._error_count += 1
            logger.error("Error in analytics subscriber for event %s: %s", event.event_type, e, exc_info=True)

    async def _handle_agent_event(self, event: Event) -> None:
        """
        Handle agent-related events (invoked, completed, failed).

        Args:
            event: Agent event
        """
        payload = event.payload

        # Parse timestamp
        timestamp = event.timestamp.isoformat() if hasattr(event.timestamp, 'isoformat') else str(event.timestamp)

        # Determine success status
        success = True
        if event.event_type == AGENT_FAILED:
            success = False
        elif event.event_type == AGENT_COMPLETED:
            success = payload.get("exit_code", 0) == 0

        # Buffer agent performance record
        async with self._lock:
            self._agent_perf_buffer.append((
                timestamp,
                event.session_id,
                payload.get("event_id"),
                payload.get("agent"),
                payload.get("invoked_by"),
                payload.get("reason"),  # task_type
                payload.get("duration_ms"),
                payload.get("tokens_used") or payload.get("tokens_consumed"),
                event.event_type.split(".")[-1],  # status: invoked/completed/failed
                success
            ))

    async def _handle_tool_event(self, event: Event) -> None:
        """
        Handle tool usage events.

        Args:
            event: Tool event
        """
        payload = event.payload

        timestamp = event.timestamp.isoformat() if hasattr(event.timestamp, 'isoformat') else str(event.timestamp)

        # Determine success and error info
        success = payload.get("success", True) if event.event_type == TOOL_USED else False
        error_type = payload.get("error_type") if event.event_type == TOOL_ERROR else None
        error_msg = payload.get("error_msg") if event.event_type == TOOL_ERROR else None

        # Buffer tool usage record
        async with self._lock:
            self._tool_usage_buffer.append((
                timestamp,
                event.session_id,
                payload.get("event_id"),
                payload.get("agent"),
                payload.get("tool"),
                payload.get("operation"),
                payload.get("duration_ms"),
                success,
                error_type,
                error_msg
            ))

        # If error, also buffer error record
        if event.event_type == TOOL_ERROR:
            async with self._lock:
                self._error_buffer.append((
                    timestamp,
                    event.session_id,
                    payload.get("event_id"),
                    payload.get("agent"),
                    error_type or "ToolError",
                    error_msg,
                    "medium",  # severity
                    None,  # file_path
                    payload.get("attempted_fix"),
                    payload.get("fix_successful"),
                    None  # resolution_time_ms
                ))

    async def _handle_session_started(self, event: Event) -> None:
        """
        Handle session start event.

        Args:
            event: SESSION_STARTED event
        """
        payload = event.payload
        timestamp = event.timestamp.isoformat() if hasattr(event.timestamp, 'isoformat') else str(event.timestamp)

        # Track in memory
        self._active_sessions[event.session_id] = {
            "started_at": timestamp,
            "total_events": 0,
            "total_agents": 0,
            "total_tokens": 0
        }

        # Buffer session record
        async with self._lock:
            self._session_buffer.append((
                event.session_id,
                timestamp,
                None,  # ended_at
                0,  # total_events
                0,  # total_agents_invoked
                0,  # total_tokens_consumed
                None,  # success
                payload.get("phase"),
                None  # notes
            ))

    async def _handle_session_ended(self, event: Event) -> None:
        """
        Handle session end event.

        Args:
            event: SESSION_ENDED event
        """
        payload = event.payload
        timestamp = event.timestamp.isoformat() if hasattr(event.timestamp, 'isoformat') else str(event.timestamp)

        # Update session record
        loop = asyncio.get_event_loop()

        def update_session():
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE sessions
                    SET ended_at = ?,
                        total_events = ?,
                        total_agents_invoked = ?,
                        total_tokens_consumed = ?,
                        success = ?
                    WHERE session_id = ?
                """, (
                    timestamp,
                    payload.get("events_logged", 0),
                    payload.get("agents_invoked", 0),
                    payload.get("total_tokens", 0),
                    True,  # TODO: Determine from exit status
                    event.session_id
                ))

        await loop.run_in_executor(None, update_session)

        # Remove from active sessions
        if event.session_id in self._active_sessions:
            del self._active_sessions[event.session_id]

    async def _handle_cost_event(self, event: Event) -> None:
        """
        Handle cost tracking event.

        Args:
            event: COST_TRACKED event
        """
        # Cost tracking can be added to a separate table in the future
        # For now, we track costs via agent_performance table
        pass

    async def _flush_buffers(self) -> None:
        """
        Flush all buffered events to database (batch insert).
        """
        if not any([
            self._agent_perf_buffer,
            self._tool_usage_buffer,
            self._error_buffer,
            self._session_buffer
        ]):
            return

        loop = asyncio.get_event_loop()

        def flush_sync():
            """Synchronous batch insert"""
            with self.db.get_connection() as conn:
                cursor = conn.cursor()

                # Insert agent performance records
                if self._agent_perf_buffer:
                    cursor.executemany("""
                        INSERT INTO agent_performance (
                            timestamp, session_id, event_id, agent_name, invoked_by,
                            task_type, duration_ms, tokens_consumed, status, success
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, self._agent_perf_buffer)
                    self._insert_count += len(self._agent_perf_buffer)

                # Insert tool usage records
                if self._tool_usage_buffer:
                    cursor.executemany("""
                        INSERT INTO tool_usage (
                            timestamp, session_id, event_id, agent_name, tool_name,
                            operation, duration_ms, success, error_type, error_message
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, self._tool_usage_buffer)
                    self._insert_count += len(self._tool_usage_buffer)

                # Insert error records
                if self._error_buffer:
                    cursor.executemany("""
                        INSERT INTO error_patterns (
                            timestamp, session_id, event_id, agent_name, error_type,
                            error_message, severity, file_path, fix_attempted,
                            fix_successful, resolution_time_ms
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, self._error_buffer)
                    self._insert_count += len(self._error_buffer)

                # Insert session records
                if self._session_buffer:
                    cursor.executemany("""
                        INSERT OR IGNORE INTO sessions (
                            session_id, started_at, ended_at, total_events,
                            total_agents_invoked, total_tokens_consumed,
                            success, phase, notes
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, self._session_buffer)
                    self._insert_count += len(self._session_buffer)

        try:
            # Run batch insert in executor
            await loop.run_in_executor(None, flush_sync)
        except Exception as e:
            self._error_count += 1
            logger.error("Error flushing analytics buffers: %s", e, exc_info=True)
        finally:
            # Clear buffers regardless of success/failure to avoid duplication
            self._agent_perf_buffer.clear()
            self._tool_usage_buffer.clear()
            self._error_buffer.clear()
            self._session_buffer.clear()

    async def shutdown(self) -> None:
        """
        Shutdown subscriber and flush remaining events.
        """
        async with self._lock:
            if any([self._agent_perf_buffer, self._tool_usage_buffer, self._error_buffer]):
                await self._flush_buffers()

    def subscribe_to_all(self, event_bus=None) -> None:
        """
        Subscribe to all event types on the event bus.

        Args:
            event_bus: EventBus instance (default: global bus)
        """
        if event_bus is None:
            event_bus = get_event_bus()

        # Subscribe to all event types
        for event_type in ALL_EVENT_TYPES:
            event_bus.subscribe(event_type, self.handle)

        logger.info(f"Analytics DB subscribed to {len(ALL_EVENT_TYPES)} event types")

    def get_stats(self) -> dict:
        """
        Get analytics subscriber statistics.

        Returns:
            Dict with event_count, insert_count, error_count, etc.
        """
        return {
            "events_processed": self._event_count,
            "records_inserted": self._insert_count,
            "processing_errors": self._error_count,
            "buffered_agent_records": len(self._agent_perf_buffer),
            "buffered_tool_records": len(self._tool_usage_buffer),
            "buffered_error_records": len(self._error_buffer),
            "active_sessions": len(self._active_sessions),
            "error_rate": self._error_count / max(self._event_count, 1)
        }


# Global subscriber instance
_global_subscriber: Optional[AnalyticsDBSubscriber] = None


def get_analytics_db_subscriber() -> Optional[AnalyticsDBSubscriber]:
    """
    Get the global analytics DB subscriber instance.

    Returns:
        AnalyticsDBSubscriber or None if not initialized
    """
    return _global_subscriber


def initialize_analytics_db_subscriber(
    db: Optional[AnalyticsDB] = None,
    batch_size: int = 100
) -> AnalyticsDBSubscriber:
    """
    Initialize the global analytics DB subscriber.

    Creates subscriber, initializes database, and connects to event bus.

    Args:
        db: AnalyticsDB instance (default: create new)
        batch_size: Number of events to batch before flush

    Returns:
        AnalyticsDBSubscriber instance
    """
    global _global_subscriber

    if _global_subscriber is not None:
        logger.warning("Analytics DB subscriber already initialized")
        return _global_subscriber

    # Create database if not provided
    if db is None:
        db = AnalyticsDB()
        db.initialize()

    # Create subscriber
    _global_subscriber = AnalyticsDBSubscriber(
        db=db,
        batch_size=batch_size
    )

    # Subscribe to all events
    _global_subscriber.subscribe_to_all()

    logger.info(f"Analytics DB subscriber initialized (batch size: {batch_size})")

    return _global_subscriber


async def shutdown_analytics_db_subscriber() -> None:
    """
    Shutdown the global analytics DB subscriber.

    Flushes any remaining buffered events.
    """
    global _global_subscriber

    if _global_subscriber is None:
        return

    await _global_subscriber.shutdown()
    _global_subscriber = None

    logger.info("Analytics DB subscriber shutdown complete")
