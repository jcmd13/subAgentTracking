"""
Tests for Model Router Event Subscriber

Tests cover:
- Event subscription and handling
- Automatic model selection on AGENT_INVOKED
- Tier upgrade recommendations on AGENT_FAILED
- Integration with cost tracker
- Session routing statistics
- Event publishing (MODEL_SELECTED, tier upgrades)

Links Back To: Main Plan → Phase 2 → Task 2.5
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock

from src.orchestration.model_router_subscriber import (
    ModelRouterSubscriber,
    MODEL_SELECTED,
    initialize_model_router_subscriber,
    get_model_router_subscriber,
    shutdown_model_router_subscriber
)
from src.orchestration.model_router import ModelRouter
from src.core.event_bus import Event, EventBus
from src.core.event_types import AGENT_INVOKED, AGENT_FAILED, AGENT_COMPLETED


@pytest.fixture
def mock_router():
    """Create mock router for testing."""
    router = Mock(spec=ModelRouter)

    # Default routing behavior
    router.select_model.return_value = (
        "claude-sonnet-4",  # model
        "base",  # tier
        {
            "complexity_score": 5,
            "routing_reason": "Standard task → base tier",
            "context_tokens": 10000,
            "task_type": "code_implementation"
        }
    )

    router.upgrade_tier.return_value = "strong"

    return router


@pytest.fixture
def event_bus():
    """Create fresh event bus for testing."""
    return EventBus()


@pytest.fixture
def subscriber(mock_router):
    """Create subscriber with mock router."""
    return ModelRouterSubscriber(router=mock_router)


# ============================================================================
# Subscription Tests
# ============================================================================

class TestSubscription:
    """Test suite for event subscription."""

    def test_subscribe_to_events(self, subscriber, event_bus):
        """Should subscribe to relevant events."""
        subscriber.subscribe_to_events(event_bus)

        # Check subscriptions
        assert AGENT_INVOKED in event_bus._subscribers
        assert AGENT_FAILED in event_bus._subscribers
        assert AGENT_COMPLETED in event_bus._subscribers


# ============================================================================
# Model Selection Tests
# ============================================================================

class TestModelSelection:
    """Test suite for automatic model selection."""

    @pytest.mark.asyncio
    async def test_handle_agent_invoked_selects_model(self, subscriber, mock_router, event_bus):
        """Should select model on AGENT_INVOKED event."""
        event = Event(
            event_type=AGENT_INVOKED,
            timestamp=datetime.utcnow(),
            payload={
                "agent": "test-agent",
                "task_type": "code_implementation",
                "context_tokens": 15000,
                "files": ["src/main.py"]
            },
            trace_id="trace-123",
            session_id="session-456"
        )

        await subscriber.handle(event)

        # Should call select_model
        mock_router.select_model.assert_called_once()
        call_args = mock_router.select_model.call_args[0][0]
        assert call_args["type"] == "code_implementation"
        assert call_args["context_tokens"] == 15000
        assert call_args["files"] == ["src/main.py"]

    @pytest.mark.asyncio
    async def test_handle_agent_invoked_publishes_event(self, subscriber, mock_router):
        """Should publish MODEL_SELECTED event."""
        # Create event bus and patch global
        from src.orchestration import model_router_subscriber
        event_bus = EventBus()

        # Track published events
        events_published = []
        original_publish = event_bus.publish

        def capture_publish(event):
            events_published.append(event)
            return original_publish(event)

        event_bus.publish = capture_publish

        # Patch get_event_bus to return our event bus
        with patch.object(model_router_subscriber, 'get_event_bus', return_value=event_bus):
            # Create AGENT_INVOKED event
            event = Event(
                event_type=AGENT_INVOKED,
                timestamp=datetime.utcnow(),
                payload={
                    "agent": "test-agent",
                    "task_type": "code_implementation",
                    "context_tokens": 15000,
                    "files": []
                },
                trace_id="trace-123",
                session_id="session-456"
            )

            # Handle event
            await subscriber.handle(event)

        # Should have published MODEL_SELECTED
        model_selected_events = [e for e in events_published if e.event_type == MODEL_SELECTED]
        assert len(model_selected_events) == 1
        selected_event = model_selected_events[0]
        assert selected_event.payload["model"] == "claude-sonnet-4"
        assert selected_event.payload["tier"] == "base"

    @pytest.mark.asyncio
    async def test_routing_decision_stored(self, subscriber, mock_router):
        """Should store routing decisions."""
        event = Event(
            event_type=AGENT_INVOKED,
            timestamp=datetime.utcnow(),
            payload={
                "agent": "test-agent",
                "task_type": "code_implementation",
                "context_tokens": 15000,
                "files": []
            },
            trace_id="trace-123",
            session_id="session-456"
        )

        await subscriber.handle(event)

        # Should have stored routing decision
        assert "session-456" in subscriber.session_routing
        routes = subscriber.session_routing["session-456"]
        assert len(routes) == 1
        assert routes[0]["agent"] == "test-agent"
        assert routes[0]["selected_model"] == "claude-sonnet-4"


# ============================================================================
# Tier Upgrade Tests
# ============================================================================

class TestTierUpgrade:
    """Test suite for tier upgrade recommendations."""

    @pytest.mark.asyncio
    async def test_handle_agent_failed_recommends_upgrade(self, subscriber, mock_router, event_bus):
        """Should recommend tier upgrade on model-related failure."""
        # First, establish routing history
        invoked_event = Event(
            event_type=AGENT_INVOKED,
            timestamp=datetime.utcnow(),
            payload={
                "agent": "test-agent",
                "task_type": "code_implementation",
                "context_tokens": 15000,
                "files": []
            },
            trace_id="trace-123",
            session_id="session-456"
        )
        await subscriber.handle(invoked_event)

        # Then fail with model-related error
        failed_event = Event(
            event_type=AGENT_FAILED,
            timestamp=datetime.utcnow(),
            payload={
                "agent": "test-agent",
                "error_msg": "Failed to generate correct code, quality issue"
            },
            trace_id="trace-123",
            session_id="session-456"
        )

        await subscriber.handle(failed_event)

        # Should call upgrade_tier
        mock_router.upgrade_tier.assert_called_once_with("base", reason="agent_failure")

    @pytest.mark.asyncio
    async def test_non_model_related_failure_no_upgrade(self, subscriber, mock_router):
        """Should not recommend upgrade for non-model-related failures."""
        # Establish routing history
        invoked_event = Event(
            event_type=AGENT_INVOKED,
            timestamp=datetime.utcnow(),
            payload={
                "agent": "test-agent",
                "task_type": "code_implementation",
                "context_tokens": 15000,
                "files": []
            },
            trace_id="trace-123",
            session_id="session-456"
        )
        await subscriber.handle(invoked_event)

        # Fail with non-model error
        failed_event = Event(
            event_type=AGENT_FAILED,
            timestamp=datetime.utcnow(),
            payload={
                "agent": "test-agent",
                "error_msg": "Network timeout error"
            },
            trace_id="trace-123",
            session_id="session-456"
        )

        # Reset mock
        mock_router.upgrade_tier.reset_mock()

        await subscriber.handle(failed_event)

        # Should NOT call upgrade_tier
        mock_router.upgrade_tier.assert_not_called()

    @pytest.mark.asyncio
    async def test_tier_upgrade_tracked(self, subscriber, mock_router):
        """Should track tier upgrades per agent."""
        # Invoke and fail multiple times
        for i in range(3):
            invoked = Event(
                event_type=AGENT_INVOKED,
                timestamp=datetime.utcnow(),
                payload={
                    "agent": "test-agent",
                    "task_type": "code_implementation",
                    "context_tokens": 15000,
                    "files": []
                },
                trace_id=f"trace-{i}",
                session_id="session-456"
            )
            await subscriber.handle(invoked)

            failed = Event(
                event_type=AGENT_FAILED,
                timestamp=datetime.utcnow(),
                payload={
                    "agent": "test-agent",
                    "error_msg": "Quality issue detected"
                },
                trace_id=f"trace-{i}",
                session_id="session-456"
            )
            await subscriber.handle(failed)

        # Should have tracked upgrades
        assert "test-agent" in subscriber.tier_upgrades
        assert subscriber.tier_upgrades["test-agent"] == 3


# ============================================================================
# Agent Completion Tests
# ============================================================================

class TestAgentCompletion:
    """Test suite for agent completion handling."""

    @pytest.mark.asyncio
    async def test_handle_agent_completed_resets_upgrades(self, subscriber, mock_router):
        """Should reset upgrade counter on successful completion."""
        # Invoke agent
        invoked = Event(
            event_type=AGENT_INVOKED,
            timestamp=datetime.utcnow(),
            payload={
                "agent": "test-agent",
                "task_type": "code_implementation",
                "context_tokens": 15000,
                "files": []
            },
            trace_id="trace-123",
            session_id="session-456"
        )
        await subscriber.handle(invoked)

        # Set upgrade counter
        subscriber.tier_upgrades["test-agent"] = 2

        # Complete successfully
        completed = Event(
            event_type=AGENT_COMPLETED,
            timestamp=datetime.utcnow(),
            payload={
                "agent": "test-agent",
                "result": {}
            },
            trace_id="trace-123",
            session_id="session-456"
        )
        await subscriber.handle(completed)

        # Should have decremented upgrade counter
        assert subscriber.tier_upgrades["test-agent"] == 1


# ============================================================================
# Budget Integration Tests
# ============================================================================

class TestBudgetIntegration:
    """Test suite for cost tracker integration."""

    @pytest.mark.asyncio
    @patch('src.orchestration.model_router_subscriber.get_cost_tracker')
    async def test_budget_constrained_routing(self, mock_get_tracker, subscriber, mock_router):
        """Should detect budget constraints and prefer free tier."""
        # Mock cost tracker with budget alerts
        mock_tracker = Mock()
        mock_tracker.check_budget_alerts.return_value = [
            {"budget_type": "daily", "percent": 90}
        ]
        mock_get_tracker.return_value = mock_tracker

        event = Event(
            event_type=AGENT_INVOKED,
            timestamp=datetime.utcnow(),
            payload={
                "agent": "test-agent",
                "task_type": "code_implementation",
                "context_tokens": 15000,
                "files": []
            },
            trace_id="trace-123",
            session_id="session-456"
        )

        await subscriber.handle(event)

        # Should have detected budget constraint
        routes = subscriber.session_routing["session-456"]
        assert routes[0]["budget_constrained"] is True


# ============================================================================
# Statistics Tests
# ============================================================================

class TestStatistics:
    """Test suite for routing statistics."""

    @pytest.mark.asyncio
    async def test_get_session_routing_stats(self, subscriber, mock_router):
        """Should return routing statistics for session."""
        # Route multiple tasks
        for i in range(5):
            event = Event(
                event_type=AGENT_INVOKED,
                timestamp=datetime.utcnow(),
                payload={
                    "agent": f"agent-{i}",
                    "task_type": "code_implementation",
                    "context_tokens": 15000,
                    "files": []
                },
                trace_id=f"trace-{i}",
                session_id="session-456"
            )
            await subscriber.handle(event)

        stats = subscriber.get_session_routing_stats("session-456")

        assert stats["total_routes"] == 5
        assert "by_tier" in stats
        assert "by_model" in stats
        assert "tier_distribution" in stats

    def test_get_stats_empty_session(self, subscriber):
        """Should handle empty session stats."""
        stats = subscriber.get_session_routing_stats("nonexistent")

        assert stats["total_routes"] == 0
        assert stats["by_tier"] == {}
        assert stats["by_model"] == {}


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests with real components."""

    @pytest.mark.asyncio
    async def test_full_workflow_invoke_route_complete(self, subscriber, mock_router, event_bus):
        """Should handle full workflow: invoke → route → complete."""
        subscriber.subscribe_to_events(event_bus)

        # Invoke agent
        invoked = Event(
            event_type=AGENT_INVOKED,
            timestamp=datetime.utcnow(),
            payload={
                "agent": "test-agent",
                "task_type": "code_implementation",
                "context_tokens": 15000,
                "files": []
            },
            trace_id="trace-123",
            session_id="session-456"
        )
        event_bus.publish(invoked)
        await asyncio.sleep(0.01)

        # Complete agent
        completed = Event(
            event_type=AGENT_COMPLETED,
            timestamp=datetime.utcnow(),
            payload={
                "agent": "test-agent",
                "result": {}
            },
            trace_id="trace-123",
            session_id="session-456"
        )
        event_bus.publish(completed)
        await asyncio.sleep(0.01)

        # Check routing history
        stats = subscriber.get_session_routing_stats("session-456")
        assert stats["total_routes"] == 1

    @pytest.mark.asyncio
    async def test_full_workflow_invoke_route_fail_upgrade(self, subscriber, mock_router, event_bus):
        """Should handle workflow: invoke → route → fail → upgrade."""
        subscriber.subscribe_to_events(event_bus)

        # Invoke agent
        invoked = Event(
            event_type=AGENT_INVOKED,
            timestamp=datetime.utcnow(),
            payload={
                "agent": "test-agent",
                "task_type": "code_implementation",
                "context_tokens": 15000,
                "files": []
            },
            trace_id="trace-123",
            session_id="session-456"
        )
        event_bus.publish(invoked)
        await asyncio.sleep(0.01)

        # Fail agent
        failed = Event(
            event_type=AGENT_FAILED,
            timestamp=datetime.utcnow(),
            payload={
                "agent": "test-agent",
                "error_msg": "Quality issue detected"
            },
            trace_id="trace-123",
            session_id="session-456"
        )
        event_bus.publish(failed)
        await asyncio.sleep(0.01)

        # Should have called upgrade_tier
        mock_router.upgrade_tier.assert_called()


# ============================================================================
# Global Instance Tests
# ============================================================================

class TestGlobalSubscriber:
    """Test suite for global subscriber instance."""

    def test_initialize_global_subscriber(self, mock_router):
        """Should initialize global subscriber."""
        shutdown_model_router_subscriber()

        subscriber = initialize_model_router_subscriber(router=mock_router)
        assert subscriber is not None
        assert get_model_router_subscriber() is subscriber

        shutdown_model_router_subscriber()

    def test_initialize_twice_warns(self, mock_router):
        """Initializing twice should warn but return existing."""
        shutdown_model_router_subscriber()

        sub1 = initialize_model_router_subscriber(router=mock_router)
        sub2 = initialize_model_router_subscriber(router=mock_router)

        assert sub1 is sub2

        shutdown_model_router_subscriber()

    def test_shutdown_clears_global(self, mock_router):
        """Shutdown should clear global instance."""
        shutdown_model_router_subscriber()

        initialize_model_router_subscriber(router=mock_router)
        assert get_model_router_subscriber() is not None

        shutdown_model_router_subscriber()
        assert get_model_router_subscriber() is None


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test suite for edge cases."""

    @pytest.mark.asyncio
    async def test_handle_event_without_router(self):
        """Should handle events gracefully without router."""
        subscriber = ModelRouterSubscriber(router=None)

        event = Event(
            event_type=AGENT_INVOKED,
            timestamp=datetime.utcnow(),
            payload={
                "agent": "test-agent",
                "task_type": "code_implementation",
                "context_tokens": 15000,
                "files": []
            },
            trace_id="trace-123",
            session_id="session-456"
        )

        # Should not crash
        await subscriber.handle(event)

    @pytest.mark.asyncio
    async def test_handle_agent_failed_without_routing_history(self, subscriber, mock_router):
        """Should handle AGENT_FAILED without prior routing history."""
        failed = Event(
            event_type=AGENT_FAILED,
            timestamp=datetime.utcnow(),
            payload={
                "agent": "unknown-agent",
                "error_msg": "Quality issue"
            },
            trace_id="trace-123",
            session_id="session-456"
        )

        # Should not crash
        await subscriber.handle(failed)

    @pytest.mark.asyncio
    async def test_handle_unknown_event_type(self, subscriber):
        """Should handle unknown event types gracefully."""
        event = Event(
            event_type="unknown.event",
            timestamp=datetime.utcnow(),
            payload={},
            trace_id="trace-123",
            session_id="session-456"
        )

        # Should not crash
        await subscriber.handle(event)
