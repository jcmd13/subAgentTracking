"""
Test suite for Event Bus Architecture

Links Back To: Main Plan → Phase 1 → Task 1.1 → Testing Requirements
Coverage Target: 100% on EventBus class
Performance Target: <5ms dispatch latency

Test Categories:
1. Subscribe/Unsubscribe (5 tests)
2. Publish Sync/Async (4 tests)
3. Multiple Subscribers (3 tests)
4. Event Ordering (2 tests)
5. Error Propagation (3 tests)
6. Performance (2 tests)
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock
from src.core.event_bus import Event, EventBus, EventHandler, get_event_bus, reset_event_bus


# Test Fixtures

@pytest.fixture
def event_bus():
    """Create fresh event bus for each test"""
    return EventBus()


@pytest.fixture
def sample_event():
    """Create sample event for testing"""
    return Event(
        event_type="test.event",
        timestamp=datetime.utcnow(),
        payload={"key": "value"},
        trace_id="trace-123",
        session_id="session-456"
    )


# Category 1: Subscribe/Unsubscribe Tests

def test_subscribe_handler(event_bus):
    """Test subscribing a handler to an event type"""
    handler = Mock()
    event_bus.subscribe("test.event", handler)

    assert event_bus.get_subscriber_count("test.event") == 1


def test_subscribe_multiple_handlers(event_bus):
    """Test subscribing multiple handlers to same event type"""
    handler1 = Mock()
    handler2 = Mock()
    handler3 = Mock()

    event_bus.subscribe("test.event", handler1)
    event_bus.subscribe("test.event", handler2)
    event_bus.subscribe("test.event", handler3)

    assert event_bus.get_subscriber_count("test.event") == 3


def test_subscribe_invalid_handler(event_bus):
    """Test subscribing non-callable raises error"""
    with pytest.raises(ValueError, match="handler must be callable"):
        event_bus.subscribe("test.event", "not_a_function")


def test_unsubscribe_handler(event_bus):
    """Test unsubscribing a handler"""
    handler = Mock()
    event_bus.subscribe("test.event", handler)

    result = event_bus.unsubscribe("test.event", handler)

    assert result is True
    assert event_bus.get_subscriber_count("test.event") == 0


def test_unsubscribe_nonexistent_handler(event_bus):
    """Test unsubscribing handler that doesn't exist returns False"""
    handler = Mock()
    result = event_bus.unsubscribe("test.event", handler)

    assert result is False


# Category 2: Publish Sync/Async Tests

@pytest.mark.asyncio
async def test_publish_async_calls_handler(event_bus, sample_event):
    """Test async publish calls subscribed handler"""
    handler = AsyncMock()
    event_bus.subscribe("test.event", handler)

    await event_bus.publish_async(sample_event)

    # Wait for async execution
    await asyncio.sleep(0.01)

    handler.assert_called_once()
    called_event = handler.call_args[0][0]
    assert called_event.event_type == "test.event"
    assert called_event.payload == {"key": "value"}


@pytest.mark.asyncio
async def test_publish_sync_creates_async_task(event_bus, sample_event):
    """Test sync publish creates async task (doesn't block)"""
    handler = AsyncMock()
    event_bus.subscribe("test.event", handler)

    # Sync publish should not block
    event_bus.publish(sample_event)

    # Wait for async task to complete
    await asyncio.sleep(0.01)

    handler.assert_called_once()


@pytest.mark.asyncio
async def test_publish_no_subscribers(event_bus, sample_event):
    """Test publishing event with no subscribers (should not error)"""
    # Should not raise exception
    await event_bus.publish_async(sample_event)


@pytest.mark.asyncio
async def test_publish_sync_handler(event_bus, sample_event):
    """Test publishing to synchronous handler"""
    handler = Mock()
    event_bus.subscribe("test.event", handler)

    await event_bus.publish_async(sample_event)

    # Wait for executor to run sync handler
    await asyncio.sleep(0.01)

    handler.assert_called_once()


# Category 3: Multiple Subscribers Tests

@pytest.mark.asyncio
async def test_multiple_subscribers_all_called(event_bus, sample_event):
    """Test all subscribers are called when event published"""
    handler1 = AsyncMock()
    handler2 = AsyncMock()
    handler3 = AsyncMock()

    event_bus.subscribe("test.event", handler1)
    event_bus.subscribe("test.event", handler2)
    event_bus.subscribe("test.event", handler3)

    await event_bus.publish_async(sample_event)
    await asyncio.sleep(0.01)

    handler1.assert_called_once()
    handler2.assert_called_once()
    handler3.assert_called_once()


@pytest.mark.asyncio
async def test_different_event_types_isolated(event_bus):
    """Test handlers only called for their subscribed event type"""
    handler_a = AsyncMock()
    handler_b = AsyncMock()

    event_bus.subscribe("event.a", handler_a)
    event_bus.subscribe("event.b", handler_b)

    event_a = Event(
        event_type="event.a",
        timestamp=datetime.utcnow(),
        payload={},
        trace_id="trace-1",
        session_id="session-1"
    )

    await event_bus.publish_async(event_a)
    await asyncio.sleep(0.01)

    handler_a.assert_called_once()
    handler_b.assert_not_called()


@pytest.mark.asyncio
async def test_subscriber_can_unsubscribe_during_execution(event_bus):
    """Test unsubscribing while events are being processed"""
    handler = AsyncMock()
    event_bus.subscribe("test.event", handler)

    event = Event(
        event_type="test.event",
        timestamp=datetime.utcnow(),
        payload={},
        trace_id="trace-1",
        session_id="session-1"
    )

    # Publish first event
    await event_bus.publish_async(event)
    await asyncio.sleep(0.01)

    # Unsubscribe
    event_bus.unsubscribe("test.event", handler)

    # Publish second event
    await event_bus.publish_async(event)
    await asyncio.sleep(0.01)

    # Should only be called once (from first event)
    assert handler.call_count == 1


# Category 4: Event Ordering Tests

@pytest.mark.asyncio
async def test_event_ordering_preserved_in_session(event_bus):
    """Test events are processed in order for same session"""
    call_order = []

    async def handler(event: Event):
        call_order.append(event.payload["sequence"])
        await asyncio.sleep(0.001)  # Small delay to test ordering

    event_bus.subscribe("test.event", handler)

    # Publish 5 events in sequence
    for i in range(5):
        event = Event(
            event_type="test.event",
            timestamp=datetime.utcnow(),
            payload={"sequence": i},
            trace_id=f"trace-{i}",
            session_id="session-1"
        )
        await event_bus.publish_async(event)

    await asyncio.sleep(0.1)

    # Should be processed in order
    assert call_order == [0, 1, 2, 3, 4]


@pytest.mark.asyncio
async def test_concurrent_events_all_processed(event_bus):
    """Test concurrent events all get processed"""
    processed_events = []

    async def handler(event: Event):
        processed_events.append(event.trace_id)

    event_bus.subscribe("test.event", handler)

    # Publish 10 events concurrently
    tasks = []
    for i in range(10):
        event = Event(
            event_type="test.event",
            timestamp=datetime.utcnow(),
            payload={},
            trace_id=f"trace-{i}",
            session_id=f"session-{i}"
        )
        tasks.append(event_bus.publish_async(event))

    await asyncio.gather(*tasks)
    await asyncio.sleep(0.1)

    # All 10 should be processed
    assert len(processed_events) == 10


# Category 5: Error Propagation Tests

@pytest.mark.asyncio
async def test_handler_error_isolated(event_bus, sample_event):
    """Test error in one handler doesn't affect others"""
    async def failing_handler(event: Event):
        raise Exception("Handler error")

    successful_handler = AsyncMock()

    event_bus.subscribe("test.event", failing_handler)
    event_bus.subscribe("test.event", successful_handler)

    # Should not raise exception
    await event_bus.publish_async(sample_event)
    await asyncio.sleep(0.01)

    # Successful handler should still be called
    successful_handler.assert_called_once()

    # Error count should be incremented
    stats = event_bus.get_stats()
    assert stats["total_handler_errors"] == 1


@pytest.mark.asyncio
async def test_sync_handler_error_isolated(event_bus, sample_event):
    """Test error in sync handler is caught"""
    def failing_handler(event: Event):
        raise Exception("Sync handler error")

    successful_handler = Mock()

    event_bus.subscribe("test.event", failing_handler)
    event_bus.subscribe("test.event", successful_handler)

    await event_bus.publish_async(sample_event)
    await asyncio.sleep(0.01)

    # Successful handler should still be called
    successful_handler.assert_called_once()


@pytest.mark.asyncio
async def test_invalid_event_validation(event_bus):
    """Test event validation catches invalid events"""
    with pytest.raises(ValueError, match="event_type cannot be empty"):
        Event(
            event_type="",
            timestamp=datetime.utcnow(),
            payload={},
            trace_id="trace-1",
            session_id="session-1"
        )

    with pytest.raises(ValueError, match="session_id cannot be empty"):
        Event(
            event_type="test.event",
            timestamp=datetime.utcnow(),
            payload={},
            trace_id="trace-1",
            session_id=""
        )


# Category 6: Performance Tests

@pytest.mark.asyncio
async def test_dispatch_latency_under_5ms(event_bus):
    """Test event dispatch completes in <5ms"""
    handler = AsyncMock()
    event_bus.subscribe("test.event", handler)

    event = Event(
        event_type="test.event",
        timestamp=datetime.utcnow(),
        payload={},
        trace_id="trace-1",
        session_id="session-1"
    )

    start = datetime.utcnow()
    await event_bus.publish_async(event)
    duration_ms = (datetime.utcnow() - start).total_seconds() * 1000

    assert duration_ms < 5, f"Dispatch took {duration_ms:.2f}ms (target: <5ms)"


@pytest.mark.asyncio
async def test_high_throughput_10k_events(event_bus):
    """Test event bus can handle 10,000 events/sec"""
    handler = AsyncMock()
    event_bus.subscribe("test.event", handler)

    event = Event(
        event_type="test.event",
        timestamp=datetime.utcnow(),
        payload={},
        trace_id="trace-1",
        session_id="session-1"
    )

    # Publish 10,000 events
    start = datetime.utcnow()
    tasks = [event_bus.publish_async(event) for _ in range(10000)]
    await asyncio.gather(*tasks)
    duration_sec = (datetime.utcnow() - start).total_seconds()

    throughput = 10000 / duration_sec

    assert throughput >= 10000, f"Throughput: {throughput:.0f} events/sec (target: 10,000+)"


# Utility Tests

def test_get_stats(event_bus):
    """Test get_stats returns correct statistics"""
    handler = Mock()
    event_bus.subscribe("test.event", handler)
    event_bus.subscribe("test.event", handler)
    event_bus.subscribe("other.event", handler)

    stats = event_bus.get_stats()

    assert "total_events_published" in stats
    assert "total_handler_errors" in stats
    assert "error_rate" in stats
    assert stats["subscriber_counts"]["test.event"] == 2
    assert stats["subscriber_counts"]["other.event"] == 1


def test_clear_all_subscribers(event_bus):
    """Test clearing all subscribers"""
    handler = Mock()
    event_bus.subscribe("test.event", handler)
    event_bus.subscribe("other.event", handler)

    event_bus.clear_all_subscribers()

    assert event_bus.get_subscriber_count("test.event") == 0
    assert event_bus.get_subscriber_count("other.event") == 0


def test_global_event_bus_singleton():
    """Test global event bus is singleton"""
    reset_event_bus()

    bus1 = get_event_bus()
    bus2 = get_event_bus()

    assert bus1 is bus2


# EventHandler Base Class Tests

class TestEventHandler(EventHandler):
    """Test implementation of EventHandler"""

    def __init__(self):
        self.events_handled = []

    async def handle(self, event: Event):
        self.events_handled.append(event)


@pytest.mark.asyncio
async def test_event_handler_base_class(event_bus, sample_event):
    """Test EventHandler base class can be subclassed"""
    handler = TestEventHandler()
    event_bus.subscribe("test.event", handler.handle)

    await event_bus.publish_async(sample_event)
    await asyncio.sleep(0.01)

    assert len(handler.events_handled) == 1
    assert handler.events_handled[0].event_type == "test.event"


# Edge Cases

@pytest.mark.asyncio
async def test_event_immutability(event_bus):
    """Test events are immutable (frozen dataclass)"""
    event = Event(
        event_type="test.event",
        timestamp=datetime.utcnow(),
        payload={},
        trace_id="trace-1",
        session_id="session-1"
    )

    with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
        event.event_type = "modified"


@pytest.mark.asyncio
async def test_large_payload_handling(event_bus):
    """Test event bus handles large payloads"""
    large_payload = {"data": "x" * 100000}  # 100KB payload
    event = Event(
        event_type="test.event",
        timestamp=datetime.utcnow(),
        payload=large_payload,
        trace_id="trace-1",
        session_id="session-1"
    )

    handler = AsyncMock()
    event_bus.subscribe("test.event", handler)

    # Should handle large payload without error
    await event_bus.publish_async(event)
    await asyncio.sleep(0.01)

    handler.assert_called_once()
    assert handler.call_args[0][0].payload == large_payload
