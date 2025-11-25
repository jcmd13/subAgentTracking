"""
Dashboard Integration Example

Demonstrates how to set up and use the real-time observability dashboard.

Links Back To: Main Plan → Phase 3 → Task 3.2

Usage:
    python examples/dashboard_example.py
"""

import asyncio
import logging
from datetime import datetime

from src.core.event_bus import Event, get_event_bus
from src.core.event_types import (
    AGENT_INVOKED, AGENT_COMPLETED, TOOL_USED,
    WORKFLOW_STARTED, WORKFLOW_COMPLETED
)
from src.observability import (
    initialize_observability,
    shutdown_observability,
    get_observability_stats
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def simulate_agent_workflow():
    """Simulate a multi-agent workflow with events."""

    event_bus = get_event_bus()

    # Workflow started
    await event_bus.publish(Event(
        event_type=WORKFLOW_STARTED,
        timestamp=datetime.utcnow(),
        payload={
            "workflow_id": "wf-demo-001",
            "task_count": 3
        },
        trace_id="demo-trace-001",
        session_id="demo-session-001"
    ))

    # Simulate 3 agents executing in sequence
    agents = [
        {"name": "config-architect", "duration": 150, "tokens": 1500},
        {"name": "refactor-agent", "duration": 200, "tokens": 2000},
        {"name": "test-engineer", "duration": 180, "tokens": 1800}
    ]

    for i, agent_data in enumerate(agents):
        # Agent invoked
        await event_bus.publish(Event(
            event_type=AGENT_INVOKED,
            timestamp=datetime.utcnow(),
            payload={
                "agent": {
                    "name": agent_data["name"],
                    "id": f"agent-{i+1}"
                },
                "invoked_by": "orchestrator",
                "reason": f"Task {i+1}: Implement feature"
            },
            trace_id="demo-trace-001",
            session_id="demo-session-001"
        ))

        # Simulate work (tool usage)
        await asyncio.sleep(0.5)

        await event_bus.publish(Event(
            event_type=TOOL_USED,
            timestamp=datetime.utcnow(),
            payload={
                "agent": agent_data["name"],
                "tool": "Write",
                "details": {"file": f"src/{agent_data['name']}.py"}
            },
            trace_id="demo-trace-001",
            session_id="demo-session-001"
        ))

        # Agent completed
        await asyncio.sleep(0.5)

        await event_bus.publish(Event(
            event_type=AGENT_COMPLETED,
            timestamp=datetime.utcnow(),
            payload={
                "agent": {
                    "name": agent_data["name"],
                    "id": f"agent-{i+1}"
                },
                "duration_ms": agent_data["duration"],
                "tokens": agent_data["tokens"],
                "cost": agent_data["tokens"] * 0.00003  # ~$0.03 per 1k tokens
            },
            trace_id="demo-trace-001",
            session_id="demo-session-001"
        ))

    # Workflow completed
    await event_bus.publish(Event(
        event_type=WORKFLOW_COMPLETED,
        timestamp=datetime.utcnow(),
        payload={
            "workflow_id": "wf-demo-001",
            "total_duration_ms": 530
        },
        trace_id="demo-trace-001",
        session_id="demo-session-001"
    ))


async def run_continuous_simulation(duration_seconds: int = 60):
    """
    Run continuous agent workflow simulation.

    Args:
        duration_seconds: How long to run simulation (default: 60 seconds)
    """
    logger.info(f"Running simulation for {duration_seconds} seconds...")

    start_time = asyncio.get_event_loop().time()

    while (asyncio.get_event_loop().time() - start_time) < duration_seconds:
        await simulate_agent_workflow()
        await asyncio.sleep(2)  # Wait 2 seconds between workflows

    logger.info("Simulation complete")


async def main():
    """Main dashboard example."""

    print("\n" + "="*70)
    print("SubAgent Tracking Dashboard - Demo")
    print("="*70)

    # Initialize observability platform with dashboard
    print("\n1. Initializing observability platform...")
    components = initialize_observability(
        websocket_host="localhost",
        websocket_port=8765,
        dashboard_port=8080,
        start_dashboard=True,  # Auto-start dashboard server
        auto_subscribe=True    # Auto-subscribe to event bus
    )

    print(f"\n   Dashboard URL: http://localhost:8080")
    print(f"   WebSocket URL: ws://localhost:8765")
    print(f"\n   Open http://localhost:8080 in your browser to view dashboard")

    # Start WebSocket server
    print("\n2. Starting WebSocket server...")
    monitor = components['monitor']
    await monitor.start()
    print(f"   WebSocket server running on ws://localhost:8765")

    # Run simulation
    print("\n3. Starting agent workflow simulation...")
    print("   Simulating multi-agent workflows for 60 seconds...")
    print("   Watch the dashboard for real-time updates!\n")

    try:
        # Run simulation
        await run_continuous_simulation(duration_seconds=60)

        # Get final statistics
        print("\n4. Final Statistics:")
        stats = get_observability_stats()

        if stats['monitor']:
            print(f"\n   Monitor:")
            print(f"   - Active connections: {stats['monitor']['active_connections']}")
            print(f"   - Total events streamed: {stats['monitor']['total_events_streamed']}")

        if stats['metrics']['cumulative']:
            cumulative = stats['metrics']['cumulative']
            print(f"\n   Metrics (All-Time):")
            print(f"   - Total events: {cumulative['total_events']}")
            print(f"   - Total tokens: {cumulative['total_tokens']}")
            print(f"   - Total cost: ${cumulative['total_cost']:.4f}")
            print(f"   - Active agents: {cumulative['active_agents']}")
            print(f"   - Active workflows: {cumulative['active_workflows']}")

        if '300' in stats['metrics']['windows']:
            window_5min = stats['metrics']['windows']['300']
            print(f"\n   Metrics (5-Minute Window):")
            print(f"   - Events/sec: {window_5min['events_per_second']:.2f}")
            print(f"   - Agents/min: {window_5min['agents_per_minute']:.2f}")
            print(f"   - Avg duration: {window_5min['avg_agent_duration_ms']:.0f}ms")
            print(f"   - P95 duration: {window_5min['p95_agent_duration_ms']:.0f}ms")

    except KeyboardInterrupt:
        print("\n\nSimulation interrupted by user")

    finally:
        # Cleanup
        print("\n5. Shutting down...")
        await monitor.stop()
        shutdown_observability()
        print("   All components shut down")

    print("\n" + "="*70)
    print("Dashboard demo complete!")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
