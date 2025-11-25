"""
Tests for Metrics Aggregator

Tests real-time metrics aggregation with rolling windows.

Links Back To: Main Plan → Phase 3 → Task 3.1
"""

import pytest
import time
from datetime import datetime
from unittest.mock import Mock, patch

from src.core.event_bus import Event, EventBus
from src.core.event_types import (
    AGENT_INVOKED, AGENT_COMPLETED, AGENT_FAILED,
    TOOL_USED, WORKFLOW_STARTED, WORKFLOW_COMPLETED
)

from src.observability.metrics_aggregator import (
    MetricsAggregator,
    WindowSize,
    EventRecord,
    MetricsSnapshot,
    initialize_metrics_aggregator,
    get_metrics_aggregator,
    shutdown_metrics_aggregator
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def aggregator():
    """Create metrics aggregator for testing."""
    agg = MetricsAggregator(
        window_sizes=[60, 300],  # 1min, 5min
        max_records=1000,
        auto_subscribe=False
    )
    yield agg
    shutdown_metrics_aggregator()


@pytest.fixture
def sample_event():
    """Create sample event for testing."""
    return Event(
        event_type=AGENT_INVOKED,
        payload={
            "agent": {"name": "test-agent", "id": "agent-1"},
            "invoked_by": "user",
            "reason": "test",
            "duration_ms": 150.0,
            "tokens": 1000,
            "cost": 0.05
        }
    )


# ============================================================================
# EventRecord Tests
# ============================================================================

class TestEventRecord:
    """Test event record data structure."""

    def test_event_record_creation(self):
        """Should create event record with all fields."""
        record = EventRecord(
            timestamp=time.time(),
            event_type=AGENT_INVOKED,
            agent="test-agent",
            duration_ms=100.0,
            tokens=500,
            cost=0.02,
            success=True
        )

        assert record.event_type == AGENT_INVOKED
        assert record.agent == "test-agent"
        assert record.duration_ms == 100.0
        assert record.tokens == 500
        assert record.cost == 0.02
        assert record.success is True


# ============================================================================
# MetricsAggregator Tests
# ============================================================================

class TestMetricsAggregator:
    """Test metrics aggregator functionality."""

    def test_initialization(self, aggregator):
        """Should initialize with correct parameters."""
        assert len(aggregator.window_sizes) == 2
        assert 60 in aggregator.window_sizes
        assert 300 in aggregator.window_sizes
        assert aggregator.max_records == 1000
        assert aggregator.cumulative_events == 0

    def test_record_single_event(self, aggregator, sample_event):
        """Should record single event."""
        aggregator.record_event(sample_event)

        assert aggregator.cumulative_events == 1
        assert aggregator.cumulative_tokens == 1000
        assert aggregator.cumulative_cost == 0.05

        # Check that event was added to all windows
        for window in aggregator.windows.values():
            assert len(window) == 1

    def test_record_multiple_events(self, aggregator):
        """Should record multiple events."""
        for i in range(10):
            event = Event(
                event_type=AGENT_INVOKED,
                payload={
                    "agent": {"name": f"agent-{i}"},
                    "tokens": 100 * i
                }
            )
            aggregator.record_event(event)

        assert aggregator.cumulative_events == 10
        assert aggregator.cumulative_tokens == sum(100 * i for i in range(10))

    def test_event_to_record_conversion(self, aggregator, sample_event):
        """Should convert Event to EventRecord correctly."""
        record = aggregator._event_to_record(sample_event)

        assert record.event_type == AGENT_INVOKED
        assert record.agent == "test-agent"
        assert record.duration_ms == 150.0
        assert record.tokens == 1000
        assert record.cost == 0.05
        assert record.success is True

    def test_event_to_record_failed_event(self, aggregator):
        """Should mark failed events as not successful."""
        event = Event(
            event_type=AGENT_FAILED,
            payload={"agent": {"name": "failed-agent"}}
        )

        record = aggregator._event_to_record(event)

        assert record.success is False

    def test_workflow_tracking(self, aggregator):
        """Should track active workflows."""
        # Start workflow
        start_event = Event(
            event_type=WORKFLOW_STARTED,
            payload={"workflow_id": "wf-1", "task_count": 3}
        )
        aggregator.record_event(start_event)

        assert "wf-1" in aggregator.active_workflows
        assert len(aggregator.active_workflows) == 1

        # Complete workflow
        complete_event = Event(
            event_type=WORKFLOW_COMPLETED,
            payload={"workflow_id": "wf-1"}
        )
        aggregator.record_event(complete_event)

        assert "wf-1" not in aggregator.active_workflows
        assert len(aggregator.active_workflows) == 0

    def test_agent_tracking(self, aggregator):
        """Should track active agents."""
        # Invoke agent
        invoke_event = Event(
            event_type=AGENT_INVOKED,
            payload={"agent": {"name": "agent-1", "id": "agent-1"}}
        )
        aggregator.record_event(invoke_event)

        assert "agent-1" in aggregator.active_agents
        assert len(aggregator.active_agents) == 1

        # Complete agent
        complete_event = Event(
            event_type=AGENT_COMPLETED,
            payload={"agent": {"name": "agent-1", "id": "agent-1"}}
        )
        aggregator.record_event(complete_event)

        assert "agent-1" not in aggregator.active_agents
        assert len(aggregator.active_agents) == 0

    def test_get_current_stats_empty(self, aggregator):
        """Should return empty stats with no events."""
        stats = aggregator.get_current_stats(window_size=60)

        assert isinstance(stats, MetricsSnapshot)
        assert stats.total_events == 0
        assert stats.agents_active == 0
        assert stats.total_tokens == 0

    def test_get_current_stats_with_events(self, aggregator):
        """Should return stats with recorded events."""
        # Record some events
        for i in range(5):
            event = Event(
                event_type=AGENT_INVOKED,
                payload={
                    "agent": {"name": f"agent-{i}"},
                    "tokens": 100,
                    "duration_ms": 50.0 + i * 10
                }
            )
            aggregator.record_event(event)

        stats = aggregator.get_current_stats(window_size=60)

        assert stats.total_events == 5
        assert stats.total_tokens == 500
        assert stats.events_per_second > 0
        assert stats.avg_agent_duration_ms > 0

    def test_get_current_stats_different_windows(self, aggregator):
        """Should compute stats for different windows."""
        # Record events
        for i in range(10):
            event = Event(
                event_type=AGENT_INVOKED,
                payload={"agent": {"name": f"agent-{i}"}}
            )
            aggregator.record_event(event)

        # Get stats for both windows
        stats_60 = aggregator.get_current_stats(window_size=60)
        stats_300 = aggregator.get_current_stats(window_size=300)

        # Both should have same events (within same time)
        assert stats_60.total_events == stats_300.total_events
        # But different rates
        assert stats_60.events_per_second == stats_300.events_per_second * 5

    def test_percentile_calculation(self, aggregator):
        """Should calculate percentiles correctly."""
        values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]

        p50 = aggregator._percentile(values, 50)
        p95 = aggregator._percentile(values, 95)
        p99 = aggregator._percentile(values, 99)

        assert p50 == 50.0
        assert p95 >= 90.0
        assert p99 >= 95.0

    def test_percentile_empty_list(self, aggregator):
        """Should handle empty list gracefully."""
        p50 = aggregator._percentile([], 50)

        assert p50 == 0.0

    def test_get_all_stats(self, aggregator):
        """Should return stats for all windows."""
        # Record event
        event = Event(
            event_type=AGENT_INVOKED,
            payload={"agent": {"name": "test"}}
        )
        aggregator.record_event(event)

        all_stats = aggregator.get_all_stats()

        assert 60 in all_stats
        assert 300 in all_stats
        assert isinstance(all_stats[60], MetricsSnapshot)
        assert isinstance(all_stats[300], MetricsSnapshot)

    def test_get_cumulative_stats(self, aggregator):
        """Should return cumulative statistics."""
        # Record multiple events
        for i in range(20):
            event = Event(
                event_type=AGENT_INVOKED,
                payload={
                    "agent": {"name": f"agent-{i}"},
                    "tokens": 50
                }
            )
            aggregator.record_event(event)

        cumulative = aggregator.get_cumulative_stats()

        assert cumulative["total_events"] == 20
        assert cumulative["total_tokens"] == 1000
        assert cumulative["events_per_second"] > 0
        assert cumulative["window_sizes"] == [60, 300]
        assert cumulative["max_records"] == 1000

    def test_clear(self, aggregator):
        """Should clear all recorded events."""
        # Record events
        for i in range(10):
            event = Event(
                event_type=AGENT_INVOKED,
                payload={"agent": {"name": f"agent-{i}"}}
            )
            aggregator.record_event(event)

        assert aggregator.cumulative_events == 10

        # Clear
        aggregator.clear()

        assert aggregator.cumulative_events == 0
        assert len(aggregator.active_workflows) == 0
        assert len(aggregator.active_agents) == 0

        for window in aggregator.windows.values():
            assert len(window) == 0

    def test_max_records_limit(self, aggregator):
        """Should respect max_records limit."""
        # Record more than max_records
        for i in range(1500):
            event = Event(
                event_type=AGENT_INVOKED,
                payload={"agent": {"name": f"agent-{i}"}}
            )
            aggregator.record_event(event)

        # Windows should not exceed max_records
        for window in aggregator.windows.values():
            assert len(window) <= aggregator.max_records

    @pytest.mark.asyncio
    async def test_handle_event_async(self, aggregator, sample_event):
        """Should handle events asynchronously."""
        await aggregator.handle(sample_event)

        assert aggregator.cumulative_events == 1


# ============================================================================
# Global Instance Management Tests
# ============================================================================

class TestGlobalInstance:
    """Test global instance management."""

    def test_initialize_creates_instance(self):
        """Should create global instance."""
        shutdown_metrics_aggregator()

        agg = initialize_metrics_aggregator(
            window_sizes=[60],
            max_records=500
        )

        assert agg is not None
        assert get_metrics_aggregator() is agg
        assert agg.window_sizes == [60]
        assert agg.max_records == 500

        shutdown_metrics_aggregator()

    def test_initialize_twice_returns_existing(self):
        """Should return existing instance on second initialization."""
        shutdown_metrics_aggregator()

        agg1 = initialize_metrics_aggregator(window_sizes=[60])
        agg2 = initialize_metrics_aggregator(window_sizes=[300])

        # Should be same instance
        assert agg1 is agg2
        # Should keep first config
        assert agg1.window_sizes == [60]

        shutdown_metrics_aggregator()

    def test_shutdown_clears_instance(self):
        """Should clear global instance on shutdown."""
        initialize_metrics_aggregator()

        shutdown_metrics_aggregator()

        assert get_metrics_aggregator() is None


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Test performance characteristics."""

    def test_recording_performance(self, aggregator):
        """Should record events with <10ms overhead."""
        start = time.time()

        # Record 100 events
        for i in range(100):
            event = Event(
                event_type=AGENT_INVOKED,
                payload={"agent": {"name": f"agent-{i}"}}
            )
            aggregator.record_event(event)

        duration = time.time() - start

        # Should be fast (<1s for 100 events = <10ms per event)
        assert duration < 1.0

        # Average should be well under 10ms
        avg_ms = (duration / 100) * 1000
        assert avg_ms < 10.0

    def test_stats_query_performance(self, aggregator):
        """Should query stats with <5ms latency."""
        # Record some events
        for i in range(100):
            event = Event(
                event_type=AGENT_INVOKED,
                payload={"agent": {"name": f"agent-{i}"}}
            )
            aggregator.record_event(event)

        # Measure query time
        start = time.time()
        stats = aggregator.get_current_stats()
        duration = (time.time() - start) * 1000  # Convert to ms

        # Should be very fast
        assert duration < 5.0
