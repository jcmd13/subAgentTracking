"""
Tests for Insight Generation Engine

Tests insight generation, report creation, and markdown formatting.

Links Back To: Main Plan → Phase 3 → Task 3.4
"""

import pytest
from datetime import datetime

from src.observability.analytics_engine import (
    Pattern,
    CostAnalysis,
    PerformanceRegression
)

from src.observability.insight_engine import (
    InsightEngine,
    InsightTemplates,
    InsightCategory,
    InsightPriority,
    Insight,
    InsightReport,
    get_insight_engine,
    reset_insight_engine
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def engine():
    """Create insight engine for testing."""
    reset_insight_engine()
    engine = InsightEngine()
    yield engine
    reset_insight_engine()


@pytest.fixture
def templates():
    """Create insight templates for testing."""
    return InsightTemplates()


@pytest.fixture
def sample_pattern():
    """Create sample pattern."""
    return Pattern(
        pattern_type="recurring_failure",
        severity="high",
        description="Test pattern",
        evidence=[{
            "agent": "test-agent",
            "failures": 8,
            "total_invocations": 10,
            "failure_rate": 0.8
        }],
        confidence=0.9,
        recommendation="Fix the agent"
    )


@pytest.fixture
def sample_cost_analysis():
    """Create sample cost analysis."""
    return CostAnalysis(
        total_cost=10.0,
        total_tokens=100000,
        cost_by_agent={"agent-1": 6.0, "agent-2": 4.0},
        cost_by_operation={},
        most_expensive_agents=[("agent-1", 6.0), ("agent-2", 4.0)],
        most_expensive_operations=[],
        optimization_opportunities=[],
        projected_monthly_cost=7200.0
    )


@pytest.fixture
def sample_regression():
    """Create sample performance regression."""
    return PerformanceRegression(
        agent="slow-agent",
        metric="avg_duration",
        baseline_value=1000.0,
        current_value=1300.0,
        degradation_percent=30.0,
        severity="moderate"
    )


# ============================================================================
# Template Tests
# ============================================================================

class TestInsightTemplates:
    """Test insight template generation."""

    def test_recurring_failure_insight(self, templates, sample_pattern):
        """Should generate insight from recurring failure pattern."""
        insight = templates.recurring_failure_insight(sample_pattern)

        assert insight is not None
        assert insight.category == InsightCategory.RELIABILITY
        assert insight.priority in [InsightPriority.CRITICAL, InsightPriority.HIGH]
        assert "test-agent" in insight.title
        assert "test-agent" in insight.description
        assert len(insight.recommendation) > 0

    def test_bottleneck_insight(self, templates):
        """Should generate insight from bottleneck pattern."""
        pattern = Pattern(
            pattern_type="bottleneck",
            severity="high",
            description="Slow agent",
            evidence=[{
                "agent": "slow-agent",
                "avg_duration_ms": 12000,
                "p95_duration_ms": 15000
            }],
            confidence=0.8,
            recommendation="Optimize"
        )

        insight = templates.bottleneck_insight(pattern)

        assert insight is not None
        assert insight.category == InsightCategory.PERFORMANCE
        assert insight.priority == InsightPriority.HIGH
        assert "slow-agent" in insight.title
        assert "12000" in insight.description or "12,000" in insight.description

    def test_inefficiency_insight_file_ops(self, templates):
        """Should generate insight for file operation inefficiency."""
        pattern = Pattern(
            pattern_type="inefficiency",
            severity="medium",
            description="Excessive file operations",
            evidence=[{
                "tool": "Read",
                "file": "test.py",
                "operation_count": 10
            }],
            confidence=0.7,
            recommendation="Consolidate"
        )

        insight = templates.inefficiency_insight(pattern)

        assert insight is not None
        assert insight.category == InsightCategory.EFFICIENCY
        assert "test.py" in insight.title or "test.py" in insight.description
        assert "Read" in insight.description

    def test_inefficiency_insight_workflow(self, templates):
        """Should generate insight for workflow inefficiency."""
        pattern = Pattern(
            pattern_type="inefficiency",
            severity="medium",
            description="Long workflow",
            evidence=[{
                "workflow_id": "wf-1",
                "duration_ms": 90000
            }],
            confidence=0.6,
            recommendation="Optimize"
        )

        insight = templates.inefficiency_insight(pattern)

        assert insight is not None
        assert insight.category == InsightCategory.EFFICIENCY
        assert "wf-1" in insight.title or "wf-1" in insight.description

    def test_high_cost_insight(self, templates, sample_cost_analysis):
        """Should generate insight for high cost."""
        insight = templates.high_cost_insight(sample_cost_analysis)

        assert insight is not None
        assert insight.category == InsightCategory.COST
        assert insight.priority == InsightPriority.HIGH
        assert "agent-1" in insight.title

    def test_high_cost_insight_low_percent(self, templates):
        """Should not generate insight if cost percent is low."""
        cost_analysis = CostAnalysis(
            total_cost=10.0,
            total_tokens=10000,
            cost_by_agent={"agent-1": 3.0, "agent-2": 7.0},
            cost_by_operation={},
            most_expensive_agents=[("agent-2", 7.0)],
            most_expensive_operations=[],
            optimization_opportunities=[],
            projected_monthly_cost=720.0
        )

        # agent-2 is only 70% (over 40% threshold)
        insight = templates.high_cost_insight(cost_analysis)
        assert insight is not None

        # Now test with < 40%
        cost_analysis.most_expensive_agents = [("agent-1", 3.0)]
        insight = templates.high_cost_insight(cost_analysis)
        # agent-1 is only 30% (under 40% threshold)
        assert insight is None

    def test_performance_regression_insight(self, templates, sample_regression):
        """Should generate insight from performance regression."""
        insight = templates.performance_regression_insight(sample_regression)

        assert insight is not None
        assert insight.category == InsightCategory.PERFORMANCE
        assert insight.priority == InsightPriority.HIGH
        assert "slow-agent" in insight.title
        assert "30" in insight.description  # 30% degradation


# ============================================================================
# Insight Engine Tests
# ============================================================================

class TestInsightEngine:
    """Test insight engine functionality."""

    def test_initialization(self, engine):
        """Should initialize correctly."""
        assert engine.templates is not None
        assert len(engine.history) == 0

    def test_generate_insights_empty(self, engine):
        """Should handle empty inputs."""
        insights = engine.generate_insights()

        assert len(insights) == 0

    def test_generate_insights_from_patterns(self, engine, sample_pattern):
        """Should generate insights from patterns."""
        insights = engine.generate_insights(patterns=[sample_pattern])

        assert len(insights) > 0
        insight = insights[0]
        assert insight.category == InsightCategory.RELIABILITY
        assert "test-agent" in insight.title

    def test_generate_insights_from_cost_analysis(self, engine, sample_cost_analysis):
        """Should generate insights from cost analysis."""
        insights = engine.generate_insights(cost_analysis=sample_cost_analysis)

        # Should generate at least 2 insights:
        # 1. High cost agent (agent-1 is 60%)
        # 2. High token usage (100k tokens)
        # 3. High projected monthly cost ($7200)
        assert len(insights) >= 2

        # Check for cost category insights
        cost_insights = [i for i in insights if i.category == InsightCategory.COST]
        assert len(cost_insights) > 0

    def test_generate_insights_from_regressions(self, engine, sample_regression):
        """Should generate insights from regressions."""
        insights = engine.generate_insights(regressions=[sample_regression])

        assert len(insights) > 0
        insight = insights[0]
        assert insight.category == InsightCategory.PERFORMANCE
        assert "slow-agent" in insight.title

    def test_generate_insights_deduplication(self, engine, sample_pattern):
        """Should deduplicate insights with same title."""
        # Generate twice with same pattern
        insights = engine.generate_insights(
            patterns=[sample_pattern, sample_pattern]
        )

        # Should only have 1 insight (deduplicated)
        assert len(insights) == 1

    def test_generate_insights_priority_sorting(self, engine):
        """Should sort insights by priority."""
        patterns = [
            Pattern(
                pattern_type="recurring_failure",
                severity="critical",
                description="Critical",
                evidence=[{"agent": "critical-agent", "failure_rate": 0.9}],
                confidence=0.9,
                recommendation="Fix"
            ),
            Pattern(
                pattern_type="inefficiency",
                severity="low",
                description="Minor",
                evidence=[{"tool": "Read", "file": "test.py", "operation_count": 3}],
                confidence=0.5,
                recommendation="Optimize"
            ),
            Pattern(
                pattern_type="bottleneck",
                severity="high",
                description="Slow",
                evidence=[{"agent": "slow-agent", "avg_duration_ms": 8000}],
                confidence=0.8,
                recommendation="Improve"
            )
        ]

        insights = engine.generate_insights(patterns=patterns)

        # Should be sorted by priority (critical > high > medium > low)
        priorities = [i.priority for i in insights]
        assert priorities == sorted(priorities, key=lambda p: p.value)

    def test_generate_insights_stores_history(self, engine, sample_pattern):
        """Should store insights in history."""
        initial_count = len(engine.history)

        engine.generate_insights(patterns=[sample_pattern])

        assert len(engine.history) > initial_count


# ============================================================================
# Report Generation Tests
# ============================================================================

class TestReportGeneration:
    """Test report generation functionality."""

    def test_generate_report_empty(self, engine):
        """Should handle empty insights."""
        report = engine.generate_report([])

        assert report.total_insights == 0
        assert report.critical_count == 0
        assert report.high_count == 0
        assert "No insights" in report.summary or "performing well" in report.summary

    def test_generate_report_basic(self, engine, sample_pattern):
        """Should generate report from insights."""
        insights = engine.generate_insights(patterns=[sample_pattern])
        report = engine.generate_report(insights)

        assert report.total_insights > 0
        assert len(report.summary) > 0
        assert report.generated_at > 0

    def test_generate_report_grouping(self, engine):
        """Should group insights by priority and category."""
        # Create diverse patterns
        patterns = [
            Pattern(
                pattern_type="recurring_failure",
                severity="critical",
                description="Critical failure",
                evidence=[{"agent": "agent-1", "failure_rate": 0.9}],
                confidence=0.9,
                recommendation="Fix"
            ),
            Pattern(
                pattern_type="bottleneck",
                severity="high",
                description="Bottleneck",
                evidence=[{"agent": "agent-2", "avg_duration_ms": 12000}],
                confidence=0.8,
                recommendation="Optimize"
            )
        ]

        insights = engine.generate_insights(patterns=patterns)
        report = engine.generate_report(insights)

        # Should have both priority groups
        assert InsightPriority.CRITICAL in report.insights_by_priority or \
               InsightPriority.HIGH in report.insights_by_priority

        # Should have category groups
        assert len(report.insights_by_category) > 0

    def test_generate_report_summary(self, engine):
        """Should generate meaningful summary."""
        patterns = [
            Pattern(
                pattern_type="recurring_failure",
                severity="critical",
                description="Critical",
                evidence=[{"agent": "agent-1", "failure_rate": 0.95}],
                confidence=0.9,
                recommendation="Fix"
            )
        ]

        insights = engine.generate_insights(patterns=patterns)
        report = engine.generate_report(insights)

        # Summary should mention critical issues
        assert "CRITICAL" in report.summary or "critical" in report.summary
        assert report.critical_count > 0


# ============================================================================
# Markdown Formatting Tests
# ============================================================================

class TestMarkdownFormatting:
    """Test markdown report formatting."""

    def test_generate_markdown_report(self, engine, sample_pattern):
        """Should generate markdown report."""
        insights = engine.generate_insights(patterns=[sample_pattern])
        report = engine.generate_report(insights)
        markdown = engine.generate_markdown_report(report)

        assert len(markdown) > 0
        assert "# " in markdown  # Has header
        assert "## " in markdown  # Has sections
        assert "**" in markdown  # Has bold text

    def test_markdown_includes_insights(self, engine, sample_pattern):
        """Should include insight details in markdown."""
        insights = engine.generate_insights(patterns=[sample_pattern])
        report = engine.generate_report(insights)
        markdown = engine.generate_markdown_report(report)

        # Should include insight title
        assert "test-agent" in markdown

        # Should include sections
        assert "Description" in markdown
        assert "Impact" in markdown
        assert "Recommendation" in markdown

    def test_markdown_priority_sections(self, engine):
        """Should have priority sections in markdown."""
        patterns = [
            Pattern(
                pattern_type="recurring_failure",
                severity="critical",
                description="Critical",
                evidence=[{"agent": "agent-1", "failure_rate": 0.9}],
                confidence=0.9,
                recommendation="Fix"
            ),
            Pattern(
                pattern_type="bottleneck",
                severity="high",
                description="High",
                evidence=[{"agent": "agent-2", "avg_duration_ms": 12000}],
                confidence=0.8,
                recommendation="Optimize"
            )
        ]

        insights = engine.generate_insights(patterns=patterns)
        report = engine.generate_report(insights)
        markdown = engine.generate_markdown_report(report)

        # Should have critical section
        if report.critical_count > 0:
            assert "Critical" in markdown or "CRITICAL" in markdown

        # Should have high priority section
        if report.high_count > 0:
            assert "High Priority" in markdown or "HIGH" in markdown


# ============================================================================
# Global Instance Tests
# ============================================================================

class TestGlobalInstance:
    """Test global instance management."""

    def test_get_insight_engine(self):
        """Should create and return global instance."""
        reset_insight_engine()

        engine1 = get_insight_engine()
        engine2 = get_insight_engine()

        # Should be same instance
        assert engine1 is engine2

        reset_insight_engine()

    def test_reset_insight_engine(self):
        """Should reset global instance."""
        engine1 = get_insight_engine()

        reset_insight_engine()

        engine2 = get_insight_engine()

        # Should be different instance
        assert engine1 is not engine2


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for insight engine."""

    def test_full_workflow(self, engine):
        """Should handle full workflow from analytics to markdown."""
        # Create analytics data
        patterns = [
            Pattern(
                pattern_type="recurring_failure",
                severity="high",
                description="Agent failing",
                evidence=[{"agent": "failing-agent", "failure_rate": 0.7}],
                confidence=0.9,
                recommendation="Fix failures"
            ),
            Pattern(
                pattern_type="bottleneck",
                severity="medium",
                description="Slow agent",
                evidence=[{"agent": "slow-agent", "avg_duration_ms": 6000}],
                confidence=0.8,
                recommendation="Optimize"
            )
        ]

        cost_analysis = CostAnalysis(
            total_cost=5.0,
            total_tokens=150000,
            cost_by_agent={"expensive-agent": 3.0},
            cost_by_operation={},
            most_expensive_agents=[("expensive-agent", 3.0)],
            most_expensive_operations=[],
            optimization_opportunities=[],
            projected_monthly_cost=3600.0
        )

        regression = PerformanceRegression(
            agent="regressed-agent",
            metric="avg_duration",
            baseline_value=1000.0,
            current_value=1500.0,
            degradation_percent=50.0,
            severity="severe"
        )

        # Generate insights
        insights = engine.generate_insights(
            patterns=patterns,
            cost_analysis=cost_analysis,
            regressions=[regression]
        )

        # Should have multiple insights
        assert len(insights) >= 3

        # Generate report
        report = engine.generate_report(insights, title="Test Report")

        # Verify report
        assert report.title == "Test Report"
        assert report.total_insights >= 3
        assert len(report.summary) > 0

        # Generate markdown
        markdown = engine.generate_markdown_report(report)

        # Verify markdown
        assert "# Test Report" in markdown
        assert len(markdown) > 500  # Should be substantial

        # Check that key elements are present
        assert "failing-agent" in markdown or "slow-agent" in markdown
        assert "expensive-agent" in markdown or "regressed-agent" in markdown
