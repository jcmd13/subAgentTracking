"""
Insight Generation Engine - Actionable Recommendations

Generates actionable insights and recommendations from analytics data.
Uses rule-based templates to transform patterns into concrete actions.

Links Back To: Main Plan → Phase 3 → Task 3.4

Features:
- Rule-based insight generation
- Prioritized recommendations
- Markdown report generation
- Historical insight tracking

Usage:
    >>> from src.observability.insight_engine import InsightEngine
    >>> engine = InsightEngine()
    >>> insights = engine.generate_insights(patterns, cost_analysis, regressions)
    >>> report = engine.generate_report(insights)
"""

import time
import logging
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from src.observability.analytics_engine import (
    Pattern,
    CostAnalysis,
    PerformanceRegression
)

logger = logging.getLogger(__name__)


# ============================================================================
# Data Types
# ============================================================================

class InsightCategory(Enum):
    """Categories of insights."""
    PERFORMANCE = "performance"
    COST = "cost"
    RELIABILITY = "reliability"
    EFFICIENCY = "efficiency"
    QUALITY = "quality"


class InsightPriority(Enum):
    """Priority levels for insights."""
    CRITICAL = 1  # Immediate action required
    HIGH = 2      # Action needed soon
    MEDIUM = 3    # Plan to address
    LOW = 4       # Consider when convenient


@dataclass
class Insight:
    """Actionable insight with recommendation."""
    title: str
    category: InsightCategory
    priority: InsightPriority
    description: str
    impact: str  # Expected impact of taking action
    recommendation: str  # Specific action to take
    evidence: Dict[str, Any]
    effort_estimate: str  # "quick", "moderate", "significant"
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            **asdict(self),
            'category': self.category.value,
            'priority': self.priority.value,
            'generated_at_readable': datetime.fromtimestamp(self.generated_at).isoformat()
        }


@dataclass
class InsightReport:
    """Comprehensive insight report."""
    title: str
    summary: str
    insights_by_priority: Dict[InsightPriority, List[Insight]]
    insights_by_category: Dict[InsightCategory, List[Insight]]
    total_insights: int
    critical_count: int
    high_count: int
    generated_at: float = field(default_factory=time.time)


# ============================================================================
# Insight Templates
# ============================================================================

class InsightTemplates:
    """Templates for generating insights from patterns."""

    @staticmethod
    def recurring_failure_insight(pattern: Pattern) -> Insight:
        """Generate insight from recurring failure pattern."""
        agent = pattern.evidence[0].get("agent", "unknown")
        failure_rate = pattern.evidence[0].get("failure_rate", 0)

        # Determine priority based on failure rate
        if failure_rate >= 0.8:
            priority = InsightPriority.CRITICAL
            effort = "moderate"
        elif failure_rate >= 0.5:
            priority = InsightPriority.HIGH
            effort = "moderate"
        else:
            priority = InsightPriority.MEDIUM
            effort = "quick"

        return Insight(
            title=f"High Failure Rate: {agent}",
            category=InsightCategory.RELIABILITY,
            priority=priority,
            description=f"Agent '{agent}' is failing {failure_rate:.1%} of invocations, indicating a reliability issue.",
            impact=f"Reducing failures will improve workflow success rate by up to {failure_rate:.1%}.",
            recommendation=f"1. Review error logs for '{agent}'\n2. Identify root cause of failures\n3. Add error handling or fix underlying issue\n4. Add integration tests to prevent regressions",
            evidence=pattern.evidence[0],
            effort_estimate=effort
        )

    @staticmethod
    def bottleneck_insight(pattern: Pattern) -> Insight:
        """Generate insight from bottleneck pattern."""
        agent = pattern.evidence[0].get("agent", "unknown")
        avg_duration = pattern.evidence[0].get("avg_duration_ms", 0)
        p95_duration = pattern.evidence[0].get("p95_duration_ms", 0)

        # Determine priority based on duration
        if avg_duration >= 10000:
            priority = InsightPriority.HIGH
            impact_percent = 50
        else:
            priority = InsightPriority.MEDIUM
            impact_percent = 30

        return Insight(
            title=f"Performance Bottleneck: {agent}",
            category=InsightCategory.PERFORMANCE,
            priority=priority,
            description=f"Agent '{agent}' is slow (avg: {avg_duration:.0f}ms, p95: {p95_duration:.0f}ms), blocking workflow progress.",
            impact=f"Optimizing could reduce overall workflow time by {impact_percent}%.",
            recommendation=f"1. Profile '{agent}' to identify slow operations\n2. Consider caching frequently accessed data\n3. Parallelize independent operations\n4. Optimize algorithms or use faster libraries\n5. Set performance budgets and monitor",
            evidence=pattern.evidence[0],
            effort_estimate="significant"
        )

    @staticmethod
    def inefficiency_insight(pattern: Pattern) -> Insight:
        """Generate insight from inefficiency pattern."""
        evidence = pattern.evidence[0]

        # File operation inefficiency
        if "file" in evidence:
            file_path = evidence.get("file", "unknown")
            tool = evidence.get("tool", "unknown")
            count = evidence.get("operation_count", 0)

            # Format operation verb correctly
            operation_verb = {
                "Read": "read",
                "Write": "written to",
                "Edit": "edited"
            }.get(tool, f"{tool.lower()}ed")

            return Insight(
                title=f"Excessive File Operations: {file_path}",
                category=InsightCategory.EFFICIENCY,
                priority=InsightPriority.MEDIUM,
                description=f"File '{file_path}' is being {operation_verb} {count} times (tool: {tool}), indicating redundant operations.",
                impact=f"Consolidating operations could reduce I/O overhead by {(count-1)/count:.1%}.",
                recommendation=f"1. Read file once and cache in memory\n2. Batch multiple edits into single operation\n3. Review if all {count} operations are necessary\n4. Consider using file watchers instead of polling",
                evidence=evidence,
                effort_estimate="quick"
            )

        # Workflow inefficiency
        elif "workflow_id" in evidence:
            workflow_id = evidence.get("workflow_id", "unknown")
            duration = evidence.get("duration_ms", 0)

            return Insight(
                title=f"Long Workflow Duration: {workflow_id}",
                category=InsightCategory.EFFICIENCY,
                priority=InsightPriority.MEDIUM,
                description=f"Workflow '{workflow_id}' took {duration/1000:.1f}s to complete.",
                impact="Optimization could improve user experience and system throughput.",
                recommendation=f"1. Profile workflow to identify bottlenecks\n2. Parallelize independent agents\n3. Cache results of expensive operations\n4. Consider breaking into smaller workflows",
                evidence=evidence,
                effort_estimate="moderate"
            )

        # Generic inefficiency
        else:
            return Insight(
                title="Inefficient Operation Detected",
                category=InsightCategory.EFFICIENCY,
                priority=InsightPriority.LOW,
                description=pattern.description,
                impact="Optimization could improve system efficiency.",
                recommendation=pattern.recommendation,
                evidence=evidence,
                effort_estimate="moderate"
            )

    @staticmethod
    def high_cost_insight(cost_analysis: CostAnalysis) -> Optional[Insight]:
        """Generate insight from high cost analysis."""
        if not cost_analysis.most_expensive_agents:
            return None

        top_agent, top_cost = cost_analysis.most_expensive_agents[0]
        cost_percent = (top_cost / cost_analysis.total_cost * 100) if cost_analysis.total_cost > 0 else 0

        if cost_percent < 40:  # Only flag if > 40% of total
            return None

        return Insight(
            title=f"High Token Cost: {top_agent}",
            category=InsightCategory.COST,
            priority=InsightPriority.HIGH,
            description=f"Agent '{top_agent}' accounts for {cost_percent:.1f}% of total costs (${top_cost:.4f}).",
            impact=f"Reducing token usage by 50% would save ${cost_analysis.projected_monthly_cost * cost_percent / 100 * 0.5:.2f}/month.",
            recommendation=f"1. Reduce context size for '{top_agent}'\n2. Use more specific prompts to reduce output tokens\n3. Cache responses for repeated queries\n4. Consider using smaller/cheaper models for this agent\n5. Set token budgets per invocation",
            evidence={
                "agent": top_agent,
                "cost": top_cost,
                "cost_percent": cost_percent,
                "projected_monthly": cost_analysis.projected_monthly_cost
            },
            effort_estimate="moderate"
        )

    @staticmethod
    def performance_regression_insight(regression: PerformanceRegression) -> Insight:
        """Generate insight from performance regression."""
        degradation = regression.degradation_percent

        # Determine priority based on severity
        priority_map = {
            "severe": InsightPriority.CRITICAL,
            "moderate": InsightPriority.HIGH,
            "minor": InsightPriority.MEDIUM
        }
        priority = priority_map.get(regression.severity, InsightPriority.MEDIUM)

        return Insight(
            title=f"Performance Regression: {regression.agent}",
            category=InsightCategory.PERFORMANCE,
            priority=priority,
            description=f"Agent '{regression.agent}' is {degradation:.1f}% slower than baseline ({regression.metric}: {regression.baseline_value:.0f}ms → {regression.current_value:.0f}ms).",
            impact=f"Regression adds {regression.current_value - regression.baseline_value:.0f}ms per invocation.",
            recommendation=f"1. Review recent changes to '{regression.agent}'\n2. Compare current vs baseline implementation\n3. Run profiler to identify performance hotspots\n4. Rollback if necessary or optimize slow code paths\n5. Add performance tests to prevent future regressions",
            evidence={
                "agent": regression.agent,
                "metric": regression.metric,
                "baseline_ms": regression.baseline_value,
                "current_ms": regression.current_value,
                "degradation_percent": degradation,
                "severity": regression.severity
            },
            effort_estimate="significant"
        )


# ============================================================================
# Insight Engine
# ============================================================================

class InsightEngine:
    """
    Insight generation engine.

    Transforms analytics data (patterns, costs, regressions) into
    actionable insights with prioritized recommendations.

    Attributes:
        templates: Insight templates
        history: Historical insights
    """

    def __init__(self):
        """Initialize insight engine."""
        self.templates = InsightTemplates()
        self.history: List[Insight] = []

        logger.info("InsightEngine initialized")

    def generate_insights(
        self,
        patterns: List[Pattern] = None,
        cost_analysis: Optional[CostAnalysis] = None,
        regressions: List[PerformanceRegression] = None
    ) -> List[Insight]:
        """
        Generate insights from analytics data.

        Args:
            patterns: Detected patterns from analytics engine
            cost_analysis: Cost analysis results
            regressions: Performance regressions

        Returns:
            List of actionable insights, sorted by priority
        """
        insights = []

        # Generate insights from patterns
        if patterns:
            for pattern in patterns:
                insight = self._pattern_to_insight(pattern)
                if insight:
                    insights.append(insight)

        # Generate insights from cost analysis
        if cost_analysis:
            cost_insights = self._cost_analysis_to_insights(cost_analysis)
            insights.extend(cost_insights)

        # Generate insights from regressions
        if regressions:
            for regression in regressions:
                insight = self.templates.performance_regression_insight(regression)
                insights.append(insight)

        # Deduplicate by title
        seen_titles = set()
        unique_insights = []
        for insight in insights:
            if insight.title not in seen_titles:
                unique_insights.append(insight)
                seen_titles.add(insight.title)

        # Sort by priority
        unique_insights.sort(key=lambda i: i.priority.value)

        # Store in history
        self.history.extend(unique_insights)

        logger.info(f"Generated {len(unique_insights)} insights")

        return unique_insights

    def _pattern_to_insight(self, pattern: Pattern) -> Optional[Insight]:
        """Convert pattern to insight using templates."""
        template_map = {
            "recurring_failure": self.templates.recurring_failure_insight,
            "bottleneck": self.templates.bottleneck_insight,
            "inefficiency": self.templates.inefficiency_insight
        }

        template_func = template_map.get(pattern.pattern_type)
        if template_func:
            return template_func(pattern)

        return None

    def _cost_analysis_to_insights(self, cost_analysis: CostAnalysis) -> List[Insight]:
        """Generate insights from cost analysis."""
        insights = []

        # High cost agent insight
        high_cost = self.templates.high_cost_insight(cost_analysis)
        if high_cost:
            insights.append(high_cost)

        # High token usage insight
        if cost_analysis.total_tokens > 100000:
            insights.append(Insight(
                title="High Token Usage Detected",
                category=InsightCategory.COST,
                priority=InsightPriority.MEDIUM,
                description=f"System consumed {cost_analysis.total_tokens:,} tokens, indicating heavy LLM usage.",
                impact=f"Reducing tokens by 20% would save ${cost_analysis.projected_monthly_cost * 0.2:.2f}/month.",
                recommendation="1. Review context sizes for all agents\n2. Implement response caching\n3. Use smaller models where possible\n4. Optimize prompts to be more concise\n5. Set token budgets per workflow",
                evidence={
                    "total_tokens": cost_analysis.total_tokens,
                    "projected_monthly_cost": cost_analysis.projected_monthly_cost
                },
                effort_estimate="moderate"
            ))

        # Projected high monthly cost
        if cost_analysis.projected_monthly_cost > 100:
            insights.append(Insight(
                title="High Projected Monthly Cost",
                category=InsightCategory.COST,
                priority=InsightPriority.HIGH,
                description=f"Current usage projects to ${cost_analysis.projected_monthly_cost:.2f}/month.",
                impact=f"Cost optimization could reduce monthly expenses by ${cost_analysis.projected_monthly_cost * 0.3:.2f}.",
                recommendation="1. Review cost optimization opportunities listed below\n2. Implement caching strategies\n3. Use tiered models (cheaper for simple tasks)\n4. Set cost budgets and alerts\n5. Monitor cost trends weekly",
                evidence={
                    "projected_monthly_cost": cost_analysis.projected_monthly_cost,
                    "total_cost": cost_analysis.total_cost
                },
                effort_estimate="significant"
            ))

        return insights

    def generate_report(
        self,
        insights: List[Insight],
        title: str = "Observability Insights Report"
    ) -> InsightReport:
        """
        Generate comprehensive insight report.

        Args:
            insights: List of insights
            title: Report title

        Returns:
            InsightReport with organized insights
        """
        # Group by priority
        insights_by_priority = defaultdict(list)
        for insight in insights:
            insights_by_priority[insight.priority].append(insight)

        # Group by category
        insights_by_category = defaultdict(list)
        for insight in insights:
            insights_by_category[insight.category].append(insight)

        # Count by priority
        critical_count = len(insights_by_priority.get(InsightPriority.CRITICAL, []))
        high_count = len(insights_by_priority.get(InsightPriority.HIGH, []))

        # Generate summary
        summary = self._generate_summary(insights, critical_count, high_count)

        return InsightReport(
            title=title,
            summary=summary,
            insights_by_priority=dict(insights_by_priority),
            insights_by_category=dict(insights_by_category),
            total_insights=len(insights),
            critical_count=critical_count,
            high_count=high_count
        )

    def _generate_summary(
        self,
        insights: List[Insight],
        critical_count: int,
        high_count: int
    ) -> str:
        """Generate executive summary."""
        total = len(insights)

        if total == 0:
            return "No insights generated. System is performing well!"

        parts = [f"Generated {total} insights:"]

        if critical_count > 0:
            parts.append(f"{critical_count} CRITICAL issues requiring immediate attention")

        if high_count > 0:
            parts.append(f"{high_count} HIGH priority items needing action soon")

        # Top categories
        category_counts = defaultdict(int)
        for insight in insights:
            category_counts[insight.category] += 1

        top_categories = sorted(
            category_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:2]

        if top_categories:
            category_names = ", ".join(c.value for c, _ in top_categories)
            parts.append(f"Primary focus areas: {category_names}")

        return ". ".join(parts) + "."

    def generate_markdown_report(self, report: InsightReport) -> str:
        """
        Generate markdown-formatted report.

        Args:
            report: InsightReport to format

        Returns:
            Markdown-formatted string
        """
        lines = []

        # Header
        lines.append(f"# {report.title}")
        lines.append("")
        lines.append(f"**Generated**: {datetime.fromtimestamp(report.generated_at).strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(report.summary)
        lines.append("")

        # Critical & High priority insights
        if report.critical_count > 0:
            lines.append("## 🚨 Critical Issues")
            lines.append("")
            critical_insights = report.insights_by_priority.get(InsightPriority.CRITICAL, [])
            for insight in critical_insights:
                lines.extend(self._format_insight_markdown(insight))
            lines.append("")

        if report.high_count > 0:
            lines.append("## ⚠️ High Priority")
            lines.append("")
            high_insights = report.insights_by_priority.get(InsightPriority.HIGH, [])
            for insight in high_insights:
                lines.extend(self._format_insight_markdown(insight))
            lines.append("")

        # Medium priority
        medium_insights = report.insights_by_priority.get(InsightPriority.MEDIUM, [])
        if medium_insights:
            lines.append("## 📋 Medium Priority")
            lines.append("")
            for insight in medium_insights:
                lines.extend(self._format_insight_markdown(insight))
            lines.append("")

        # Low priority
        low_insights = report.insights_by_priority.get(InsightPriority.LOW, [])
        if low_insights:
            lines.append("## 💡 Low Priority")
            lines.append("")
            for insight in low_insights:
                lines.extend(self._format_insight_markdown(insight))
            lines.append("")

        return "\n".join(lines)

    def _format_insight_markdown(self, insight: Insight) -> List[str]:
        """Format single insight as markdown."""
        lines = []

        # Title with category badge
        category_emoji = {
            InsightCategory.PERFORMANCE: "⚡",
            InsightCategory.COST: "💰",
            InsightCategory.RELIABILITY: "🔒",
            InsightCategory.EFFICIENCY: "⚙️",
            InsightCategory.QUALITY: "✨"
        }
        emoji = category_emoji.get(insight.category, "📌")

        lines.append(f"### {emoji} {insight.title}")
        lines.append("")

        # Description
        lines.append(f"**Description**: {insight.description}")
        lines.append("")

        # Impact
        lines.append(f"**Impact**: {insight.impact}")
        lines.append("")

        # Recommendation
        lines.append(f"**Recommendation**:")
        lines.append("")
        lines.append(insight.recommendation)
        lines.append("")

        # Metadata
        lines.append(f"**Effort**: {insight.effort_estimate.capitalize()} | **Category**: {insight.category.value}")
        lines.append("")

        return lines


# ============================================================================
# Global Instance Management
# ============================================================================

_engine_instance: Optional[InsightEngine] = None


def get_insight_engine() -> InsightEngine:
    """Get or create global insight engine instance."""
    global _engine_instance

    if _engine_instance is None:
        _engine_instance = InsightEngine()

    return _engine_instance


def reset_insight_engine() -> None:
    """Reset global insight engine instance."""
    global _engine_instance
    _engine_instance = None
