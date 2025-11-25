"""
Analytics Engine - Pattern Detection and Performance Analysis

Analyzes event data to detect patterns, identify optimization opportunities,
and flag performance regressions.

Links Back To: Main Plan → Phase 3 → Task 3.3

Features:
- Pattern detection (recurring failures, bottlenecks, inefficiencies)
- Cost analysis (token usage, expensive operations)
- Performance regression detection (comparing against baselines)
- Optimization recommendations

Usage:
    >>> from src.observability.analytics_engine import AnalyticsEngine
    >>> engine = AnalyticsEngine()
    >>> patterns = engine.detect_patterns(events)
    >>> cost_analysis = engine.analyze_costs(events)
"""

import time
import logging
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from statistics import mean, median, stdev

from src.core.event_bus import Event
from src.core.event_types import (
    AGENT_INVOKED, AGENT_COMPLETED, AGENT_FAILED,
    TOOL_USED, WORKFLOW_STARTED, WORKFLOW_COMPLETED
)

logger = logging.getLogger(__name__)


# ============================================================================
# Data Types
# ============================================================================

@dataclass
class Pattern:
    """Detected pattern in event data."""
    pattern_type: str  # "recurring_failure", "bottleneck", "inefficiency"
    severity: str  # "low", "medium", "high", "critical"
    description: str
    evidence: List[Dict[str, Any]]
    confidence: float  # 0.0 - 1.0
    recommendation: str
    detected_at: float = field(default_factory=time.time)


@dataclass
class CostAnalysis:
    """Cost analysis results."""
    total_cost: float
    total_tokens: int
    cost_by_agent: Dict[str, float]
    cost_by_operation: Dict[str, float]
    most_expensive_agents: List[Tuple[str, float]]
    most_expensive_operations: List[Tuple[str, float]]
    optimization_opportunities: List[str]
    projected_monthly_cost: float


@dataclass
class PerformanceBaseline:
    """Performance baseline for comparison."""
    agent: str
    avg_duration_ms: float
    p50_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float
    sample_count: int
    created_at: float = field(default_factory=time.time)


@dataclass
class PerformanceRegression:
    """Detected performance regression."""
    agent: str
    metric: str  # "avg_duration", "p95_duration", etc.
    baseline_value: float
    current_value: float
    degradation_percent: float
    severity: str  # "minor", "moderate", "severe"
    detected_at: float = field(default_factory=time.time)


# ============================================================================
# Analytics Engine
# ============================================================================

class AnalyticsEngine:
    """
    Analytics engine for pattern detection and performance analysis.

    Analyzes event streams to identify:
    - Recurring failures and error patterns
    - Performance bottlenecks
    - Cost optimization opportunities
    - Performance regressions

    Attributes:
        baselines: Performance baselines by agent
        history: Historical analysis results
    """

    def __init__(self):
        """Initialize analytics engine."""
        self.baselines: Dict[str, PerformanceBaseline] = {}
        self.history: List[Pattern] = []

        logger.info("AnalyticsEngine initialized")

    # ========================================================================
    # Pattern Detection
    # ========================================================================

    def detect_patterns(
        self,
        events: List[Event],
        lookback_window: int = 3600  # 1 hour
    ) -> List[Pattern]:
        """
        Detect patterns in event data.

        Args:
            events: List of events to analyze
            lookback_window: Time window in seconds (default: 1 hour)

        Returns:
            List of detected patterns
        """
        patterns = []

        # Filter to recent events
        cutoff = time.time() - lookback_window
        recent_events = [
            e for e in events
            if e.timestamp.timestamp() >= cutoff
        ]

        if not recent_events:
            return patterns

        # Detect different pattern types
        patterns.extend(self._detect_recurring_failures(recent_events))
        patterns.extend(self._detect_bottlenecks(recent_events))
        patterns.extend(self._detect_inefficiencies(recent_events))
        patterns.extend(self._detect_workflow_patterns(recent_events))

        # Store in history
        self.history.extend(patterns)

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        patterns.sort(key=lambda p: severity_order.get(p.severity, 4))

        return patterns

    def _detect_recurring_failures(self, events: List[Event]) -> List[Pattern]:
        """Detect recurring failure patterns."""
        patterns = []

        # Group failures by agent
        failures_by_agent = defaultdict(list)
        for event in events:
            if event.event_type == AGENT_FAILED:
                agent = self._extract_agent_name(event)
                if agent:
                    failures_by_agent[agent].append(event)

        # Check for recurring failures
        for agent, failures in failures_by_agent.items():
            if len(failures) >= 3:  # 3+ failures
                # Check failure rate
                total_invocations = sum(
                    1 for e in events
                    if e.event_type == AGENT_INVOKED
                    and self._extract_agent_name(e) == agent
                )

                if total_invocations > 0:
                    failure_rate = len(failures) / total_invocations

                    if failure_rate >= 0.5:  # 50%+ failure rate
                        severity = "critical" if failure_rate >= 0.8 else "high"
                        patterns.append(Pattern(
                            pattern_type="recurring_failure",
                            severity=severity,
                            description=f"Agent '{agent}' has high failure rate: {failure_rate:.1%}",
                            evidence=[{
                                "agent": agent,
                                "failures": len(failures),
                                "total_invocations": total_invocations,
                                "failure_rate": failure_rate
                            }],
                            confidence=0.9,
                            recommendation=f"Investigate '{agent}' agent failures. Check error logs and fix root cause."
                        ))

        return patterns

    def _detect_bottlenecks(self, events: List[Event]) -> List[Pattern]:
        """Detect performance bottlenecks."""
        patterns = []

        # Group completions by agent
        durations_by_agent = defaultdict(list)
        for event in events:
            if event.event_type == AGENT_COMPLETED:
                agent = self._extract_agent_name(event)
                duration = event.payload.get("duration_ms")
                if agent and duration:
                    durations_by_agent[agent].append(duration)

        # Check for slow agents
        for agent, durations in durations_by_agent.items():
            if len(durations) >= 3:
                avg_duration = mean(durations)
                p95_duration = self._percentile(sorted(durations), 95)

                # Flag if avg > 5 seconds or p95 > 10 seconds
                if avg_duration > 5000 or p95_duration > 10000:
                    severity = "high" if avg_duration > 10000 else "medium"
                    patterns.append(Pattern(
                        pattern_type="bottleneck",
                        severity=severity,
                        description=f"Agent '{agent}' is slow: avg={avg_duration:.0f}ms, p95={p95_duration:.0f}ms",
                        evidence=[{
                            "agent": agent,
                            "avg_duration_ms": avg_duration,
                            "p95_duration_ms": p95_duration,
                            "sample_count": len(durations)
                        }],
                        confidence=0.8,
                        recommendation=f"Optimize '{agent}' agent performance. Consider caching, parallelization, or algorithm improvements."
                    ))

        return patterns

    def _detect_inefficiencies(self, events: List[Event]) -> List[Pattern]:
        """Detect inefficient patterns (repeated work, excessive tool usage)."""
        patterns = []

        # Detect repeated file operations
        file_operations = defaultdict(int)
        for event in events:
            if event.event_type == TOOL_USED:
                tool = event.payload.get("tool")
                details = event.payload.get("details", {})
                file_path = details.get("file")

                if tool in ["Read", "Write", "Edit"] and file_path:
                    key = f"{tool}:{file_path}"
                    file_operations[key] += 1

        # Flag excessive operations on same file
        for op_key, count in file_operations.items():
            if count >= 5:  # 5+ operations on same file
                tool, file_path = op_key.split(":", 1)
                patterns.append(Pattern(
                    pattern_type="inefficiency",
                    severity="medium",
                    description=f"Excessive {tool} operations on '{file_path}': {count} times",
                    evidence=[{
                        "tool": tool,
                        "file": file_path,
                        "operation_count": count
                    }],
                    confidence=0.7,
                    recommendation=f"Consolidate {tool} operations on '{file_path}' to reduce overhead."
                ))

        return patterns

    def _detect_workflow_patterns(self, events: List[Event]) -> List[Pattern]:
        """Detect workflow-level patterns."""
        patterns = []

        # Group workflow events
        workflows = defaultdict(dict)
        for event in events:
            if event.event_type == WORKFLOW_STARTED:
                wf_id = event.payload.get("workflow_id")
                if wf_id:
                    workflows[wf_id]["started"] = event.timestamp.timestamp()

            elif event.event_type == WORKFLOW_COMPLETED:
                wf_id = event.payload.get("workflow_id")
                duration = event.payload.get("total_duration_ms")
                if wf_id:
                    workflows[wf_id]["completed"] = event.timestamp.timestamp()
                    workflows[wf_id]["duration_ms"] = duration

        # Check for long-running workflows
        for wf_id, data in workflows.items():
            if "duration_ms" in data and data["duration_ms"] > 60000:  # > 1 minute
                patterns.append(Pattern(
                    pattern_type="inefficiency",
                    severity="medium",
                    description=f"Long-running workflow '{wf_id}': {data['duration_ms']/1000:.1f}s",
                    evidence=[{
                        "workflow_id": wf_id,
                        "duration_ms": data["duration_ms"]
                    }],
                    confidence=0.6,
                    recommendation=f"Investigate workflow '{wf_id}' for optimization opportunities."
                ))

        return patterns

    # ========================================================================
    # Cost Analysis
    # ========================================================================

    def analyze_costs(
        self,
        events: List[Event],
        lookback_window: int = 86400  # 24 hours
    ) -> CostAnalysis:
        """
        Analyze costs from event data.

        Args:
            events: List of events to analyze
            lookback_window: Time window in seconds (default: 24 hours)

        Returns:
            CostAnalysis with breakdown and recommendations
        """
        # Filter to recent events
        cutoff = time.time() - lookback_window
        recent_events = [
            e for e in events
            if e.timestamp.timestamp() >= cutoff
        ]

        total_cost = 0.0
        total_tokens = 0
        cost_by_agent = defaultdict(float)
        cost_by_operation = defaultdict(float)
        token_by_agent = defaultdict(int)

        # Aggregate costs
        for event in recent_events:
            payload = event.payload
            cost = payload.get("cost", 0.0)
            tokens = payload.get("tokens") or payload.get("tokens_consumed", 0)

            if cost or tokens:
                total_cost += cost
                total_tokens += tokens

                # By agent
                agent = self._extract_agent_name(event)
                if agent:
                    cost_by_agent[agent] += cost
                    token_by_agent[agent] += tokens

                # By operation type
                operation = event.event_type
                cost_by_operation[operation] += cost

        # Sort by cost
        most_expensive_agents = sorted(
            cost_by_agent.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        most_expensive_operations = sorted(
            cost_by_operation.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        # Generate optimization recommendations
        optimization_opportunities = []

        if most_expensive_agents:
            top_agent, top_cost = most_expensive_agents[0]
            if top_cost > total_cost * 0.5:  # > 50% of total cost
                optimization_opportunities.append(
                    f"Agent '{top_agent}' accounts for {top_cost/total_cost:.1%} of total cost. "
                    f"Optimize this agent to reduce costs significantly."
                )

        if total_tokens > 100000:  # > 100k tokens
            avg_tokens = total_tokens / len([e for e in recent_events if e.event_type == AGENT_COMPLETED])
            optimization_opportunities.append(
                f"High token usage detected ({total_tokens:,} tokens). "
                f"Average {avg_tokens:.0f} tokens per agent. Consider reducing context size."
            )

        # Project monthly cost
        hours_in_window = lookback_window / 3600
        hourly_cost = total_cost / hours_in_window if hours_in_window > 0 else 0
        projected_monthly_cost = hourly_cost * 24 * 30

        return CostAnalysis(
            total_cost=total_cost,
            total_tokens=total_tokens,
            cost_by_agent=dict(cost_by_agent),
            cost_by_operation=dict(cost_by_operation),
            most_expensive_agents=most_expensive_agents,
            most_expensive_operations=most_expensive_operations,
            optimization_opportunities=optimization_opportunities,
            projected_monthly_cost=projected_monthly_cost
        )

    # ========================================================================
    # Performance Regression Detection
    # ========================================================================

    def update_baseline(
        self,
        agent: str,
        events: List[Event]
    ) -> PerformanceBaseline:
        """
        Update performance baseline for an agent.

        Args:
            agent: Agent name
            events: Recent events for this agent

        Returns:
            Updated performance baseline
        """
        # Extract durations
        durations = []
        for event in events:
            if (event.event_type == AGENT_COMPLETED and
                self._extract_agent_name(event) == agent):
                duration = event.payload.get("duration_ms")
                if duration:
                    durations.append(duration)

        if not durations:
            return None

        # Calculate baseline metrics
        durations_sorted = sorted(durations)
        baseline = PerformanceBaseline(
            agent=agent,
            avg_duration_ms=mean(durations),
            p50_duration_ms=self._percentile(durations_sorted, 50),
            p95_duration_ms=self._percentile(durations_sorted, 95),
            p99_duration_ms=self._percentile(durations_sorted, 99),
            sample_count=len(durations)
        )

        self.baselines[agent] = baseline
        logger.info(f"Updated baseline for agent '{agent}': avg={baseline.avg_duration_ms:.0f}ms")

        return baseline

    def detect_regressions(
        self,
        events: List[Event],
        threshold_percent: float = 20.0  # 20% degradation
    ) -> List[PerformanceRegression]:
        """
        Detect performance regressions by comparing against baselines.

        Args:
            events: Recent events to analyze
            threshold_percent: Degradation threshold (default: 20%)

        Returns:
            List of detected regressions
        """
        regressions = []

        # Group events by agent
        events_by_agent = defaultdict(list)
        for event in events:
            if event.event_type == AGENT_COMPLETED:
                agent = self._extract_agent_name(event)
                if agent:
                    events_by_agent[agent].append(event)

        # Check each agent against baseline
        for agent, agent_events in events_by_agent.items():
            if agent not in self.baselines:
                continue  # No baseline yet

            baseline = self.baselines[agent]

            # Calculate current metrics
            durations = [
                e.payload.get("duration_ms")
                for e in agent_events
                if e.payload.get("duration_ms")
            ]

            if len(durations) < 3:
                continue  # Need at least 3 samples

            durations_sorted = sorted(durations)
            current_avg = mean(durations)
            current_p95 = self._percentile(durations_sorted, 95)

            # Check for regressions
            metrics = [
                ("avg_duration", baseline.avg_duration_ms, current_avg),
                ("p95_duration", baseline.p95_duration_ms, current_p95)
            ]

            for metric_name, baseline_value, current_value in metrics:
                if baseline_value > 0:
                    degradation = ((current_value - baseline_value) / baseline_value) * 100

                    if degradation >= threshold_percent:
                        # Classify severity
                        if degradation >= 50:
                            severity = "severe"
                        elif degradation >= 30:
                            severity = "moderate"
                        else:
                            severity = "minor"

                        regressions.append(PerformanceRegression(
                            agent=agent,
                            metric=metric_name,
                            baseline_value=baseline_value,
                            current_value=current_value,
                            degradation_percent=degradation,
                            severity=severity
                        ))

        return regressions

    # ========================================================================
    # Helper Methods
    # ========================================================================

    def _extract_agent_name(self, event: Event) -> Optional[str]:
        """Extract agent name from event."""
        agent_data = event.payload.get("agent")

        if isinstance(agent_data, dict):
            return agent_data.get("name") or agent_data.get("id")
        elif isinstance(agent_data, str):
            return agent_data

        return None

    def _percentile(self, sorted_values: List[float], percentile: int) -> float:
        """Calculate percentile from sorted values."""
        if not sorted_values:
            return 0.0

        index = int((percentile / 100) * len(sorted_values))
        index = max(0, min(index, len(sorted_values) - 1))
        return sorted_values[index]


# ============================================================================
# Global Instance Management
# ============================================================================

_engine_instance: Optional[AnalyticsEngine] = None


def get_analytics_engine() -> AnalyticsEngine:
    """Get or create global analytics engine instance."""
    global _engine_instance

    if _engine_instance is None:
        _engine_instance = AnalyticsEngine()

    return _engine_instance


def reset_analytics_engine() -> None:
    """Reset global analytics engine instance."""
    global _engine_instance
    _engine_instance = None
