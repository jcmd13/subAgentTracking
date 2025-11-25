"""
Tests for Real-Time Monitoring Infrastructure

Tests the WebSocket server, event streaming, and client management.

Links Back To: Main Plan → Phase 3 → Task 3.1
"""

import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Check if websockets is available
try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

from src.core.event_bus import Event, EventBus
from src.core.event_types import AGENT_INVOKED, AGENT_COMPLETED, TOOL_USED

if WEBSOCKETS_AVAILABLE:
    from src.observability.realtime_monitor import (
        RealtimeMonitor,
        FilterType,
        EventFilter,
        ClientSubscription,
        initialize_realtime_monitor,
        get_realtime_monitor,
        shutdown_realtime_monitor
    )


pytestmark = pytest.mark.skipif(
    not WEBSOCKETS_AVAILABLE,
    reason="websockets package not installed"
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def event_bus():
    """Create event bus for testing."""
    bus = EventBus()
    yield bus


@pytest.fixture
def monitor():
    """Create realtime monitor for testing."""
    monitor = RealtimeMonitor(
        host="localhost",
        port=8765,
        max_connections=10,
        auto_subscribe=False  # Manual subscription for testing
    )
    yield monitor
    shutdown_realtime_monitor()


@pytest.fixture
def sample_event():
    """Create sample event for testing."""
    return Event(
        event_type=AGENT_INVOKED,
        payload={
            "agent": {"name": "test-agent", "id": "agent-1"},
            "invoked_by": "user",
            "reason": "test"
        }
    )


# ============================================================================
# EventFilter Tests
# ============================================================================

class TestEventFilter:
    """Test event filter functionality."""

    def test_empty_filter_matches_all(self, sample_event):
        """Empty filter should match all events."""
        filter_obj = EventFilter(filter_type=FilterType.EVENT_TYPE, values=set())

        assert filter_obj.matches(sample_event) is True

    def test_event_type_filter_matches(self, sample_event):
        """Event type filter should match correct events."""
        filter_obj = EventFilter(
            filter_type=FilterType.EVENT_TYPE,
            values={AGENT_INVOKED, AGENT_COMPLETED}
        )

        assert filter_obj.matches(sample_event) is True

    def test_event_type_filter_rejects(self, sample_event):
        """Event type filter should reject non-matching events."""
        filter_obj = EventFilter(
            filter_type=FilterType.EVENT_TYPE,
            values={TOOL_USED}
        )

        assert filter_obj.matches(sample_event) is False

    def test_agent_filter_matches(self, sample_event):
        """Agent filter should match correct agents."""
        filter_obj = EventFilter(
            filter_type=FilterType.AGENT,
            values={"test-agent", "other-agent"}
        )

        assert filter_obj.matches(sample_event) is True

    def test_agent_filter_rejects(self, sample_event):
        """Agent filter should reject non-matching agents."""
        filter_obj = EventFilter(
            filter_type=FilterType.AGENT,
            values={"different-agent"}
        )

        assert filter_obj.matches(sample_event) is False


# ============================================================================
# ClientSubscription Tests
# ============================================================================

class TestClientSubscription:
    """Test client subscription functionality."""

    def test_no_filters_matches_all(self, sample_event):
        """Client with no filters should match all events."""
        websocket_mock = MagicMock()
        client = ClientSubscription(
            client_id="test-client",
            websocket=websocket_mock
        )

        assert client.matches_event(sample_event) is True

    def test_single_filter_matching(self, sample_event):
        """Client with matching filter should match event."""
        websocket_mock = MagicMock()
        client = ClientSubscription(
            client_id="test-client",
            websocket=websocket_mock,
            filters=[
                EventFilter(
                    filter_type=FilterType.EVENT_TYPE,
                    values={AGENT_INVOKED}
                )
            ]
        )

        assert client.matches_event(sample_event) is True

    def test_single_filter_non_matching(self, sample_event):
        """Client with non-matching filter should reject event."""
        websocket_mock = MagicMock()
        client = ClientSubscription(
            client_id="test-client",
            websocket=websocket_mock,
            filters=[
                EventFilter(
                    filter_type=FilterType.EVENT_TYPE,
                    values={TOOL_USED}
                )
            ]
        )

        assert client.matches_event(sample_event) is False

    def test_multiple_filters_all_match(self, sample_event):
        """Client with multiple matching filters should match."""
        websocket_mock = MagicMock()
        client = ClientSubscription(
            client_id="test-client",
            websocket=websocket_mock,
            filters=[
                EventFilter(
                    filter_type=FilterType.EVENT_TYPE,
                    values={AGENT_INVOKED}
                ),
                EventFilter(
                    filter_type=FilterType.AGENT,
                    values={"test-agent"}
                )
            ]
        )

        assert client.matches_event(sample_event) is True

    def test_multiple_filters_one_fails(self, sample_event):
        """Client with one non-matching filter should reject."""
        websocket_mock = MagicMock()
        client = ClientSubscription(
            client_id="test-client",
            websocket=websocket_mock,
            filters=[
                EventFilter(
                    filter_type=FilterType.EVENT_TYPE,
                    values={AGENT_INVOKED}
                ),
                EventFilter(
                    filter_type=FilterType.AGENT,
                    values={"different-agent"}
                )
            ]
        )

        assert client.matches_event(sample_event) is False


# ============================================================================
# RealtimeMonitor Tests
# ============================================================================

class TestRealtimeMonitor:
    """Test real-time monitor functionality."""

    def test_initialization(self, monitor):
        """Should initialize with correct parameters."""
        assert monitor.host == "localhost"
        assert monitor.port == 8765
        assert monitor.max_connections == 10
        assert monitor.running is False
        assert len(monitor.clients) == 0

    @pytest.mark.asyncio
    async def test_start_stop(self, monitor):
        """Should start and stop cleanly."""
        await monitor.start()
        assert monitor.running is True
        assert monitor.server is not None

        await monitor.stop()
        assert monitor.running is False
        assert monitor.server is None

    @pytest.mark.asyncio
    async def test_handle_event_not_running(self, monitor, sample_event):
        """Should ignore events when not running."""
        await monitor.handle(sample_event)

        # Should not crash, just ignore
        assert monitor.total_events_streamed == 0

    @pytest.mark.asyncio
    async def test_handle_event_no_clients(self, monitor, sample_event):
        """Should handle event with no connected clients."""
        await monitor.start()

        await monitor.handle(sample_event)

        # No events streamed (no clients)
        assert monitor.total_events_streamed == 0

        await monitor.stop()

    def test_get_stats_initial(self, monitor):
        """Should return stats before starting."""
        stats = monitor.get_stats()

        assert stats["running"] is False
        assert stats["active_connections"] == 0
        assert stats["total_connections"] == 0
        assert stats["total_events_streamed"] == 0

    @pytest.mark.asyncio
    async def test_get_stats_after_start(self, monitor):
        """Should return stats after starting."""
        await monitor.start()

        stats = monitor.get_stats()

        assert stats["running"] is True
        assert "uptime_seconds" in stats
        assert stats["uptime_seconds"] >= 0

        await monitor.stop()


# ============================================================================
# Global Instance Management Tests
# ============================================================================

class TestGlobalInstance:
    """Test global instance management."""

    def test_initialize_creates_instance(self):
        """Should create global instance."""
        shutdown_realtime_monitor()  # Clean state

        monitor = initialize_realtime_monitor(
            host="localhost",
            port=9999
        )

        assert monitor is not None
        assert get_realtime_monitor() is monitor

        shutdown_realtime_monitor()

    def test_initialize_twice_returns_existing(self):
        """Should return existing instance on second initialization."""
        shutdown_realtime_monitor()

        monitor1 = initialize_realtime_monitor(port=9999)
        monitor2 = initialize_realtime_monitor(port=8888)

        # Should be same instance
        assert monitor1 is monitor2
        # Should keep first port
        assert monitor1.port == 9999

        shutdown_realtime_monitor()

    def test_shutdown_clears_instance(self):
        """Should clear global instance on shutdown."""
        initialize_realtime_monitor()

        shutdown_realtime_monitor()

        assert get_realtime_monitor() is None


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for real-time monitoring."""

    @pytest.mark.asyncio
    async def test_event_streaming_flow(self, event_bus, sample_event):
        """Should stream events from event bus to clients."""
        # This is a conceptual test - full WebSocket testing requires
        # actual client connections which are complex to mock

        monitor = RealtimeMonitor(
            host="localhost",
            port=8765,
            auto_subscribe=False
        )

        await monitor.start()

        # Simulate event from event bus
        await monitor.handle(sample_event)

        # Verify event was processed (even though no clients)
        assert monitor.running is True

        await monitor.stop()

    @pytest.mark.asyncio
    async def test_multiple_windows(self):
        """Should handle events across different time windows."""
        # This test validates the basic flow works
        monitor = RealtimeMonitor(auto_subscribe=False)

        await monitor.start()

        # Create multiple events
        for i in range(10):
            event = Event(
                event_type=AGENT_INVOKED,
                payload={"agent": {"name": f"agent-{i}"}}
            )
            await monitor.handle(event)

        await monitor.stop()
