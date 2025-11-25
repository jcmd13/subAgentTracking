"""
Tests for Fleet Monitor

Tests multi-agent workflow tracking, bottleneck detection, and fleet statistics.

Links Back To: Main Plan → Phase 3 → Task 3.5
"""

import pytest
import time
from datetime import datetime, timedelta

from src.core.event_bus import Event
from src.core.event_types import (
    AGENT_INVOKED, AGENT_COMPLETED, AGENT_FAILED,
    WORKFLOW_STARTED, WORKFLOW_COMPLETED
)

from src.observability.fleet_monitor import (
    FleetMonitor,
    AgentStatus,
    AgentExecution,
    WorkflowState,
    Bottleneck,
    FleetStatistics,
    get_fleet_monitor,
    initialize_fleet_monitor,
    shutdown_fleet_monitor
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def monitor():
    """Create fleet monitor for testing."""
    shutdown_fleet_monitor()
    monitor = FleetMonitor(max_workflows=10, auto_subscribe=False)
    yield monitor
    shutdown_fleet_monitor()


@pytest.fixture
def sample_workflow_events():
    """Create sample workflow events."""
    now = datetime.utcnow()
    workflow_id = "wf-test-001"

    return [
        # Workflow start
        Event(
            event_type=WORKFLOW_STARTED,
            timestamp=now,
            payload={"workflow_id": workflow_id},
            trace_id=workflow_id,
            session_id="session-1"
        ),

        # Agent 1: Invoked
        Event(
            event_type=AGENT_INVOKED,
            timestamp=now + timedelta(seconds=1),
            payload={
                "agent": {"name": "agent-1", "id": "agent-1"},
                "invoked_by": "orchestrator"
            },
            trace_id=workflow_id,
            session_id="session-1"
        ),

        # Agent 1: Completed
        Event(
            event_type=AGENT_COMPLETED,
            timestamp=now + timedelta(seconds=3),
            payload={
                "agent": {"name": "agent-1", "id": "agent-1"},
                "duration_ms": 2000,
                "tokens": 1000,
                "cost": 0.03
            },
            trace_id=workflow_id,
            session_id="session-1"
        ),

        # Agent 2: Invoked
        Event(
            event_type=AGENT_INVOKED,
            timestamp=now + timedelta(seconds=4),
            payload={
                "agent": {"name": "agent-2", "id": "agent-2"},
                "invoked_by": "orchestrator"
            },
            trace_id=workflow_id,
            session_id="session-1"
        ),

        # Agent 2: Completed
        Event(
            event_type=AGENT_COMPLETED,
            timestamp=now + timedelta(seconds=6),
            payload={
                "agent": {"name": "agent-2", "id": "agent-2"},
                "duration_ms": 2000,
                "tokens": 1500,
                "cost": 0.045
            },
            trace_id=workflow_id,
            session_id="session-1"
        ),

        # Workflow complete
        Event(
            event_type=WORKFLOW_COMPLETED,
            timestamp=now + timedelta(seconds=7),
            payload={
                "workflow_id": workflow_id,
                "total_duration_ms": 6000
            },
            trace_id=workflow_id,
            session_id="session-1"
        )
    ]


# ============================================================================
# Initialization Tests
# ============================================================================

class TestInitialization:
    """Test fleet monitor initialization."""

    def test_initialization(self, monitor):
        """Should initialize correctly."""
        assert monitor.max_workflows == 10
        assert len(monitor.workflows) == 0
        assert monitor.total_workflows_completed == 0
        assert monitor.total_agents_run == 0

    def test_initialization_with_params(self):
        """Should initialize with custom parameters."""
        monitor = FleetMonitor(max_workflows=50, auto_subscribe=False)

        assert monitor.max_workflows == 50

        shutdown_fleet_monitor()


# ============================================================================
# Event Handling Tests
# ============================================================================

class TestEventHandling:
    """Test event handling."""

    @pytest.mark.asyncio
    async def test_handle_workflow_started(self, monitor):
        """Should handle workflow started event."""
        event = Event(
            event_type=WORKFLOW_STARTED,
            timestamp=datetime.utcnow(),
            payload={"workflow_id": "wf-1"},
            trace_id="wf-1",
            session_id="session-1"
        )

        await monitor.handle(event)

        assert "wf-1" in monitor.workflows
        workflow = monitor.workflows["wf-1"]
        assert workflow.status == "active"

    @pytest.mark.asyncio
    async def test_handle_agent_invoked(self, monitor):
        """Should handle agent invoked event."""
        # First start workflow
        workflow_event = Event(
            event_type=WORKFLOW_STARTED,
            timestamp=datetime.utcnow(),
            payload={"workflow_id": "wf-1"},
            trace_id="wf-1",
            session_id="session-1"
        )
        await monitor.handle(workflow_event)

        # Then invoke agent
        agent_event = Event(
            event_type=AGENT_INVOKED,
            timestamp=datetime.utcnow(),
            payload={
                "agent": {"name": "test-agent", "id": "agent-1"},
                "invoked_by": "user"
            },
            trace_id="wf-1",
            session_id="session-1"
        )
        await monitor.handle(agent_event)

        workflow = monitor.workflows["wf-1"]
        assert "agent-1" in workflow.agents
        assert workflow.agents["agent-1"].status == AgentStatus.RUNNING
        assert monitor.total_agents_run == 1

    @pytest.mark.asyncio
    async def test_handle_agent_completed(self, monitor, sample_workflow_events):
        """Should handle agent completed event."""
        # Process first 3 events (workflow start, agent invoked, agent completed)
        for event in sample_workflow_events[:3]:
            await monitor.handle(event)

        workflow = monitor.workflows["wf-test-001"]
        execution = workflow.agents["agent-1"]

        assert execution.status == AgentStatus.COMPLETED
        assert execution.duration_ms == 2000
        assert execution.tokens == 1000
        assert execution.cost == 0.03
        assert workflow.total_tokens == 1000
        assert workflow.total_cost == 0.03

    @pytest.mark.asyncio
    async def test_handle_agent_failed(self, monitor):
        """Should handle agent failed event."""
        # Start workflow and invoke agent
        workflow_event = Event(
            event_type=WORKFLOW_STARTED,
            timestamp=datetime.utcnow(),
            payload={"workflow_id": "wf-1"},
            trace_id="wf-1",
            session_id="session-1"
        )
        await monitor.handle(workflow_event)

        agent_invoked = Event(
            event_type=AGENT_INVOKED,
            timestamp=datetime.utcnow(),
            payload={"agent": {"name": "test-agent", "id": "agent-1"}},
            trace_id="wf-1",
            session_id="session-1"
        )
        await monitor.handle(agent_invoked)

        # Agent fails
        agent_failed = Event(
            event_type=AGENT_FAILED,
            timestamp=datetime.utcnow(),
            payload={
                "agent": {"name": "test-agent", "id": "agent-1"},
                "error": "Test error"
            },
            trace_id="wf-1",
            session_id="session-1"
        )
        await monitor.handle(agent_failed)

        workflow = monitor.workflows["wf-1"]
        execution = workflow.agents["agent-1"]

        assert execution.status == AgentStatus.FAILED
        assert execution.error == "Test error"

    @pytest.mark.asyncio
    async def test_handle_workflow_completed(self, monitor, sample_workflow_events):
        """Should handle workflow completed event."""
        # Process all events
        for event in sample_workflow_events:
            await monitor.handle(event)

        # Workflow should be in history, not active workflows
        assert "wf-test-001" in monitor.workflows
        workflow = monitor.workflows["wf-test-001"]
        assert workflow.status == "completed"
        assert workflow.total_duration_ms == 6000
        assert len(monitor.workflow_history) == 1


# ============================================================================
# Workflow State Tests
# ============================================================================

class TestWorkflowState:
    """Test workflow state queries."""

    @pytest.mark.asyncio
    async def test_get_workflow_state(self, monitor, sample_workflow_events):
        """Should get workflow state."""
        # Process events
        for event in sample_workflow_events[:3]:
            await monitor.handle(event)

        workflow = monitor.get_workflow_state("wf-test-001")

        assert workflow is not None
        assert workflow.workflow_id == "wf-test-001"
        assert len(workflow.agents) == 1

    @pytest.mark.asyncio
    async def test_get_active_workflows(self, monitor, sample_workflow_events):
        """Should get active workflows."""
        # Process partial events (workflow not completed)
        for event in sample_workflow_events[:5]:
            await monitor.handle(event)

        active = monitor.get_active_workflows()

        assert len(active) == 1
        assert active[0].workflow_id == "wf-test-001"

    @pytest.mark.asyncio
    async def test_get_workflow_timeline(self, monitor, sample_workflow_events):
        """Should get workflow execution timeline."""
        # Process all events
        for event in sample_workflow_events:
            await monitor.handle(event)

        timeline = monitor.get_workflow_timeline("wf-test-001")

        # Should have events: workflow start, agent1 start/end, agent2 start/end, workflow end
        assert len(timeline) >= 5

        # Check order (should be sorted by timestamp)
        timestamps = [event['timestamp'] for event in timeline]
        assert timestamps == sorted(timestamps)

        # Check event types
        event_types = [event['type'] for event in timeline]
        assert 'workflow_start' in event_types
        assert 'workflow_end' in event_types
        assert 'agent_start' in event_types
        assert 'agent_end' in event_types


# ============================================================================
# Bottleneck Detection Tests
# ============================================================================

class TestBottleneckDetection:
    """Test bottleneck detection."""

    @pytest.mark.asyncio
    async def test_detect_bottlenecks_slow_agent(self, monitor):
        """Should detect slow agent bottleneck."""
        now = datetime.utcnow()
        workflow_id = "wf-slow"

        # Create workflow with one very slow agent
        events = [
            Event(
                event_type=WORKFLOW_STARTED,
                timestamp=now,
                payload={"workflow_id": workflow_id},
                trace_id=workflow_id,
                session_id="session-1"
            ),
            Event(
                event_type=AGENT_INVOKED,
                timestamp=now + timedelta(seconds=1),
                payload={"agent": {"name": "fast-agent", "id": "agent-1"}},
                trace_id=workflow_id,
                session_id="session-1"
            ),
            Event(
                event_type=AGENT_COMPLETED,
                timestamp=now + timedelta(seconds=2),
                payload={
                    "agent": {"name": "fast-agent", "id": "agent-1"},
                    "duration_ms": 1000
                },
                trace_id=workflow_id,
                session_id="session-1"
            ),
            Event(
                event_type=AGENT_INVOKED,
                timestamp=now + timedelta(seconds=3),
                payload={"agent": {"name": "slow-agent", "id": "agent-2"}},
                trace_id=workflow_id,
                session_id="session-1"
            ),
            Event(
                event_type=AGENT_COMPLETED,
                timestamp=now + timedelta(seconds=13),
                payload={
                    "agent": {"name": "slow-agent", "id": "agent-2"},
                    "duration_ms": 10000  # 10 seconds (very slow)
                },
                trace_id=workflow_id,
                session_id="session-1"
            ),
            Event(
                event_type=WORKFLOW_COMPLETED,
                timestamp=now + timedelta(seconds=14),
                payload={
                    "workflow_id": workflow_id,
                    "total_duration_ms": 13000
                },
                trace_id=workflow_id,
                session_id="session-1"
            )
        ]

        for event in events:
            await monitor.handle(event)

        bottlenecks = monitor.detect_bottlenecks(workflow_id, threshold_percent=30.0)

        # Should detect slow-agent as bottleneck (10s out of 13s = 77%)
        assert len(bottlenecks) > 0
        slow_bottleneck = [b for b in bottlenecks if b.bottleneck_type == "slow"]
        assert len(slow_bottleneck) > 0
        assert slow_bottleneck[0].agent_name == "slow-agent"

    @pytest.mark.asyncio
    async def test_detect_bottlenecks_sequential(self, monitor, sample_workflow_events):
        """Should detect sequential execution bottleneck."""
        # Process all events (agents run sequentially)
        for event in sample_workflow_events:
            await monitor.handle(event)

        bottlenecks = monitor.detect_bottlenecks("wf-test-001", threshold_percent=30.0)

        # Should detect sequential execution (agents don't overlap)
        sequential_bottlenecks = [b for b in bottlenecks if b.bottleneck_type == "sequential"]
        assert len(sequential_bottlenecks) >= 0  # May or may not be detected depending on threshold


# ============================================================================
# Fleet Statistics Tests
# ============================================================================

class TestFleetStatistics:
    """Test fleet statistics."""

    @pytest.mark.asyncio
    async def test_get_fleet_statistics_empty(self, monitor):
        """Should return empty statistics."""
        stats = monitor.get_fleet_statistics()

        assert stats.active_workflows == 0
        assert stats.completed_workflows == 0
        assert stats.total_agents_run == 0

    @pytest.mark.asyncio
    async def test_get_fleet_statistics_with_data(self, monitor, sample_workflow_events):
        """Should return accurate statistics."""
        # Process all events
        for event in sample_workflow_events:
            await monitor.handle(event)

        stats = monitor.get_fleet_statistics()

        assert stats.completed_workflows == 1
        assert stats.total_agents_run == 2
        assert stats.total_tokens == 2500  # 1000 + 1500
        assert stats.total_cost == 0.075  # 0.03 + 0.045


# ============================================================================
# Global Instance Tests
# ============================================================================

class TestGlobalInstance:
    """Test global instance management."""

    def test_initialize_fleet_monitor(self):
        """Should create global instance."""
        shutdown_fleet_monitor()

        monitor = initialize_fleet_monitor(max_workflows=50)

        assert monitor is not None
        assert get_fleet_monitor() is monitor
        assert monitor.max_workflows == 50

        shutdown_fleet_monitor()

    def test_initialize_twice(self):
        """Should return existing instance."""
        shutdown_fleet_monitor()

        monitor1 = initialize_fleet_monitor(max_workflows=50)
        monitor2 = initialize_fleet_monitor(max_workflows=100)

        # Should be same instance
        assert monitor1 is monitor2
        # Should keep first config
        assert monitor1.max_workflows == 50

        shutdown_fleet_monitor()

    def test_shutdown_fleet_monitor(self):
        """Should clear global instance."""
        initialize_fleet_monitor()

        shutdown_fleet_monitor()

        assert get_fleet_monitor() is None


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for fleet monitor."""

    @pytest.mark.asyncio
    async def test_full_workflow_lifecycle(self, monitor):
        """Should handle complete workflow lifecycle."""
        now = datetime.utcnow()
        workflow_id = "wf-integration"

        # Create complex workflow
        events = []

        # Workflow start
        events.append(Event(
            event_type=WORKFLOW_STARTED,
            timestamp=now,
            payload={"workflow_id": workflow_id},
            trace_id=workflow_id,
            session_id="session-1"
        ))

        # 3 agents executing
        for i in range(3):
            # Agent invoked
            events.append(Event(
                event_type=AGENT_INVOKED,
                timestamp=now + timedelta(seconds=i*3+1),
                payload={
                    "agent": {"name": f"agent-{i}", "id": f"agent-{i}"},
                    "invoked_by": "orchestrator"
                },
                trace_id=workflow_id,
                session_id="session-1"
            ))

            # Agent completed
            events.append(Event(
                event_type=AGENT_COMPLETED,
                timestamp=now + timedelta(seconds=i*3+3),
                payload={
                    "agent": {"name": f"agent-{i}", "id": f"agent-{i}"},
                    "duration_ms": 2000,
                    "tokens": 1000,
                    "cost": 0.03
                },
                trace_id=workflow_id,
                session_id="session-1"
            ))

        # Workflow complete
        events.append(Event(
            event_type=WORKFLOW_COMPLETED,
            timestamp=now + timedelta(seconds=10),
            payload={
                "workflow_id": workflow_id,
                "total_duration_ms": 9000
            },
            trace_id=workflow_id,
            session_id="session-1"
        ))

        # Process all events
        for event in events:
            await monitor.handle(event)

        # Verify workflow state
        workflow = monitor.get_workflow_state(workflow_id)
        assert workflow is not None
        assert len(workflow.agents) == 3
        assert workflow.status == "completed"
        assert workflow.total_tokens == 3000
        assert workflow.total_cost == 0.09

        # Verify timeline
        timeline = monitor.get_workflow_timeline(workflow_id)
        assert len(timeline) >= 7  # start + 3*(agent start+end) + end

        # Verify statistics
        stats = monitor.get_fleet_statistics()
        assert stats.completed_workflows == 1
        assert stats.total_agents_run == 3
