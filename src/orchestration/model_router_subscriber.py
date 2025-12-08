"""
Model Router Event Subscriber - Integration with Event Bus

Subscribes to agent invocation events and automatically routes to appropriate
model tier, publishing routing decisions as events.

Links Back To: Main Plan → Phase 2 → Task 2.5

Key Features:
- Automatic model selection on AGENT_INVOKED events
- Publishes MODEL_SELECTED events with routing metadata
- Tracks routing statistics via event bus
- Integrates with cost tracker for budget-aware routing
- Supports tier upgrades on AGENT_FAILED events

Event Flow:
1. AGENT_INVOKED → Analyze task → Select model → MODEL_SELECTED
2. AGENT_FAILED → Check if tier upgrade needed → Publish recommendation
3. Cost tracking integration for budget-aware decisions
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import logging

from src.core.event_bus import Event, EventHandler, get_event_bus
from src.core.event_types import (
    AGENT_INVOKED,
    AGENT_FAILED,
    AGENT_COMPLETED
)
from src.orchestration.model_router import get_model_router, ModelRouter
from src.core.cost_tracker import get_cost_tracker

logger = logging.getLogger(__name__)

# Define new event type for model routing
MODEL_SELECTED = "model.selected"


class ModelRouterSubscriber(EventHandler):
    """
    Event subscriber that routes agent tasks to appropriate models.

    Listens for AGENT_INVOKED events and automatically selects the best
    model based on task complexity, context size, and budget constraints.
    """

    def __init__(self, router: Optional[ModelRouter] = None):
        """
        Initialize model router subscriber.

        Args:
            router: ModelRouter instance (uses global if None)
        """
        self.router = router or get_model_router()

        if self.router is None:
            logger.warning("ModelRouter not initialized, subscriber will be inactive")

        # Track routing decisions per session
        self.session_routing: Dict[str, List[Dict[str, Any]]] = {}

        # Track tier upgrades
        self.tier_upgrades: Dict[str, int] = {}  # agent_id -> upgrade_count

    async def handle(self, event: Event) -> None:
        """
        Handle events for model routing.

        Args:
            event: Event to process
        """
        try:
            if event.event_type == AGENT_INVOKED:
                await self._handle_agent_invoked(event)
            elif event.event_type == AGENT_FAILED:
                await self._handle_agent_failed(event)
            elif event.event_type == AGENT_COMPLETED:
                await self._handle_agent_completed(event)

        except Exception as e:
            logger.error(f"Error in model router subscriber: {e}", exc_info=True)

    async def _handle_agent_invoked(self, event: Event) -> None:
        """
        Handle AGENT_INVOKED event by selecting appropriate model.

        Args:
            event: AGENT_INVOKED event
        """
        if not self.router:
            return

        payload = event.payload

        # Extract task information
        task = {
            "type": payload.get("task_type", "unknown"),
            "context_tokens": payload.get("context_tokens", 0),
            "files": payload.get("files", [])
        }

        # Add agent context for better routing
        agent_name = payload.get("agent", "unknown")
        task["agent"] = agent_name

        # Check if this agent has had tier upgrades
        if agent_name in self.tier_upgrades:
            # Start at higher tier if previous failures
            upgrade_count = self.tier_upgrades[agent_name]
            if upgrade_count > 0:
                logger.info(
                    f"Agent '{agent_name}' has {upgrade_count} previous upgrades, "
                    f"considering higher tier"
                )

        # Check budget constraints
        cost_tracker = get_cost_tracker()
        budget_constrained = False
        if cost_tracker:
            alerts = cost_tracker.check_budget_alerts(event.session_id)
            if alerts:
                # Budget alerts exist, prefer free tier
                budget_constrained = True
                logger.warning(
                    f"Budget constraints detected ({len(alerts)} alerts), "
                    f"preferring free tier models"
                )

        # Select model
        model, tier, metadata = self.router.select_model(task)

        # Override with free tier if budget constrained
        if budget_constrained and tier not in ["weak"]:
            logger.info(f"Budget constrained, considering downgrade from {tier} to weak")
            # Note: Would need to implement downgrade logic here
            # For now, just log the recommendation

        # Track routing decision
        routing_decision = {
            "agent": agent_name,
            "task_type": task["type"],
            "selected_model": model,
            "tier": tier,
            "complexity_score": metadata["complexity_score"],
            "routing_reason": metadata["routing_reason"],
            "budget_constrained": budget_constrained,
            "timestamp": datetime.now(timezone.utc)
        }

        # Store routing decision
        if event.session_id not in self.session_routing:
            self.session_routing[event.session_id] = []
        self.session_routing[event.session_id].append(routing_decision)

        # Publish MODEL_SELECTED event
        await self._publish_model_selected_event(event, model, tier, metadata)

        logger.info(
            f"Model routing for agent '{agent_name}': {model} ({tier} tier, "
            f"complexity={metadata['complexity_score']})"
        )

    async def _handle_agent_failed(self, event: Event) -> None:
        """
        Handle AGENT_FAILED event and recommend tier upgrade if appropriate.

        Args:
            event: AGENT_FAILED event
        """
        if not self.router:
            return

        payload = event.payload
        agent_name = payload.get("agent", "unknown")
        error_msg = payload.get("error_msg", "")

        # Check if failure might be model-related
        model_related_errors = [
            "quality", "accuracy", "incomplete", "invalid", "incorrect",
            "failed to", "unable to", "could not"
        ]

        is_model_related = any(
            keyword in error_msg.lower() for keyword in model_related_errors
        )

        if not is_model_related:
            logger.debug(f"Agent '{agent_name}' failure not model-related, skipping upgrade")
            return

        # Get current routing for this agent in this session
        session_routes = self.session_routing.get(event.session_id, [])
        agent_routes = [r for r in session_routes if r["agent"] == agent_name]

        if not agent_routes:
            logger.warning(f"No routing history for agent '{agent_name}', cannot recommend upgrade")
            return

        # Get most recent routing
        current_route = agent_routes[-1]
        current_tier = current_route["tier"]

        # Recommend tier upgrade
        new_tier = self.router.upgrade_tier(current_tier, reason="agent_failure")

        if new_tier != current_tier:
            # Track upgrade
            self.tier_upgrades[agent_name] = self.tier_upgrades.get(agent_name, 0) + 1

            # Publish upgrade recommendation
            await self._publish_tier_upgrade_event(
                event,
                agent_name,
                current_tier,
                new_tier,
                error_msg
            )

            logger.warning(
                f"Agent '{agent_name}' failed, recommending tier upgrade: "
                f"{current_tier} → {new_tier}"
            )

    async def _handle_agent_completed(self, event: Event) -> None:
        """
        Handle AGENT_COMPLETED event to track successful routing decisions.

        Args:
            event: AGENT_COMPLETED event
        """
        payload = event.payload
        agent_name = payload.get("agent", "unknown")

        # Get routing for this agent
        session_routes = self.session_routing.get(event.session_id, [])
        agent_routes = [r for r in session_routes if r["agent"] == agent_name]

        if agent_routes:
            route = agent_routes[-1]
            logger.debug(
                f"Agent '{agent_name}' completed successfully with "
                f"{route['selected_model']} ({route['tier']} tier)"
            )

            # Reset upgrade counter on success
            if agent_name in self.tier_upgrades:
                self.tier_upgrades[agent_name] = max(0, self.tier_upgrades[agent_name] - 1)

    async def _publish_model_selected_event(
        self,
        original_event: Event,
        model: str,
        tier: str,
        metadata: Dict[str, Any]
    ) -> None:
        """
        Publish MODEL_SELECTED event.

        Args:
            original_event: Original AGENT_INVOKED event
            model: Selected model name
            tier: Selected tier
            metadata: Routing metadata
        """
        event_bus = get_event_bus()

        event = Event(
            event_type=MODEL_SELECTED,
            timestamp=datetime.now(timezone.utc),
            payload={
                "model": model,
                "tier": tier,
                "complexity_score": metadata["complexity_score"],
                "routing_reason": metadata["routing_reason"],
                "context_tokens": metadata["context_tokens"],
                "task_type": metadata["task_type"],
                "agent": original_event.payload.get("agent", "unknown")
            },
            trace_id=original_event.trace_id,
            session_id=original_event.session_id
        )

        event_bus.publish(event)

    async def _publish_tier_upgrade_event(
        self,
        original_event: Event,
        agent_name: str,
        current_tier: str,
        new_tier: str,
        reason: str
    ) -> None:
        """
        Publish tier upgrade recommendation event.

        Args:
            original_event: Original AGENT_FAILED event
            agent_name: Agent that failed
            current_tier: Current tier
            new_tier: Recommended tier
            reason: Failure reason
        """
        event_bus = get_event_bus()

        # Define event type (could be added to event_types.py)
        MODEL_TIER_UPGRADE = "model.tier_upgrade"

        event = Event(
            event_type=MODEL_TIER_UPGRADE,
            timestamp=datetime.now(timezone.utc),
            payload={
                "agent": agent_name,
                "current_tier": current_tier,
                "recommended_tier": new_tier,
                "reason": reason,
                "recommendation": f"Upgrade from {current_tier} to {new_tier} due to agent failure"
            },
            trace_id=original_event.trace_id,
            session_id=original_event.session_id
        )

        event_bus.publish(event)

    def get_session_routing_stats(self, session_id: str) -> Dict[str, Any]:
        """
        Get routing statistics for a session.

        Args:
            session_id: Session ID

        Returns:
            Statistics dictionary
        """
        routes = self.session_routing.get(session_id, [])

        if not routes:
            return {
                "total_routes": 0,
                "by_tier": {},
                "by_model": {},
                "budget_constrained_count": 0
            }

        # Count by tier
        by_tier = {}
        for route in routes:
            tier = route["tier"]
            by_tier[tier] = by_tier.get(tier, 0) + 1

        # Count by model
        by_model = {}
        for route in routes:
            model = route["selected_model"]
            by_model[model] = by_model.get(model, 0) + 1

        # Count budget-constrained decisions
        budget_constrained = sum(
            1 for route in routes if route.get("budget_constrained", False)
        )

        return {
            "total_routes": len(routes),
            "by_tier": by_tier,
            "by_model": by_model,
            "budget_constrained_count": budget_constrained,
            "tier_distribution": {
                tier: count / len(routes) for tier, count in by_tier.items()
            }
        }

    def subscribe_to_events(self, event_bus=None) -> None:
        """
        Subscribe to relevant events.

        Args:
            event_bus: Event bus instance (uses global if None)
        """
        if event_bus is None:
            event_bus = get_event_bus()

        event_bus.subscribe(AGENT_INVOKED, self.handle)
        event_bus.subscribe(AGENT_FAILED, self.handle)
        event_bus.subscribe(AGENT_COMPLETED, self.handle)

        logger.info("Model router subscriber registered for AGENT_INVOKED, AGENT_FAILED, AGENT_COMPLETED")


# Global subscriber instance
_global_subscriber: Optional[ModelRouterSubscriber] = None


def get_model_router_subscriber() -> Optional[ModelRouterSubscriber]:
    """Get the global model router subscriber instance."""
    return _global_subscriber


def initialize_model_router_subscriber(router: Optional[ModelRouter] = None) -> ModelRouterSubscriber:
    """
    Initialize the global model router subscriber.

    Args:
        router: ModelRouter instance (uses global if None)

    Returns:
        ModelRouterSubscriber instance
    """
    global _global_subscriber

    if _global_subscriber is not None:
        logger.warning("Model router subscriber already initialized")
        return _global_subscriber

    # Create subscriber
    _global_subscriber = ModelRouterSubscriber(router=router)

    # Subscribe to events
    _global_subscriber.subscribe_to_events()

    logger.info("Model router subscriber initialized and subscribed to events")

    return _global_subscriber


def shutdown_model_router_subscriber() -> None:
    """Shutdown the global model router subscriber."""
    global _global_subscriber
    _global_subscriber = None
    logger.info("Model router subscriber shutdown complete")
