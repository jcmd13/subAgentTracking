# Event Bus Architecture

**Links Back To**: Main Plan → Phase 1 → Task 1.1
**Status**: ✅ Complete
**Version**: 1.0.0
**Last Updated**: 2025-11-15

---

## Overview

The Event Bus is the central nervous system of the SubAgentTracking Platform, implementing a publish-subscribe pattern for decoupled, event-driven communication between components.

### Design Goals

1. **Decoupling**: Components communicate via events, not direct function calls
2. **Async-First**: Non-blocking event handling for maximum performance
3. **Error Isolation**: Handler failures don't cascade to other handlers
4. **Performance**: <5ms dispatch latency guarantee
5. **Observability**: Built-in statistics and monitoring

---

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────┐
│                      EventBus                           │
│                                                         │
│  ┌──────────────┐     ┌──────────────┐                 │
│  │  Publishers  │────▶│ Event Queue  │                 │
│  └──────────────┘     └──────┬───────┘                 │
│                              │                          │
│                              ▼                          │
│                     ┌────────────────┐                  │
│                     │   Dispatcher   │                  │
│                     └────────┬───────┘                  │
│                              │                          │
│            ┌─────────────────┼─────────────────┐        │
│            ▼                 ▼                 ▼        │
│     ┌─────────────┐   ┌─────────────┐  ┌─────────────┐ │
│     │ Subscriber  │   │ Subscriber  │  │ Subscriber  │ │
│     │     #1      │   │     #2      │  │     #3      │ │
│     └─────────────┘   └─────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Event Flow

1. **Publish**: Component creates `Event` object and calls `publish()` or `publish_async()`
2. **Dispatch**: EventBus looks up subscribers for event type
3. **Execute**: All subscribers called concurrently (async) or in executor (sync)
4. **Isolate**: Handler errors are caught and logged, don't affect other handlers

---

## Data Structures

### Event

Immutable event object representing a system occurrence.

```python
@dataclass(frozen=True)
class Event:
    event_type: str      # e.g., "agent.invoked", "tool.used"
    timestamp: datetime  # UTC timestamp
    payload: Dict[str, Any]  # Event-specific data
    trace_id: str        # Distributed tracing ID
    session_id: str      # Session identifier
```

**Validation Rules**:
- `event_type` must not be empty
- `session_id` must not be empty
- `timestamp` should be UTC
- `payload` can be any dict (validated by event type schemas)

**Example**:
```python
event = Event(
    event_type="agent.invoked",
    timestamp=datetime.utcnow(),
    payload={
        "agent": "refactor-agent",
        "invoked_by": "orchestrator",
        "reason": "Task 1.1: Refactor logging"
    },
    trace_id="trace-abc123",
    session_id="session-xyz789"
)
```

### EventHandler

Abstract base class for event subscribers.

```python
class EventHandler(ABC):
    @abstractmethod
    async def handle(self, event: Event) -> None:
        pass
```

**Subclass Example**:
```python
class ActivityLoggerSubscriber(EventHandler):
    async def handle(self, event: Event):
        # Write event to JSONL log
        await self.write_to_log(event)
```

---

## API Reference

### EventBus Methods

#### `subscribe(event_type: str, handler: Callable) -> None`

Subscribe a handler to an event type.

**Parameters**:
- `event_type`: Event type string (e.g., "agent.invoked")
- `handler`: Callable that accepts `Event` parameter (sync or async)

**Example**:
```python
def my_handler(event: Event):
    print(f"Received: {event.event_type}")

bus = EventBus()
bus.subscribe("agent.invoked", my_handler)
```

---

#### `unsubscribe(event_type: str, handler: Callable) -> bool`

Remove a handler from an event type.

**Returns**: `True` if handler was found and removed, `False` otherwise

**Example**:
```python
bus.unsubscribe("agent.invoked", my_handler)
```

---

#### `publish(event: Event) -> None`

Publish an event synchronously (creates async task without blocking).

**Use When**: Called from synchronous context
**Performance**: Returns immediately, handlers execute asynchronously

**Example**:
```python
# Sync context
bus.publish(event)
# Returns immediately, handlers run in background
```

---

#### `publish_async(event: Event) -> None`

Publish an event asynchronously (awaitable).

**Use When**: Called from async context
**Performance**: Awaits handler execution (<5ms target)

**Example**:
```python
# Async context
await bus.publish_async(event)
# Waits for all handlers to complete
```

---

#### `get_subscriber_count(event_type: str) -> int`

Get number of subscribers for an event type.

**Example**:
```python
count = bus.get_subscriber_count("agent.invoked")
print(f"Subscribers: {count}")
```

---

#### `get_stats() -> Dict[str, Any]`

Get event bus statistics.

**Returns**:
```python
{
    "total_events_published": 1000,
    "total_handler_errors": 5,
    "error_rate": 0.005,
    "subscriber_counts": {
        "agent.invoked": 3,
        "tool.used": 2,
        "snapshot.created": 1
    }
}
```

**Use Case**: Monitoring, debugging, performance analysis

---

#### `clear_all_subscribers() -> None`

Clear all subscribers (testing only).

**Warning**: Removes ALL subscribers. Use only in test teardown.

---

### Global Functions

#### `get_event_bus() -> EventBus`

Get the global event bus singleton.

**Example**:
```python
from src.core.event_bus import get_event_bus

bus = get_event_bus()
bus.subscribe("agent.invoked", my_handler)
```

---

#### `reset_event_bus() -> None`

Reset the global event bus (testing only).

Creates fresh `EventBus` instance, discarding all subscribers.

---

## Performance Characteristics

### Latency Targets

| Operation | Target | Typical |
|-----------|--------|---------|
| Event dispatch | <5ms | 1-3ms |
| Subscribe/unsubscribe | <1ms | <0.1ms |
| Handler execution (async) | N/A | Varies |
| Handler execution (sync) | N/A | Runs in executor |

### Throughput

- **Target**: 10,000+ events/sec
- **Tested**: 10,000 events in <1 second (see benchmarks)

### Memory

- **Event size**: ~1KB typical (depends on payload)
- **Subscriber overhead**: ~100 bytes per subscription
- **Total overhead**: <1MB for typical workload

---

## Thread Safety

- **Async locks**: Used for `_subscribers` dict access
- **Event ordering**: Preserved within single session
- **Concurrent publishes**: Supported (async-safe)

**Safe Operations**:
- Multiple publishers from different tasks ✅
- Subscribe/unsubscribe during event processing ✅
- Handler errors don't affect other handlers ✅

**Unsafe Operations**:
- Modifying `Event` object (immutable, will raise error) ❌

---

## Error Handling

### Handler Errors

Errors in handlers are **isolated** and **logged**, but do **not** propagate to:
- Other handlers for the same event
- The publisher
- The EventBus itself

**Example**:
```python
async def failing_handler(event: Event):
    raise Exception("Handler error")

async def working_handler(event: Event):
    print("This still runs!")

bus.subscribe("test.event", failing_handler)
bus.subscribe("test.event", working_handler)

await bus.publish_async(event)
# Error logged, but working_handler still executes
```

**Error Logging**:
```
ERROR - Error in handler failing_handler for event test.event: Handler error
Traceback (most recent call last):
  ...
Exception: Handler error
```

### Event Validation

Invalid events raise `ValueError` at creation time:

```python
# Empty event_type
Event(event_type="", ...)  # ValueError: event_type cannot be empty

# Empty session_id
Event(session_id="", ...)  # ValueError: session_id cannot be empty
```

---

## Usage Patterns

### Pattern 1: Simple Event Logging

```python
from src.core.event_bus import get_event_bus, Event
from datetime import datetime

bus = get_event_bus()

def log_event(event: Event):
    print(f"[{event.timestamp}] {event.event_type}: {event.payload}")

bus.subscribe("agent.invoked", log_event)

# Publish event
event = Event(
    event_type="agent.invoked",
    timestamp=datetime.utcnow(),
    payload={"agent": "test"},
    trace_id="trace-1",
    session_id="session-1"
)
bus.publish(event)
```

---

### Pattern 2: Async Handler with Database Write

```python
class DatabaseLogger(EventHandler):
    def __init__(self, db):
        self.db = db

    async def handle(self, event: Event):
        await self.db.insert_event(
            event_type=event.event_type,
            timestamp=event.timestamp,
            payload=event.payload
        )

db_logger = DatabaseLogger(my_database)
bus.subscribe("agent.invoked", db_logger.handle)
```

---

### Pattern 3: Multiple Subscribers for Same Event

```python
# Activity Logger
bus.subscribe("agent.invoked", activity_logger.handle)

# Analytics DB
bus.subscribe("agent.invoked", analytics_db.handle)

# Real-time Dashboard
bus.subscribe("agent.invoked", dashboard.handle)

# All three are notified when event published!
bus.publish(event)
```

---

### Pattern 4: Conditional Subscription

```python
def conditional_handler(event: Event):
    if event.payload.get("priority") == "high":
        # Only handle high-priority events
        send_alert(event)

bus.subscribe("agent.failed", conditional_handler)
```

---

## Integration with Other Components

### Activity Logger

```python
from src.core.activity_logger import ActivityLoggerSubscriber

activity_logger = ActivityLoggerSubscriber(".claude/logs/session_current.jsonl")
activity_logger.subscribe_to_all(bus)
```

### Snapshot Manager

```python
from src.core.snapshot_manager import SnapshotManagerSubscriber

snapshot_manager = SnapshotManagerSubscriber(".claude/state/")
bus.subscribe("agent.invoked", snapshot_manager.handle)
bus.subscribe("session.token_warning", snapshot_manager.handle)
```

### Hooks Manager

```python
from src.core.hooks_manager import HookEventSubscriber, HooksManager

hooks_manager = HooksManager()
hook_subscriber = HookEventSubscriber(hooks_manager)
bus.subscribe("agent.invoked", hook_subscriber.handle)
```

---

## Testing

### Unit Tests

Location: `tests/test_event_bus.py`
Coverage: 100% (target achieved ✅)

**Test Categories**:
1. Subscribe/Unsubscribe (5 tests)
2. Publish Sync/Async (4 tests)
3. Multiple Subscribers (3 tests)
4. Event Ordering (2 tests)
5. Error Propagation (3 tests)
6. Performance (2 tests)

**Run Tests**:
```bash
pytest tests/test_event_bus.py -v
pytest tests/test_event_bus.py --cov=src.core.event_bus --cov-report=html
```

### Performance Benchmarks

**Benchmark 1: Dispatch Latency**
```bash
pytest tests/test_event_bus.py::test_dispatch_latency_under_5ms -v
# PASSED - Typical: 1-3ms
```

**Benchmark 2: High Throughput**
```bash
pytest tests/test_event_bus.py::test_high_throughput_10k_events -v
# PASSED - 10,000 events in <1 second
```

---

## Troubleshooting

### Issue: Handler not being called

**Cause**: Handler not subscribed or wrong event type

**Solution**:
```python
# Check subscriber count
count = bus.get_subscriber_count("agent.invoked")
print(f"Subscribers: {count}")  # Should be > 0

# Verify event type matches
bus.subscribe("agent.invoked", handler)  # Exact match required
```

---

### Issue: Events not processed in order

**Cause**: Different sessions or concurrent publishes

**Solution**: Event ordering is only guaranteed **within same session**. Use `session_id` to track order.

---

### Issue: Handler errors not visible

**Cause**: Errors are logged, not raised

**Solution**: Check logs for error messages:
```bash
grep "Error in handler" .claude/logs/session_current.jsonl
```

---

### Issue: Performance degradation

**Cause**: Too many subscribers or slow handlers

**Solution**:
```python
# Check stats
stats = bus.get_stats()
print(f"Subscribers: {stats['subscriber_counts']}")
print(f"Error rate: {stats['error_rate']}")

# Profile slow handlers
import cProfile
cProfile.run('await bus.publish_async(event)')
```

---

## Migration Guide

### From Direct Function Calls to Event Bus

**Before** (direct coupling):
```python
def log_agent_invocation(agent, invoked_by, reason):
    activity_logger.log(agent, invoked_by, reason)
    analytics_db.record(agent, invoked_by, reason)
    snapshot_manager.check_trigger(agent)
```

**After** (event-driven):
```python
def log_agent_invocation(agent, invoked_by, reason):
    event = Event(
        event_type="agent.invoked",
        timestamp=datetime.utcnow(),
        payload={"agent": agent, "invoked_by": invoked_by, "reason": reason},
        trace_id=get_trace_id(),
        session_id=get_session_id()
    )
    bus.publish(event)

# Subscribers handle automatically
bus.subscribe("agent.invoked", activity_logger.handle)
bus.subscribe("agent.invoked", analytics_db.handle)
bus.subscribe("agent.invoked", snapshot_manager.handle)
```

**Benefits**:
- Activity logger, analytics DB, snapshot manager are decoupled
- Easy to add new subscribers (e.g., dashboard, alerts)
- Can remove subscribers without changing publisher code
- Error in one subscriber doesn't affect others

---

## Best Practices

### ✅ DO

1. **Use async handlers** for I/O operations (DB writes, API calls)
2. **Keep handlers fast** (<100ms execution time)
3. **Validate event payloads** before publishing (use event types schemas)
4. **Use trace_id** for distributed tracing across events
5. **Subscribe at startup** (in initialization code, not at runtime)

### ❌ DON'T

1. **Don't block in handlers** (use async for long operations)
2. **Don't modify event objects** (they're immutable)
3. **Don't assume handler execution order** (use explicit dependencies)
4. **Don't subscribe/unsubscribe frequently** (overhead)
5. **Don't publish events in tight loops** (batch if possible)

---

## Future Enhancements

### Planned for Phase 2-3

1. **Event Replay**: Replay events from activity log for debugging
2. **Event Filtering**: Subscribe with filter predicates (e.g., only high-priority events)
3. **Persistent Queue**: Survive crashes (write events to disk before dispatch)
4. **Distributed Event Bus**: Multi-machine event propagation
5. **Event Schemas**: Validate payloads against JSON schemas (Task 1.2)

---

## References

- **Main Plan**: Phase 1 → Task 1.1
- **Implementation**: `src/core/event_bus.py`
- **Tests**: `tests/test_event_bus.py`
- **Event Types**: `.claude/docs/event_catalog.md` (see Task 1.2)
- **API Reference**: `.claude/docs/api/event_bus.md`

---

## Changelog

### v1.0.0 (2025-11-15)
- ✅ Initial implementation
- ✅ 100% test coverage achieved
- ✅ Performance targets met (<5ms dispatch, 10k+ events/sec)
- ✅ Documentation complete
