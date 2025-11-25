"""
Tests for Analytics Engine

Tests pattern detection, cost analysis, and performance regression detection.

Links Back To: Main Plan → Phase 3 → Task 3.3
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock

from src.core.event_bus import Event
from src.core.event_types import (
    AGENT_INVOKED, AGENT_COMPLETED, AGENT_FAILED,
    TOOL_USED, WORKFLOW_STARTED, WORKFLOW_COMPLETED
)

from src.observability.analytics_engine import (
    AnalyticsEngine,
    Pattern,
    CostAnalysis,
    PerformanceBaseline,
    PerformanceRegression,
    get_analytics_engine,
    reset_analytics_engine
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def engine():
    """Create analytics engine for testing."""
    reset_analytics_engine()
    engine = AnalyticsEngine()
    yield engine
    reset_analytics_engine()


@pytest.fixture
def sample_events():
    """Create sample events for testing."""
    now = datetime.utcnow()

    return [
        # Agent 1: Success
        Event(
            event_type=AGENT_INVOKED,
            timestamp=now,
            payload={"agent": {"name": "agent-1"}},
            trace_id="trace-1",
            session_id="session-1"
        ),
        Event(
            event_type=AGENT_COMPLETED,
            timestamp=now + timedelta(seconds=1),
            payload={
                "agent": {"name": "agent-1"},
                "duration_ms": 1000,
                "tokens": 500,
                "cost": 0.015
            },
            trace_id="trace-1",
            session_id="session-1"
        ),

        # Agent 2: Failure
        Event(
            event_type=AGENT_INVOKED,
            timestamp=now + timedelta(seconds=2),
            payload={"agent": {"name": "agent-2"}},
            trace_id="trace-2",
            session_id="session-1"
        ),
        Event(
            event_type=AGENT_FAILED,
            timestamp=now + timedelta(seconds=3),
            payload={"agent": {"name": "agent-2"}},
            trace_id="trace-2",
            session_id="session-1"
        ),
    ]


# ============================================================================
# Pattern Detection Tests
# ============================================================================

class TestPatternDetection:
    """Test pattern detection functionality."""

    def test_detect_patterns_empty(self, engine):
        """Should handle empty event list."""
        patterns = engine.detect_patterns([])

        assert len(patterns) == 0

    def test_detect_recurring_failures(self, engine):
        """Should detect agents with high failure rates."""
        now = datetime.utcnow()

        # Create agent with 3 failures out of 4 invocations (75% failure rate)
        events = []
        for i in range(4):
            events.append(Event(
                event_type=AGENT_INVOKED,
                timestamp=now + timedelta(seconds=i*2),
                payload={"agent": {"name": "failing-agent"}},
                trace_id=f"trace-{i}",
                session_id="session-1"
            ))

            if i < 3:  # First 3 fail
                events.append(Event(
                    event_type=AGENT_FAILED,
                    timestamp=now + timedelta(seconds=i*2+1),
                    payload={"agent": {"name": "failing-agent"}},
                    trace_id=f"trace-{i}",
                    session_id="session-1"
                ))
            else:  # Last one succeeds
                events.append(Event(
                    event_type=AGENT_COMPLETED,
                    timestamp=now + timedelta(seconds=i*2+1),
                    payload={"agent": {"name": "failing-agent"}},
                    trace_id=f"trace-{i}",
                    session_id="session-1"
                ))

        patterns = engine.detect_patterns(events)

        # Should detect recurring failure pattern
        failure_patterns = [p for p in patterns if p.pattern_type == "recurring_failure"]
        assert len(failure_patterns) >= 1

        pattern = failure_patterns[0]
        assert pattern.severity in ["high", "critical"]
        assert "failing-agent" in pattern.description
        assert pattern.confidence >= 0.8

    def test_detect_bottlenecks(self, engine):
        """Should detect slow agents."""
        now = datetime.utcnow()

        # Create agent with slow performance (avg > 5 seconds)
        events = []
        for i in range(5):
            events.append(Event(
                event_type=AGENT_COMPLETED,
                timestamp=now + timedelta(seconds=i*10),
                payload={
                    "agent": {"name": "slow-agent"},
                    "duration_ms": 6000 + i * 100  # 6-6.4 seconds
                },
                trace_id=f"trace-{i}",
                session_id="session-1"
            ))

        patterns = engine.detect_patterns(events)

        # Should detect bottleneck
        bottleneck_patterns = [p for p in patterns if p.pattern_type == "bottleneck"]
        assert len(bottleneck_patterns) >= 1

        pattern = bottleneck_patterns[0]
        assert "slow-agent" in pattern.description
        assert pattern.severity in ["medium", "high"]

    def test_detect_inefficiencies(self, engine):
        """Should detect repeated file operations."""
        now = datetime.utcnow()

        # Create repeated Read operations on same file
        events = []
        for i in range(6):
            events.append(Event(
                event_type=TOOL_USED,
                timestamp=now + timedelta(seconds=i),
                payload={
                    "agent": "test-agent",
                    "tool": "Read",
                    "details": {"file": "src/test.py"}
                },
                trace_id=f"trace-{i}",
                session_id="session-1"
            ))

        patterns = engine.detect_patterns(events)

        # Should detect inefficiency
        inefficiency_patterns = [p for p in patterns if p.pattern_type == "inefficiency"]
        assert len(inefficiency_patterns) >= 1

        pattern = inefficiency_patterns[0]
        assert "test.py" in pattern.description
        assert "Read" in pattern.description

    def test_detect_workflow_patterns(self, engine):
        """Should detect long-running workflows."""
        now = datetime.utcnow()

        events = [
            Event(
                event_type=WORKFLOW_STARTED,
                timestamp=now,
                payload={"workflow_id": "wf-1"},
                trace_id="trace-1",
                session_id="session-1"
            ),
            Event(
                event_type=WORKFLOW_COMPLETED,
                timestamp=now + timedelta(seconds=90),
                payload={
                    "workflow_id": "wf-1",
                    "total_duration_ms": 90000  # 90 seconds
                },
                trace_id="trace-1",
                session_id="session-1"
            )
        ]

        patterns = engine.detect_patterns(events)

        # Should detect long-running workflow
        workflow_patterns = [
            p for p in patterns
            if p.pattern_type == "inefficiency" and "workflow" in p.description.lower()
        ]
        assert len(workflow_patterns) >= 1


# ============================================================================
# Cost Analysis Tests
# ============================================================================

class TestCostAnalysis:
    """Test cost analysis functionality."""

    def test_analyze_costs_empty(self, engine):
        """Should handle empty event list."""
        analysis = engine.analyze_costs([])

        assert analysis.total_cost == 0.0
        assert analysis.total_tokens == 0
        assert len(analysis.cost_by_agent) == 0

    def test_analyze_costs_basic(self, engine):
        """Should analyze costs correctly."""
        now = datetime.utcnow()

        events = [
            Event(
                event_type=AGENT_COMPLETED,
                timestamp=now,
                payload={
                    "agent": {"name": "agent-1"},
                    "tokens": 1000,
                    "cost": 0.03
                },
                trace_id="trace-1",
                session_id="session-1"
            ),
            Event(
                event_type=AGENT_COMPLETED,
                timestamp=now + timedelta(seconds=1),
                payload={
                    "agent": {"name": "agent-2"},
                    "tokens": 2000,
                    "cost": 0.06
                },
                trace_id="trace-2",
                session_id="session-1"
            )
        ]

        analysis = engine.analyze_costs(events)

        assert analysis.total_cost == 0.09
        assert analysis.total_tokens == 3000
        assert "agent-1" in analysis.cost_by_agent
        assert "agent-2" in analysis.cost_by_agent
        assert analysis.cost_by_agent["agent-1"] == 0.03
        assert analysis.cost_by_agent["agent-2"] == 0.06

    def test_analyze_costs_most_expensive(self, engine):
        """Should identify most expensive agents."""
        now = datetime.utcnow()

        events = []
        for i in range(5):
            events.append(Event(
                event_type=AGENT_COMPLETED,
                timestamp=now + timedelta(seconds=i),
                payload={
                    "agent": {"name": f"agent-{i}"},
                    "tokens": (i + 1) * 1000,
                    "cost": (i + 1) * 0.03
                },
                trace_id=f"trace-{i}",
                session_id="session-1"
            ))

        analysis = engine.analyze_costs(events)

        # Most expensive should be agent-4 (5th agent)
        assert len(analysis.most_expensive_agents) > 0
        top_agent, top_cost = analysis.most_expensive_agents[0]
        assert top_agent == "agent-4"
        assert top_cost == 0.15

    def test_analyze_costs_optimization_opportunities(self, engine):
        """Should generate optimization recommendations."""
        now = datetime.utcnow()

        # Create agent with > 50% of total cost
        events = [
            Event(
                event_type=AGENT_COMPLETED,
                timestamp=now,
                payload={
                    "agent": {"name": "expensive-agent"},
                    "tokens": 100000,
                    "cost": 3.0
                },
                trace_id="trace-1",
                session_id="session-1"
            ),
            Event(
                event_type=AGENT_COMPLETED,
                timestamp=now + timedelta(seconds=1),
                payload={
                    "agent": {"name": "cheap-agent"},
                    "tokens": 1000,
                    "cost": 0.03
                },
                trace_id="trace-2",
                session_id="session-1"
            )
        ]

        analysis = engine.analyze_costs(events)

        # Should recommend optimizing expensive-agent
        assert len(analysis.optimization_opportunities) > 0
        assert any("expensive-agent" in rec for rec in analysis.optimization_opportunities)

    def test_analyze_costs_projected_monthly(self, engine):
        """Should project monthly costs."""
        now = datetime.utcnow()

        # 1 hour of events costing $1
        events = [
            Event(
                event_type=AGENT_COMPLETED,
                timestamp=now,
                payload={"agent": {"name": "agent-1"}, "cost": 1.0},
                trace_id="trace-1",
                session_id="session-1"
            )
        ]

        analysis = engine.analyze_costs(events, lookback_window=3600)  # 1 hour

        # Should project ~$720/month (1$/hour * 24 * 30)
        assert analysis.projected_monthly_cost > 700
        assert analysis.projected_monthly_cost < 750


# ============================================================================
# Performance Regression Tests
# ============================================================================

class TestPerformanceRegression:
    """Test performance regression detection."""

    def test_update_baseline(self, engine):
        """Should create performance baseline."""
        now = datetime.utcnow()

        events = []
        for i in range(10):
            events.append(Event(
                event_type=AGENT_COMPLETED,
                timestamp=now + timedelta(seconds=i),
                payload={
                    "agent": {"name": "test-agent"},
                    "duration_ms": 1000 + i * 10  # 1000-1090ms
                },
                trace_id=f"trace-{i}",
                session_id="session-1"
            ))

        baseline = engine.update_baseline("test-agent", events)

        assert baseline is not None
        assert baseline.agent == "test-agent"
        assert baseline.sample_count == 10
        assert baseline.avg_duration_ms > 1000
        assert baseline.avg_duration_ms < 1100

    def test_detect_regressions_none(self, engine):
        """Should not detect regression if performance is stable."""
        now = datetime.utcnow()

        # Create baseline
        baseline_events = []
        for i in range(10):
            baseline_events.append(Event(
                event_type=AGENT_COMPLETED,
                timestamp=now + timedelta(seconds=i),
                payload={
                    "agent": {"name": "test-agent"},
                    "duration_ms": 1000
                },
                trace_id=f"trace-{i}",
                session_id="session-1"
            ))

        engine.update_baseline("test-agent", baseline_events)

        # Current events with similar performance
        current_events = []
        for i in range(5):
            current_events.append(Event(
                event_type=AGENT_COMPLETED,
                timestamp=now + timedelta(seconds=i+20),
                payload={
                    "agent": {"name": "test-agent"},
                    "duration_ms": 1050  # Slightly higher but < 20% threshold
                },
                trace_id=f"trace-{i+20}",
                session_id="session-1"
            ))

        regressions = engine.detect_regressions(current_events)

        assert len(regressions) == 0

    def test_detect_regressions_degradation(self, engine):
        """Should detect performance regression."""
        now = datetime.utcnow()

        # Create baseline
        baseline_events = []
        for i in range(10):
            baseline_events.append(Event(
                event_type=AGENT_COMPLETED,
                timestamp=now + timedelta(seconds=i),
                payload={
                    "agent": {"name": "test-agent"},
                    "duration_ms": 1000
                },
                trace_id=f"trace-{i}",
                session_id="session-1"
            ))

        engine.update_baseline("test-agent", baseline_events)

        # Current events with degraded performance (30% slower)
        current_events = []
        for i in range(5):
            current_events.append(Event(
                event_type=AGENT_COMPLETED,
                timestamp=now + timedelta(seconds=i+20),
                payload={
                    "agent": {"name": "test-agent"},
                    "duration_ms": 1300  # 30% slower
                },
                trace_id=f"trace-{i+20}",
                session_id="session-1"
            ))

        regressions = engine.detect_regressions(current_events, threshold_percent=20.0)

        # Should detect regression
        assert len(regressions) > 0

        regression = regressions[0]
        assert regression.agent == "test-agent"
        assert regression.degradation_percent >= 20
        assert regression.severity in ["minor", "moderate", "severe"]

    def test_detect_regressions_severity(self, engine):
        """Should classify regression severity correctly."""
        now = datetime.utcnow()

        # Create baseline
        baseline_events = []
        for i in range(10):
            baseline_events.append(Event(
                event_type=AGENT_COMPLETED,
                timestamp=now + timedelta(seconds=i),
                payload={
                    "agent": {"name": "test-agent"},
                    "duration_ms": 1000
                },
                trace_id=f"trace-{i}",
                session_id="session-1"
            ))

        engine.update_baseline("test-agent", baseline_events)

        # Test severe degradation (60% slower)
        current_events = []
        for i in range(5):
            current_events.append(Event(
                event_type=AGENT_COMPLETED,
                timestamp=now + timedelta(seconds=i+20),
                payload={
                    "agent": {"name": "test-agent"},
                    "duration_ms": 1600  # 60% slower
                },
                trace_id=f"trace-{i+20}",
                session_id="session-1"
            ))

        regressions = engine.detect_regressions(current_events, threshold_percent=20.0)

        # Should detect severe regression
        assert len(regressions) > 0
        assert any(r.severity == "severe" for r in regressions)


# ============================================================================
# Global Instance Tests
# ============================================================================

class TestGlobalInstance:
    """Test global instance management."""

    def test_get_analytics_engine(self):
        """Should create and return global instance."""
        reset_analytics_engine()

        engine1 = get_analytics_engine()
        engine2 = get_analytics_engine()

        # Should be same instance
        assert engine1 is engine2

        reset_analytics_engine()

    def test_reset_analytics_engine(self):
        """Should reset global instance."""
        engine1 = get_analytics_engine()

        reset_analytics_engine()

        engine2 = get_analytics_engine()

        # Should be different instance
        assert engine1 is not engine2


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for analytics engine."""

    def test_full_analysis_workflow(self, engine):
        """Should perform full analysis workflow."""
        now = datetime.utcnow()

        # Create realistic event sequence
        events = []

        # Workflow started
        events.append(Event(
            event_type=WORKFLOW_STARTED,
            timestamp=now,
            payload={"workflow_id": "wf-1"},
            trace_id="trace-1",
            session_id="session-1"
        ))

        # Agent 1: Fast, cheap
        for i in range(3):
            events.append(Event(
                event_type=AGENT_INVOKED,
                timestamp=now + timedelta(seconds=i*5),
                payload={"agent": {"name": "fast-agent"}},
                trace_id=f"trace-{i}",
                session_id="session-1"
            ))
            events.append(Event(
                event_type=AGENT_COMPLETED,
                timestamp=now + timedelta(seconds=i*5+1),
                payload={
                    "agent": {"name": "fast-agent"},
                    "duration_ms": 1000,
                    "tokens": 500,
                    "cost": 0.015
                },
                trace_id=f"trace-{i}",
                session_id="session-1"
            ))

        # Agent 2: Slow, expensive
        for i in range(3):
            events.append(Event(
                event_type=AGENT_INVOKED,
                timestamp=now + timedelta(seconds=20+i*15),
                payload={"agent": {"name": "slow-agent"}},
                trace_id=f"trace-slow-{i}",
                session_id="session-1"
            ))
            events.append(Event(
                event_type=AGENT_COMPLETED,
                timestamp=now + timedelta(seconds=20+i*15+10),
                payload={
                    "agent": {"name": "slow-agent"},
                    "duration_ms": 10000,  # 10 seconds
                    "tokens": 10000,
                    "cost": 0.3
                },
                trace_id=f"trace-slow-{i}",
                session_id="session-1"
            ))

        # Workflow completed
        events.append(Event(
            event_type=WORKFLOW_COMPLETED,
            timestamp=now + timedelta(seconds=80),
            payload={"workflow_id": "wf-1", "total_duration_ms": 80000},
            trace_id="trace-1",
            session_id="session-1"
        ))

        # Run full analysis
        patterns = engine.detect_patterns(events)
        cost_analysis = engine.analyze_costs(events)

        # Update baselines
        engine.update_baseline("fast-agent", events)
        engine.update_baseline("slow-agent", events)

        # Verify results
        assert len(patterns) > 0  # Should detect bottleneck and/or long workflow
        assert cost_analysis.total_cost > 0
        assert cost_analysis.total_tokens > 0
        assert "slow-agent" in cost_analysis.cost_by_agent
        assert "fast-agent" in cost_analysis.cost_by_agent
        assert "fast-agent" in engine.baselines
        assert "slow-agent" in engine.baselines
