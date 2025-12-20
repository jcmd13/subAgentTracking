"""
Metrics Aggregator - Live Statistics with Rolling Windows

This module provides real-time metrics aggregation with rolling time windows,
enabling live dashboards to display current performance statistics.

Links Back To: Main Plan → Phase 3 → Task 3.1

Features:
- Rolling window calculations (1min, 5min, 15min)
- Event rate tracking
- Resource usage monitoring
- Cost accumulation
- Performance percentiles

Performance Targets:
- Aggregation overhead: <10ms per event
- Memory usage: <100MB for 1M events
- Query latency: <5ms

Usage:
    >>> from src.observability.metrics_aggregator import MetricsAggregator
    >>> aggregator = MetricsAggregator(window_size=300)  # 5 minutes
    >>> aggregator.record_event(event)
    >>> stats = aggregator.get_current_stats()
"""

import time
from collections import deque, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from src.core.event_bus import Event, EventHandler, get_event_bus
from src.core.event_types import (
    AGENT_INVOKED, AGENT_COMPLETED, AGENT_FAILED,
    TOOL_USED, WORKFLOW_STARTED, WORKFLOW_COMPLETED,
    TASK_STARTED, TASK_STAGE_CHANGED, TASK_COMPLETED,
    TEST_RUN_STARTED, TEST_RUN_COMPLETED,
    ALL_EVENT_TYPES
)

import logging
logger = logging.getLogger(__name__)


# ============================================================================
# Data Types
# ============================================================================

class WindowSize(Enum):
    """Standard time window sizes."""
    ONE_MINUTE = 60
    FIVE_MINUTES = 300
    FIFTEEN_MINUTES = 900
    ONE_HOUR = 3600


@dataclass
class EventRecord:
    """Single event record for aggregation."""
    timestamp: float
    event_type: str
    agent: Optional[str] = None
    duration_ms: Optional[float] = None
    tokens: Optional[int] = None
    cost: Optional[float] = None
    status: Optional[str] = None
    success: bool = True


@dataclass
class MetricsSnapshot:
    """Snapshot of current metrics."""
    timestamp: float
    window_size_seconds: int

    # Event counts
    total_events: int = 0
    events_by_type: Dict[str, int] = field(default_factory=dict)

    # Agent metrics
    agents_active: int = 0
    agents_completed: int = 0
    agents_failed: int = 0

    # Workflow metrics
    workflows_active: int = 0
    workflows_completed: int = 0

    # Task metrics
    tasks_active: int = 0
    tasks_completed: int = 0

    # Test metrics
    tests_running: int = 0
    tests_passed: int = 0
    tests_failed: int = 0

    # Performance metrics
    avg_agent_duration_ms: float = 0.0
    p50_agent_duration_ms: float = 0.0
    p95_agent_duration_ms: float = 0.0
    p99_agent_duration_ms: float = 0.0

    # Resource metrics
    total_tokens: int = 0
    total_cost: float = 0.0
    tokens_per_second: float = 0.0
    cost_per_hour: float = 0.0

    # Rate metrics
    events_per_second: float = 0.0
    agents_per_minute: float = 0.0


# ============================================================================
# Metrics Aggregator
# ============================================================================

class MetricsAggregator(EventHandler):
    """
    Real-time metrics aggregation with rolling windows.

    Collects events and computes live statistics over configurable
    time windows. Designed for minimal overhead and fast queries.

    Attributes:
        window_sizes: List of window sizes to maintain (seconds)
        max_records: Maximum records to keep per window
    """

    def __init__(
        self,
        window_sizes: Optional[List[int]] = None,
        max_records: int = 10000,
        auto_subscribe: bool = False
    ):
        """
        Initialize metrics aggregator.

        Args:
            window_sizes: Time windows to maintain (default: 1m, 5m, 15m)
            max_records: Maximum records per window (memory limit)
            auto_subscribe: Auto-subscribe to event bus (False by default due to async/sync compatibility)
        """
        if window_sizes is None:
            window_sizes = [
                WindowSize.ONE_MINUTE.value,
                WindowSize.FIVE_MINUTES.value,
                WindowSize.FIFTEEN_MINUTES.value
            ]

        self.window_sizes = sorted(window_sizes)
        self.max_records = max_records
        self.auto_subscribe = auto_subscribe

        # Event storage (one deque per window size)
        self.windows: Dict[int, deque] = {
            size: deque(maxlen=max_records)
            for size in window_sizes
        }

        # Active workflow tracking
        self.active_workflows: Dict[str, float] = {}  # workflow_id -> start_time
        self.active_agents: Dict[str, float] = {}  # agent_id -> start_time
        self.active_tasks: Dict[str, float] = {}  # task_id -> start_time
        self.active_tests: Dict[str, float] = {}  # test_id -> start_time

        # Cumulative metrics (all-time)
        self.cumulative_events = 0
        self.cumulative_tokens = 0
        self.cumulative_cost = 0.0

        # Performance tracking
        self.started_at = time.time()

        # Subscribe to event bus
        if auto_subscribe:
            event_bus = get_event_bus()
            for event_type in ALL_EVENT_TYPES:
                event_bus.subscribe(event_type, self)

        logger.info(
            f"MetricsAggregator initialized: "
            f"windows={window_sizes}, max_records={max_records}"
        )

    async def handle(self, event: Event) -> None:
        """
        Handle event from event bus - record for aggregation.

        Args:
            event: Event to record
        """
        self.record_event(event)

    def record_event(self, event: Event) -> None:
        """
        Record event in all time windows.

        Args:
            event: Event to record
        """
        start_time = time.time()

        # Extract event data
        record = self._event_to_record(event)

        # Add to all windows
        for window_size, window in self.windows.items():
            window.append(record)

        # Update active tracking
        self._update_active_tracking(event)

        # Update cumulative metrics
        self.cumulative_events += 1
        if record.tokens:
            self.cumulative_tokens += record.tokens
        if record.cost:
            self.cumulative_cost += record.cost

        # Log performance warning if slow
        duration = (time.time() - start_time) * 1000
        if duration > 10:
            logger.warning(f"Slow event recording: {duration:.2f}ms")

    def _event_to_record(self, event: Event) -> EventRecord:
        """Convert Event to EventRecord."""
        payload = event.payload

        # Extract agent name
        agent = None
        if "agent" in payload:
            agent_data = payload["agent"]
            if isinstance(agent_data, dict):
                agent = agent_data.get("name")
            else:
                agent = str(agent_data)

        # Extract duration
        duration_ms = payload.get("duration_ms")
        if duration_ms is None and "metadata" in payload:
            metadata = payload["metadata"]
            if isinstance(metadata, dict):
                duration_ms = metadata.get("duration_ms")

        # Extract tokens and cost
        tokens = payload.get("tokens")
        if tokens is None:
            tokens = payload.get("tokens_consumed")
        if tokens is None:
            tokens = payload.get("tokens_used")

        cost = payload.get("cost")
        if cost is None:
            cost = payload.get("cost_usd")

        # Extract status (task/test completion)
        status = payload.get("status")

        # Determine success
        success = event.event_type != AGENT_FAILED

        return EventRecord(
            timestamp=event.timestamp.timestamp(),
            event_type=event.event_type,
            agent=agent,
            duration_ms=duration_ms,
            tokens=tokens,
            cost=cost,
            status=status,
            success=success
        )

    def _update_active_tracking(self, event: Event) -> None:
        """Update active workflow/agent tracking."""
        payload = event.payload

        # Track workflows
        if event.event_type == WORKFLOW_STARTED:
            workflow_id = payload.get("workflow_id")
            if workflow_id:
                self.active_workflows[workflow_id] = event.timestamp.timestamp()

        elif event.event_type == WORKFLOW_COMPLETED:
            workflow_id = payload.get("workflow_id")
            if workflow_id and workflow_id in self.active_workflows:
                del self.active_workflows[workflow_id]

        # Track agents
        if event.event_type == AGENT_INVOKED:
            agent_data = payload.get("agent", {})
            if isinstance(agent_data, dict):
                agent_id = agent_data.get("id") or agent_data.get("name")
            else:
                agent_id = str(agent_data)

            if agent_id:
                self.active_agents[agent_id] = event.timestamp.timestamp()

        elif event.event_type in [AGENT_COMPLETED, AGENT_FAILED]:
            agent_data = payload.get("agent", {})
            if isinstance(agent_data, dict):
                agent_id = agent_data.get("id") or agent_data.get("name")
            else:
                agent_id = str(agent_data)

            if agent_id and agent_id in self.active_agents:
                del self.active_agents[agent_id]

        # Track tasks
        if event.event_type in [TASK_STARTED, TASK_STAGE_CHANGED]:
            task_id = payload.get("task_id")
            if task_id:
                self.active_tasks[task_id] = event.timestamp.timestamp()

        elif event.event_type == TASK_COMPLETED:
            task_id = payload.get("task_id")
            if task_id and task_id in self.active_tasks:
                del self.active_tasks[task_id]

        # Track tests
        test_suite = payload.get("test_suite")
        test_task_id = payload.get("task_id")
        test_key = payload.get("run_id")
        if not test_key:
            if test_suite and test_task_id:
                test_key = f"{test_suite}:{test_task_id}"
            else:
                test_key = test_suite

        if event.event_type == TEST_RUN_STARTED and test_key:
            self.active_tests[test_key] = event.timestamp.timestamp()

        elif event.event_type == TEST_RUN_COMPLETED and test_key:
            if test_key in self.active_tests:
                del self.active_tests[test_key]

    def get_current_stats(
        self,
        window_size: Optional[int] = None
    ) -> MetricsSnapshot:
        """
        Get current metrics for specified window.

        Args:
            window_size: Window size in seconds (default: smallest window)

        Returns:
            MetricsSnapshot with current statistics
        """
        if window_size is None:
            window_size = self.window_sizes[0]

        if window_size not in self.windows:
            raise ValueError(f"Window size {window_size} not configured")

        current_time = time.time()
        window = self.windows[window_size]

        # Filter to window
        cutoff = current_time - window_size
        recent_records = [r for r in window if r.timestamp >= cutoff]

        if not recent_records:
            return MetricsSnapshot(
                timestamp=current_time,
                window_size_seconds=window_size
            )

        # Compute statistics
        snapshot = MetricsSnapshot(
            timestamp=current_time,
            window_size_seconds=window_size
        )

        # Event counts
        snapshot.total_events = len(recent_records)
        snapshot.events_by_type = defaultdict(int)
        for record in recent_records:
            snapshot.events_by_type[record.event_type] += 1

        # Agent metrics
        snapshot.agents_active = len(self.active_agents)
        snapshot.agents_completed = snapshot.events_by_type.get(AGENT_COMPLETED, 0)
        snapshot.agents_failed = snapshot.events_by_type.get(AGENT_FAILED, 0)

        # Workflow metrics
        snapshot.workflows_active = len(self.active_workflows)
        snapshot.workflows_completed = snapshot.events_by_type.get(WORKFLOW_COMPLETED, 0)

        # Task metrics
        snapshot.tasks_active = len(self.active_tasks)
        snapshot.tasks_completed = snapshot.events_by_type.get(TASK_COMPLETED, 0)

        # Test metrics
        snapshot.tests_running = len(self.active_tests)
        snapshot.tests_passed = sum(
            1 for r in recent_records
            if r.event_type == TEST_RUN_COMPLETED and r.status == "passed"
        )
        snapshot.tests_failed = sum(
            1 for r in recent_records
            if r.event_type == TEST_RUN_COMPLETED and r.status == "failed"
        )

        # Performance metrics (agent durations)
        durations = [
            r.duration_ms for r in recent_records
            if r.duration_ms is not None
        ]
        if durations:
            durations_sorted = sorted(durations)
            snapshot.avg_agent_duration_ms = sum(durations) / len(durations)
            snapshot.p50_agent_duration_ms = self._percentile(durations_sorted, 50)
            snapshot.p95_agent_duration_ms = self._percentile(durations_sorted, 95)
            snapshot.p99_agent_duration_ms = self._percentile(durations_sorted, 99)

        # Resource metrics
        snapshot.total_tokens = sum(r.tokens or 0 for r in recent_records)
        snapshot.total_cost = sum(r.cost or 0.0 for r in recent_records)

        # Rate metrics
        snapshot.events_per_second = len(recent_records) / window_size
        snapshot.agents_per_minute = (
            snapshot.events_by_type.get(AGENT_INVOKED, 0) / (window_size / 60)
        )
        snapshot.tokens_per_second = snapshot.total_tokens / window_size
        snapshot.cost_per_hour = snapshot.total_cost * (3600 / window_size)

        return snapshot

    def _percentile(self, sorted_values: List[float], percentile: int) -> float:
        """Calculate percentile from sorted values."""
        if not sorted_values:
            return 0.0

        index = int((percentile / 100) * len(sorted_values))
        index = max(0, min(index, len(sorted_values) - 1))
        return sorted_values[index]

    def get_all_stats(self) -> Dict[int, MetricsSnapshot]:
        """Get statistics for all configured windows."""
        return {
            window_size: self.get_current_stats(window_size)
            for window_size in self.window_sizes
        }

    def get_cumulative_stats(self) -> Dict[str, Any]:
        """Get all-time cumulative statistics."""
        uptime = time.time() - self.started_at

        return {
            "uptime_seconds": uptime,
            "total_events": self.cumulative_events,
            "total_tokens": self.cumulative_tokens,
            "total_cost": self.cumulative_cost,
            "events_per_second": self.cumulative_events / uptime if uptime > 0 else 0,
            "active_workflows": len(self.active_workflows),
            "active_agents": len(self.active_agents),
            "active_tasks": len(self.active_tasks),
            "active_tests": len(self.active_tests),
            "window_sizes": self.window_sizes,
            "max_records": self.max_records
        }

    def clear(self) -> None:
        """Clear all recorded events (for testing)."""
        for window in self.windows.values():
            window.clear()

        self.active_workflows.clear()
        self.active_agents.clear()
        self.active_tasks.clear()
        self.active_tests.clear()
        self.cumulative_events = 0
        self.cumulative_tokens = 0
        self.cumulative_cost = 0.0
        self.started_at = time.time()


# ============================================================================
# Global Instance Management
# ============================================================================

_aggregator_instance: Optional[MetricsAggregator] = None


def initialize_metrics_aggregator(
    window_sizes: Optional[List[int]] = None,
    max_records: int = 10000,
    auto_subscribe: bool = False
) -> MetricsAggregator:
    """
    Initialize global metrics aggregator instance.

    Args:
        window_sizes: Time windows to maintain (default: 1m, 5m, 15m)
        max_records: Maximum records per window
        auto_subscribe: Auto-subscribe to event bus

    Returns:
        MetricsAggregator instance
    """
    global _aggregator_instance

    if _aggregator_instance is not None:
        logger.warning("MetricsAggregator already initialized")
        return _aggregator_instance

    _aggregator_instance = MetricsAggregator(
        window_sizes=window_sizes,
        max_records=max_records,
        auto_subscribe=auto_subscribe
    )

    return _aggregator_instance


def get_metrics_aggregator() -> Optional[MetricsAggregator]:
    """Get global metrics aggregator instance."""
    return _aggregator_instance


def shutdown_metrics_aggregator() -> None:
    """Shutdown global metrics aggregator instance."""
    global _aggregator_instance
    _aggregator_instance = None
