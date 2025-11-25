"""
Fleet Monitor - Multi-Agent Workflow Visualization

Tracks and visualizes multi-agent workflows, showing dependencies,
parallel execution, and bottlenecks.

Links Back To: Main Plan → Phase 3 → Task 3.5

Features:
- Workflow dependency tracking
- Agent execution timeline
- Bottleneck identification
- Resource utilization monitoring

Usage:
    >>> from src.observability.fleet_monitor import FleetMonitor
    >>> monitor = FleetMonitor()
    >>> monitor.record_agent_start(agent_id, workflow_id)
    >>> monitor.record_agent_complete(agent_id, duration_ms)
    >>> workflow = monitor.get_workflow_state(workflow_id)
"""

import time
import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, Tuple
from enum import Enum

from src.core.event_bus import Event, EventHandler, get_event_bus
from src.core.event_types import (
    AGENT_INVOKED, AGENT_COMPLETED, AGENT_FAILED,
    WORKFLOW_STARTED, WORKFLOW_COMPLETED
)

logger = logging.getLogger(__name__)


# ============================================================================
# Data Types
# ============================================================================

class AgentStatus(Enum):
    """Agent execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentExecution:
    """Single agent execution record."""
    agent_id: str
    agent_name: str
    workflow_id: str
    status: AgentStatus
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    duration_ms: Optional[float] = None
    invoked_by: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    tokens: Optional[int] = None
    cost: Optional[float] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result['status'] = self.status.value
        return result


@dataclass
class WorkflowState:
    """Multi-agent workflow state."""
    workflow_id: str
    started_at: float
    completed_at: Optional[float] = None
    status: str = "active"  # "active", "completed", "failed"
    agents: Dict[str, AgentExecution] = field(default_factory=dict)
    execution_order: List[str] = field(default_factory=list)
    total_duration_ms: Optional[float] = None
    total_tokens: int = 0
    total_cost: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'workflow_id': self.workflow_id,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'status': self.status,
            'agents': {k: v.to_dict() for k, v in self.agents.items()},
            'execution_order': self.execution_order,
            'total_duration_ms': self.total_duration_ms,
            'total_tokens': self.total_tokens,
            'total_cost': self.total_cost
        }


@dataclass
class Bottleneck:
    """Identified bottleneck in workflow."""
    workflow_id: str
    agent_id: str
    agent_name: str
    bottleneck_type: str  # "sequential", "slow", "blocking"
    duration_ms: float
    percent_of_total: float
    description: str
    recommendation: str


@dataclass
class FleetStatistics:
    """Fleet-wide statistics."""
    active_workflows: int
    completed_workflows: int
    active_agents: int
    completed_agents: int
    failed_agents: int
    total_agents_run: int
    avg_workflow_duration_ms: float
    avg_agent_duration_ms: float
    parallelization_ratio: float  # How much work is done in parallel
    total_tokens: int
    total_cost: float


# ============================================================================
# Fleet Monitor
# ============================================================================

class FleetMonitor(EventHandler):
    """
    Fleet monitor for multi-agent workflow tracking.

    Tracks agent executions across multiple workflows, identifying
    dependencies, parallel execution, and bottlenecks.

    Attributes:
        workflows: Active and completed workflows
        max_workflows: Maximum workflows to keep in memory
    """

    def __init__(
        self,
        max_workflows: int = 100,
        auto_subscribe: bool = False
    ):
        """
        Initialize fleet monitor.

        Args:
            max_workflows: Maximum workflows to track (default: 100)
            auto_subscribe: Auto-subscribe to event bus (default: False)
        """
        self.max_workflows = max_workflows
        self.workflows: Dict[str, WorkflowState] = {}
        self.workflow_history: deque = deque(maxlen=max_workflows)

        # Statistics
        self.total_workflows_completed = 0
        self.total_agents_run = 0

        if auto_subscribe:
            event_bus = get_event_bus()
            for event_type in [AGENT_INVOKED, AGENT_COMPLETED, AGENT_FAILED,
                              WORKFLOW_STARTED, WORKFLOW_COMPLETED]:
                event_bus.subscribe(event_type, self)

        logger.info(f"FleetMonitor initialized: max_workflows={max_workflows}")

    async def handle(self, event: Event) -> None:
        """
        Handle event from event bus.

        Args:
            event: Event to process
        """
        if event.event_type == WORKFLOW_STARTED:
            self._handle_workflow_started(event)
        elif event.event_type == WORKFLOW_COMPLETED:
            self._handle_workflow_completed(event)
        elif event.event_type == AGENT_INVOKED:
            self._handle_agent_invoked(event)
        elif event.event_type == AGENT_COMPLETED:
            self._handle_agent_completed(event)
        elif event.event_type == AGENT_FAILED:
            self._handle_agent_failed(event)

    # ========================================================================
    # Event Handlers
    # ========================================================================

    def _handle_workflow_started(self, event: Event) -> None:
        """Handle workflow started event."""
        workflow_id = event.payload.get("workflow_id")
        if not workflow_id:
            return

        workflow = WorkflowState(
            workflow_id=workflow_id,
            started_at=event.timestamp.timestamp(),
            status="active"
        )

        self.workflows[workflow_id] = workflow
        logger.debug(f"Workflow started: {workflow_id}")

    def _handle_workflow_completed(self, event: Event) -> None:
        """Handle workflow completed event."""
        workflow_id = event.payload.get("workflow_id")
        if not workflow_id or workflow_id not in self.workflows:
            return

        workflow = self.workflows[workflow_id]
        workflow.completed_at = event.timestamp.timestamp()
        workflow.status = "completed"
        workflow.total_duration_ms = event.payload.get("total_duration_ms")

        # Move to history
        self.workflow_history.append(workflow)
        self.total_workflows_completed += 1

        logger.debug(f"Workflow completed: {workflow_id}")

    def _handle_agent_invoked(self, event: Event) -> None:
        """Handle agent invoked event."""
        agent_data = event.payload.get("agent", {})
        agent_name = self._extract_agent_name(agent_data)
        agent_id = self._extract_agent_id(agent_data)

        if not agent_name:
            return

        # Determine workflow ID (from trace or session)
        workflow_id = event.trace_id or event.session_id

        # Get or create workflow
        if workflow_id not in self.workflows:
            self.workflows[workflow_id] = WorkflowState(
                workflow_id=workflow_id,
                started_at=event.timestamp.timestamp(),
                status="active"
            )

        workflow = self.workflows[workflow_id]

        # Create agent execution
        execution = AgentExecution(
            agent_id=agent_id,
            agent_name=agent_name,
            workflow_id=workflow_id,
            status=AgentStatus.RUNNING,
            started_at=event.timestamp.timestamp(),
            invoked_by=event.payload.get("invoked_by")
        )

        workflow.agents[agent_id] = execution
        workflow.execution_order.append(agent_id)

        self.total_agents_run += 1

        logger.debug(f"Agent invoked: {agent_name} in workflow {workflow_id}")

    def _handle_agent_completed(self, event: Event) -> None:
        """Handle agent completed event."""
        agent_data = event.payload.get("agent", {})
        agent_id = self._extract_agent_id(agent_data)

        if not agent_id:
            return

        # Find agent in workflows
        execution = self._find_agent_execution(agent_id)
        if not execution:
            return

        # Update execution
        execution.completed_at = event.timestamp.timestamp()
        execution.status = AgentStatus.COMPLETED
        execution.duration_ms = event.payload.get("duration_ms")
        execution.tokens = event.payload.get("tokens")
        execution.cost = event.payload.get("cost", 0.0)

        # Update workflow totals
        workflow = self.workflows.get(execution.workflow_id)
        if workflow:
            if execution.tokens:
                workflow.total_tokens += execution.tokens
            if execution.cost:
                workflow.total_cost += execution.cost

        logger.debug(f"Agent completed: {agent_id}")

    def _handle_agent_failed(self, event: Event) -> None:
        """Handle agent failed event."""
        agent_data = event.payload.get("agent", {})
        agent_id = self._extract_agent_id(agent_data)

        if not agent_id:
            return

        # Find agent in workflows
        execution = self._find_agent_execution(agent_id)
        if not execution:
            return

        # Update execution
        execution.completed_at = event.timestamp.timestamp()
        execution.status = AgentStatus.FAILED
        execution.error = event.payload.get("error", "Unknown error")

        logger.debug(f"Agent failed: {agent_id}")

    # ========================================================================
    # Workflow State Queries
    # ========================================================================

    def get_workflow_state(self, workflow_id: str) -> Optional[WorkflowState]:
        """
        Get workflow state.

        Args:
            workflow_id: Workflow ID

        Returns:
            WorkflowState or None if not found
        """
        return self.workflows.get(workflow_id)

    def get_active_workflows(self) -> List[WorkflowState]:
        """Get all active workflows."""
        return [
            wf for wf in self.workflows.values()
            if wf.status == "active"
        ]

    def get_workflow_timeline(
        self,
        workflow_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get workflow execution timeline.

        Args:
            workflow_id: Workflow ID

        Returns:
            List of timeline events with timestamps
        """
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return []

        timeline = []

        # Add workflow start
        timeline.append({
            'timestamp': workflow.started_at,
            'type': 'workflow_start',
            'workflow_id': workflow_id
        })

        # Add agent events
        for agent_id in workflow.execution_order:
            execution = workflow.agents.get(agent_id)
            if not execution:
                continue

            # Agent start
            if execution.started_at:
                timeline.append({
                    'timestamp': execution.started_at,
                    'type': 'agent_start',
                    'agent_id': agent_id,
                    'agent_name': execution.agent_name
                })

            # Agent end
            if execution.completed_at:
                timeline.append({
                    'timestamp': execution.completed_at,
                    'type': 'agent_end',
                    'agent_id': agent_id,
                    'agent_name': execution.agent_name,
                    'status': execution.status.value
                })

        # Add workflow end
        if workflow.completed_at:
            timeline.append({
                'timestamp': workflow.completed_at,
                'type': 'workflow_end',
                'workflow_id': workflow_id
            })

        # Sort by timestamp
        timeline.sort(key=lambda x: x['timestamp'])

        return timeline

    # ========================================================================
    # Bottleneck Detection
    # ========================================================================

    def detect_bottlenecks(
        self,
        workflow_id: str,
        threshold_percent: float = 30.0
    ) -> List[Bottleneck]:
        """
        Detect bottlenecks in workflow.

        Args:
            workflow_id: Workflow ID
            threshold_percent: Threshold for bottleneck (default: 30%)

        Returns:
            List of detected bottlenecks
        """
        workflow = self.workflows.get(workflow_id)
        if not workflow:
            return []

        bottlenecks = []

        # Calculate total workflow duration
        if workflow.completed_at:
            total_duration = (workflow.completed_at - workflow.started_at) * 1000
        else:
            total_duration = (time.time() - workflow.started_at) * 1000

        if total_duration == 0:
            return []

        # Find slow agents
        for agent_id, execution in workflow.agents.items():
            if execution.duration_ms and execution.duration_ms > 0:
                percent = (execution.duration_ms / total_duration) * 100

                if percent >= threshold_percent:
                    bottlenecks.append(Bottleneck(
                        workflow_id=workflow_id,
                        agent_id=agent_id,
                        agent_name=execution.agent_name,
                        bottleneck_type="slow",
                        duration_ms=execution.duration_ms,
                        percent_of_total=percent,
                        description=f"Agent '{execution.agent_name}' took {percent:.1f}% of total workflow time",
                        recommendation=f"Optimize '{execution.agent_name}' to reduce workflow duration"
                    ))

        # Detect sequential execution (lack of parallelism)
        if len(workflow.agents) >= 3:
            # Check if agents are running sequentially
            overlaps = self._calculate_execution_overlaps(workflow)

            if overlaps < 0.3:  # Less than 30% overlap
                bottlenecks.append(Bottleneck(
                    workflow_id=workflow_id,
                    agent_id="workflow",
                    agent_name="Workflow",
                    bottleneck_type="sequential",
                    duration_ms=total_duration,
                    percent_of_total=100.0,
                    description=f"Workflow has {overlaps:.1%} parallelization (agents run mostly sequentially)",
                    recommendation="Identify independent agents and run them in parallel"
                ))

        return bottlenecks

    def _calculate_execution_overlaps(self, workflow: WorkflowState) -> float:
        """
        Calculate execution overlap ratio (parallelization).

        Returns:
            Overlap ratio (0.0 = fully sequential, 1.0 = fully parallel)
        """
        # Collect execution intervals
        intervals = []
        for execution in workflow.agents.values():
            if execution.started_at and execution.completed_at:
                intervals.append((execution.started_at, execution.completed_at))

        if len(intervals) < 2:
            return 0.0

        # Sort by start time
        intervals.sort()

        # Calculate total sequential time vs total time
        total_time = sum(end - start for start, end in intervals)

        # Calculate wall clock time
        min_start = min(start for start, _ in intervals)
        max_end = max(end for _, end in intervals)
        wall_clock_time = max_end - min_start

        if wall_clock_time == 0:
            return 0.0

        # Overlap ratio
        return 1.0 - (wall_clock_time / total_time)

    # ========================================================================
    # Fleet Statistics
    # ========================================================================

    def get_fleet_statistics(self) -> FleetStatistics:
        """Get fleet-wide statistics."""
        active_workflows = [w for w in self.workflows.values() if w.status == "active"]
        completed_workflows = list(self.workflow_history)

        # Count agents
        active_agents = 0
        completed_agents = 0
        failed_agents = 0

        for workflow in active_workflows:
            for execution in workflow.agents.values():
                if execution.status == AgentStatus.RUNNING:
                    active_agents += 1
                elif execution.status == AgentStatus.COMPLETED:
                    completed_agents += 1
                elif execution.status == AgentStatus.FAILED:
                    failed_agents += 1

        # Calculate averages
        workflow_durations = []
        agent_durations = []
        parallelization_ratios = []
        total_tokens = 0
        total_cost = 0.0

        for workflow in completed_workflows:
            if workflow.total_duration_ms:
                workflow_durations.append(workflow.total_duration_ms)

            total_tokens += workflow.total_tokens
            total_cost += workflow.total_cost

            for execution in workflow.agents.values():
                if execution.duration_ms:
                    agent_durations.append(execution.duration_ms)

            # Calculate parallelization
            overlap = self._calculate_execution_overlaps(workflow)
            parallelization_ratios.append(overlap)

        avg_workflow_duration = sum(workflow_durations) / len(workflow_durations) if workflow_durations else 0
        avg_agent_duration = sum(agent_durations) / len(agent_durations) if agent_durations else 0
        avg_parallelization = sum(parallelization_ratios) / len(parallelization_ratios) if parallelization_ratios else 0

        return FleetStatistics(
            active_workflows=len(active_workflows),
            completed_workflows=len(completed_workflows),
            active_agents=active_agents,
            completed_agents=completed_agents,
            failed_agents=failed_agents,
            total_agents_run=self.total_agents_run,
            avg_workflow_duration_ms=avg_workflow_duration,
            avg_agent_duration_ms=avg_agent_duration,
            parallelization_ratio=avg_parallelization,
            total_tokens=total_tokens,
            total_cost=total_cost
        )

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _extract_agent_name(self, agent_data: Any) -> Optional[str]:
        """Extract agent name from agent data."""
        if isinstance(agent_data, dict):
            return agent_data.get("name") or agent_data.get("id")
        elif isinstance(agent_data, str):
            return agent_data
        return None

    def _extract_agent_id(self, agent_data: Any) -> Optional[str]:
        """Extract agent ID from agent data."""
        if isinstance(agent_data, dict):
            return agent_data.get("id") or agent_data.get("name")
        elif isinstance(agent_data, str):
            return agent_data
        return None

    def _find_agent_execution(self, agent_id: str) -> Optional[AgentExecution]:
        """Find agent execution across all workflows."""
        for workflow in self.workflows.values():
            if agent_id in workflow.agents:
                return workflow.agents[agent_id]
        return None

    def clear(self) -> None:
        """Clear all workflow data (for testing)."""
        self.workflows.clear()
        self.workflow_history.clear()
        self.total_workflows_completed = 0
        self.total_agents_run = 0


# ============================================================================
# Global Instance Management
# ============================================================================

_monitor_instance: Optional[FleetMonitor] = None


def get_fleet_monitor() -> Optional[FleetMonitor]:
    """Get global fleet monitor instance."""
    return _monitor_instance


def initialize_fleet_monitor(
    max_workflows: int = 100,
    auto_subscribe: bool = False
) -> FleetMonitor:
    """
    Initialize global fleet monitor instance.

    Args:
        max_workflows: Maximum workflows to track
        auto_subscribe: Auto-subscribe to event bus

    Returns:
        FleetMonitor instance
    """
    global _monitor_instance

    if _monitor_instance is not None:
        logger.warning("FleetMonitor already initialized")
        return _monitor_instance

    _monitor_instance = FleetMonitor(
        max_workflows=max_workflows,
        auto_subscribe=auto_subscribe
    )

    return _monitor_instance


def shutdown_fleet_monitor() -> None:
    """Shutdown global fleet monitor instance."""
    global _monitor_instance
    _monitor_instance = None
