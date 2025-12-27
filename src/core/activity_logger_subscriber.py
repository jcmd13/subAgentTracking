"""
Activity Logger Event Subscriber

Subscribes to event bus and writes events to JSONL log files.
This is the event-driven version that integrates with the event bus architecture.

Links Back To: Main Plan → Phase 1 → Task 1.3

Migration Strategy:
- New event-driven subscriber class
- Maintains same JSONL format as original logger
- Performance: <1ms overhead (same as before)
"""

import asyncio
import json
import gzip
from datetime import datetime
from pathlib import Path
from typing import Optional
import logging

from src.core.event_bus import Event, EventHandler, get_event_bus
from src.core.event_types import ALL_EVENT_TYPES
from src.core.config import get_config

logger = logging.getLogger(__name__)


class ActivityLoggerSubscriber(EventHandler):
    """
    Subscribes to all events and logs them to JSONL format.

    This class bridges the event bus to the activity logging system,
    writing all events to append-only JSONL files for audit trail.

    Performance: <1ms per event (async write with buffering)
    Format: JSONL (one JSON object per line)
    Compression: Optional gzip
    """

    def __init__(
        self,
        log_file_path: Path,
        use_compression: bool = False,
        buffer_size: int = 100
    ):
        """
        Initialize activity logger subscriber.

        Args:
            log_file_path: Path to JSONL log file
            use_compression: Enable gzip compression
            buffer_size: Number of events to buffer before flush
        """
        self.log_file_path = log_file_path
        self.use_compression = use_compression
        self.buffer_size = buffer_size

        # Event buffer for batch writes
        self._buffer = []
        self._lock: Optional[asyncio.Lock] = None
        self._write_count = 0
        self._error_count = 0

        # Ensure parent directory exists
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def handle(self, event: Event) -> None:
        """
        Handle an event by writing to JSONL log.

        Converts Event object to JSONL format and appends to log file.
        Uses buffering for performance.

        Args:
            event: Event to log
        """
        try:
            # Convert Event to JSONL-compatible dict
            log_entry = self._event_to_jsonl(event)

            # Add to buffer
            async with self._get_lock():
                self._buffer.append(log_entry)

                # Flush if buffer full
                if len(self._buffer) >= self.buffer_size:
                    await self._flush_buffer()

        except Exception as e:
            self._error_count += 1
            logger.error("Error logging event %s: %s", event.event_type, e, exc_info=True)

    def _event_to_jsonl(self, event: Event) -> dict:
        """
        Convert Event object to JSONL-compatible dictionary.

        Maps the event bus Event format to the activity logger JSONL format
        for backward compatibility.

        Args:
            event: Event to convert

        Returns:
            Dictionary ready for JSON serialization
        """
        # Base JSONL entry
        jsonl_entry = {
            "timestamp": event.timestamp.isoformat(),
            "session_id": event.session_id,
            "trace_id": event.trace_id,
            "event_type": event.event_type,
        }

        # Merge payload (flattened structure for JSONL)
        jsonl_entry.update(event.payload)

        return jsonl_entry

    async def _flush_buffer(self) -> None:
        """
        Flush buffered events to log file.

        Writes all buffered events in a single I/O operation for performance.
        """
        if not self._buffer:
            return

        try:
            # Get buffered events
            events_to_write = self._buffer.copy()
            self._buffer.clear()

            # Write to file
            if self.use_compression:
                await self._write_compressed(events_to_write)
            else:
                await self._write_uncompressed(events_to_write)

            self._write_count += len(events_to_write)

        except Exception as e:
            self._error_count += len(events_to_write)
            logger.error("Error flushing buffer: %s", e, exc_info=True)

    async def _write_uncompressed(self, events: list) -> None:
        """
        Write events to uncompressed JSONL file.

        Args:
            events: List of event dicts to write
        """
        loop = asyncio.get_running_loop()

        def write_sync():
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                for event in events:
                    json_line = json.dumps(event, ensure_ascii=False)
                    f.write(json_line + "\n")
                f.flush()

        # Run in executor to avoid blocking
        await loop.run_in_executor(None, write_sync)

    async def _write_compressed(self, events: list) -> None:
        """
        Write events to gzip-compressed JSONL file.

        Args:
            events: List of event dicts to write
        """
        loop = asyncio.get_running_loop()

        def write_sync():
            with gzip.open(self.log_file_path, "at", encoding="utf-8") as f:
                for event in events:
                    json_line = json.dumps(event, ensure_ascii=False)
                    f.write(json_line + "\n")
                f.flush()

        # Run in executor to avoid blocking
        await loop.run_in_executor(None, write_sync)

    async def shutdown(self) -> None:
        """
        Shutdown subscriber and flush remaining events.
        """
        async with self._get_lock():
            if self._buffer:
                await self._flush_buffer()

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

        logger.info(f"Activity logger subscribed to {len(ALL_EVENT_TYPES)} event types")

    def get_stats(self) -> dict:
        """
        Get activity logger statistics.

        Returns:
            Dict with write_count, error_count, buffer_size
        """
        return {
            "events_written": self._write_count,
            "write_errors": self._error_count,
            "buffered_events": len(self._buffer),
            "error_rate": self._error_count / max(self._write_count, 1)
        }


# Global subscriber instance
_global_subscriber: Optional[ActivityLoggerSubscriber] = None


def get_activity_logger_subscriber() -> Optional[ActivityLoggerSubscriber]:
    """
    Get the global activity logger subscriber instance.

    Returns:
        ActivityLoggerSubscriber or None if not initialized
    """
    return _global_subscriber


def initialize_activity_logger_subscriber(
    session_id: str,
    use_compression: bool = False
) -> ActivityLoggerSubscriber:
    """
    Initialize the global activity logger subscriber.

    Creates subscriber, connects to event bus, and starts logging.

    Args:
        session_id: Session ID for log file naming
        use_compression: Enable gzip compression

    Returns:
        ActivityLoggerSubscriber instance
    """
    global _global_subscriber

    if _global_subscriber is not None:
        logger.warning("Activity logger subscriber already initialized")
        return _global_subscriber

    config = get_config()

    # Create log file path
    log_path = config.logs_dir / f"{session_id}.jsonl"
    if use_compression:
        log_path = log_path.with_suffix(".jsonl.gz")

    # Create subscriber
    _global_subscriber = ActivityLoggerSubscriber(
        log_file_path=log_path,
        use_compression=use_compression
    )

    # Subscribe to all events
    _global_subscriber.subscribe_to_all()

    logger.info(f"Activity logger initialized: {log_path}")

    return _global_subscriber


async def shutdown_activity_logger_subscriber() -> None:
    """
    Shutdown the global activity logger subscriber.

    Flushes any remaining buffered events and closes log file.
    """
    global _global_subscriber

    if _global_subscriber is None:
        return

    await _global_subscriber.shutdown()
    _global_subscriber = None

    logger.info("Activity logger subscriber shutdown complete")
