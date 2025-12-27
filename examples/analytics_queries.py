"""
Analytics Query Examples - SubAgent Tracking System

This example demonstrates how to query the analytics database to get insights
about your agent's performance, tool effectiveness, and error patterns.
"""

import sys
import os
import json
from datetime import datetime, timedelta

# Add the project root to path (adjust based on your project structure)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.analytics_db import AnalyticsDB


def example_query_agent_performance():
    """
    Demonstrates querying agent performance metrics.
    """
    print("\n" + "=" * 60)
    print("Example 1: Agent Performance Analytics")
    print("=" * 60)

    db = AnalyticsDB()

    # Get overall agent performance
    print("\n[1] Overall agent performance:")
    try:
        perf = db.query_agent_performance()
        print(f"   Total agents used: {len(perf)}")
        for agent_name, metrics in list(perf.items())[:3]:  # Show first 3
            print(f"\n   Agent: {agent_name}")
            print(f"   - Total invocations: {metrics.get('count', 0)}")
            print(f"   - Success rate: {metrics.get('success_rate', 0):.1%}")
            print(f"   - Avg duration: {metrics.get('avg_duration_ms', 0):.1f}ms")
    except Exception as e:
        print(f"   (Query example - no data yet: {e})")

    # Get performance for specific agent
    print("\n[2] Performance for specific agent (config-architect):")
    try:
        # This is a conceptual example - adapt to your actual DB schema
        perf = db.query_agent_performance()
        if "config-architect" in perf:
            agent_perf = perf["config-architect"]
            print(f"   Invocations: {agent_perf.get('count', 0)}")
            print(f"   Success rate: {agent_perf.get('success_rate', 0):.1%}")
            print(f"   Total tokens: {agent_perf.get('total_tokens', 0)}")
    except Exception as e:
        print(f"   (No data yet: {e})")


def example_query_tool_effectiveness():
    """
    Demonstrates querying tool usage and effectiveness.
    """
    print("\n" + "=" * 60)
    print("Example 2: Tool Effectiveness Analytics")
    print("=" * 60)

    db = AnalyticsDB()

    # Get tool usage stats
    print("\n[1] Tool usage statistics:")
    try:
        tools = db.query_tool_effectiveness()
        print(f"   Tools tracked: {len(tools)}")
        for tool_name, metrics in list(tools.items())[:5]:  # Show first 5
            print(f"\n   Tool: {tool_name}")
            print(f"   - Uses: {metrics.get('count', 0)}")
            print(f"   - Success rate: {metrics.get('success_rate', 0):.1%}")
            print(f"   - Avg duration: {metrics.get('avg_duration_ms', 0):.1f}ms")
    except Exception as e:
        print(f"   (Query example - no data yet: {e})")

    # Most used tools
    print("\n[2] Most frequently used tools:")
    try:
        tools = db.query_tool_effectiveness()
        sorted_tools = sorted(
            tools.items(), key=lambda x: x[1].get("count", 0), reverse=True
        )
        for tool_name, metrics in sorted_tools[:5]:
            count = metrics.get("count", 0)
            print(f"   {tool_name:20} - {count:4} uses")
    except Exception as e:
        print(f"   (No data yet: {e})")

    # Slowest tools
    print("\n[3] Slowest tools (by average duration):")
    try:
        tools = db.query_tool_effectiveness()
        sorted_tools = sorted(
            tools.items(), key=lambda x: x[1].get("avg_duration_ms", 0), reverse=True
        )
        for tool_name, metrics in sorted_tools[:5]:
            duration = metrics.get("avg_duration_ms", 0)
            print(f"   {tool_name:20} - {duration:8.1f}ms avg")
    except Exception as e:
        print(f"   (No data yet: {e})")


def example_query_error_patterns():
    """
    Demonstrates querying error patterns and trends.
    """
    print("\n" + "=" * 60)
    print("Example 3: Error Pattern Analysis")
    print("=" * 60)

    db = AnalyticsDB()

    # Get error patterns
    print("\n[1] Error patterns:")
    try:
        errors = db.query_error_patterns()
        print(f"   Total error types: {len(errors)}")
        for error_type, data in list(errors.items())[:5]:
            print(f"\n   Error: {error_type}")
            print(f"   - Count: {data.get('count', 0)}")
            print(f"   - Severity: {data.get('severity', 'unknown')}")
            print(f"   - Fixed rate: {data.get('fixed_rate', 0):.1%}")
    except Exception as e:
        print(f"   (Query example - no data yet: {e})")

    # Most common errors
    print("\n[2] Most common errors:")
    try:
        errors = db.query_error_patterns()
        sorted_errors = sorted(
            errors.items(), key=lambda x: x[1].get("count", 0), reverse=True
        )
        for error_type, data in sorted_errors[:5]:
            count = data.get("count", 0)
            print(f"   {error_type:25} - {count:3} occurrences")
    except Exception as e:
        print(f"   (No data yet: {e})")

    # Critical errors (unfixed)
    print("\n[3] Critical unfixed errors:")
    try:
        errors = db.query_error_patterns()
        critical = {
            e: d
            for e, d in errors.items()
            if d.get("severity") == "critical" and d.get("fixed_rate", 0) < 1
        }
        if critical:
            for error_type, data in critical.items():
                count = data.get("count", 0)
                print(f"   {error_type:25} - {count:3} unfixed")
        else:
            print("   ✅ No critical unfixed errors")
    except Exception as e:
        print(f"   (No data yet: {e})")


def example_query_session_summary():
    """
    Demonstrates querying session summaries and stats.
    """
    print("\n" + "=" * 60)
    print("Example 4: Session Summaries")
    print("=" * 60)

    db = AnalyticsDB()

    # Get current session summary
    print("\n[1] Current session summary:")
    try:
        summary = db.get_session_summary()
        print(f"   Session ID: {summary.get('session_id', 'N/A')}")
        print(f"   Duration: {summary.get('duration_seconds', 0):.1f}s")
        print(f"   Events logged: {summary.get('total_events', 0)}")
        print(f"   Tokens used: {summary.get('total_tokens', 0)}")
        print(f"   Agents used: {summary.get('agent_count', 0)}")
        print(f"   Tools used: {summary.get('tool_count', 0)}")
        print(f"   Errors: {summary.get('error_count', 0)}")
    except Exception as e:
        print(f"   (Query example - no data yet: {e})")

    # Get session cost estimate
    print("\n[2] Session cost estimate:")
    try:
        summary = db.get_session_summary()
        tokens = summary.get("total_tokens", 0)
        # Rough estimate: Haiku ~1M context per $1
        estimated_cost = tokens / 1_000_000
        print(f"   Total tokens: {tokens:,}")
        print(f"   Est. cost (Haiku): ${estimated_cost:.4f}")
        print(f"   Cost per agent: ${estimated_cost / max(1, summary.get('agent_count', 1)):.4f}")
    except Exception as e:
        print(f"   (No data yet: {e})")

    # Get agent efficiency
    print("\n[3] Agent efficiency metrics:")
    try:
        summary = db.get_session_summary()
        agents = summary.get("agent_count", 1)
        tools = summary.get("tool_count", 1)
        events = summary.get("total_events", 0)
        print(f"   Events per agent: {events / max(1, agents):.1f}")
        print(f"   Tools per event: {tools / max(1, events):.2f}")
        print(f"   Success rate: {summary.get('success_rate', 0):.1%}")
    except Exception as e:
        print(f"   (No data yet: {e})")


def example_query_file_operations():
    """
    Demonstrates querying file operation statistics.
    """
    print("\n" + "=" * 60)
    print("Example 5: File Operation Analytics")
    print("=" * 60)

    db = AnalyticsDB()

    print("\n[1] File operation types:")
    try:
        # File operations are tracked in the events table
        # This is a conceptual example of what you could query
        print("   Operations tracked:")
        print("   - Read operations (file access)")
        print("   - Write operations (file creation)")
        print("   - Edit operations (file modification)")
        print("   - Delete operations (file removal)")
    except Exception as e:
        print(f"   (No data yet: {e})")

    print("\n[2] Most modified files:")
    print("   (Would show files with most edit operations)")

    print("\n[3] File growth metrics:")
    print("   (Would show lines added/removed, file size changes)")


def example_decision_tracking():
    """
    Demonstrates querying agent decision patterns.
    """
    print("\n" + "=" * 60)
    print("Example 6: Decision Pattern Analysis")
    print("=" * 60)

    print("\n[1] Common decisions:")
    print("   - Which agent to use for task?")
    print("   - Which implementation approach?")
    print("   - Error recovery strategy?")

    print("\n[2] Decision confidence levels:")
    print("   - High confidence (>0.9): Trust fully")
    print("   - Medium confidence (0.7-0.9): Verify with secondary check")
    print("   - Low confidence (<0.7): Get user approval")

    print("\n[3] Decision outcomes:")
    print("   - Success: Did the chosen approach work?")
    print("   - Rework needed: Did it require iteration?")
    print("   - Failure: Did it fail?")


def example_optimization_recommendations():
    """
    Demonstrates how to use analytics for optimization.
    """
    print("\n" + "=" * 60)
    print("Example 7: Optimization Recommendations")
    print("=" * 60)

    print("\n[1] Performance optimization tips:")
    print("   • Check slowest tools and consider optimization")
    print("   • Identify frequently failing operations and automate recovery")
    print("   • Look for patterns in errors and prevent them")
    print("   • Track token usage and optimize prompts")

    print("\n[2] Cost optimization tips:")
    print("   • Switch to faster models when precision not needed")
    print("   • Batch operations to reduce overhead")
    print("   • Use snapshots to avoid token waste on recovery")
    print("   • Monitor cost per agent and per tool")

    print("\n[3] Quality optimization tips:")
    print("   • Increase validation checks for high-risk operations")
    print("   • Add more testing for error-prone agents")
    print("   • Track success rates and improve low-performing agents")
    print("   • Monitor test coverage and aim for >80%")


def example_custom_sql_queries():
    """
    Shows how to execute custom SQL queries if needed.
    """
    print("\n" + "=" * 60)
    print("Example 8: Custom SQL Queries")
    print("=" * 60)

    db = AnalyticsDB()

    print("\n[1] Using AnalyticsDB with custom queries:")
    print("   The AnalyticsDB class supports custom SQL queries.")
    print("   You have full access to the SQLite database.")

    print("\n[2] Available tables:")
    print("   • events - All logged events")
    print("   • sessions - Session summaries")
    print("   • agents - Agent performance metrics")
    print("   • tools - Tool usage statistics")
    print("   • errors - Error patterns")
    print("   • task_performance - Task execution metrics")
    print("   • context - Context usage tracking")

    print("\n[3] Example custom query:")
    print("""
    # Get all events from the last hour
    events = db.get_events_since(datetime.now() - timedelta(hours=1))
    for event in events[:10]:
        print(f"{event['timestamp']} - {event['event_type']}")
    """)

    print("\n[4] Accessing the database connection:")
    print("""
    # Direct database access if needed
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions ORDER BY created_at DESC LIMIT 5")
        sessions = cursor.fetchall()
    """)


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Analytics Query Examples")
    print("=" * 60)

    example_query_agent_performance()
    example_query_tool_effectiveness()
    example_query_error_patterns()
    example_query_session_summary()
    example_query_file_operations()
    example_decision_tracking()
    example_optimization_recommendations()
    example_custom_sql_queries()

    print("\n" + "=" * 60)
    print("✅ All query examples completed!")
    print("=" * 60)
    print("\nFor more details:")
    print("  • See README.md for complete API docs")
    print("  • Check src/core/analytics_db.py for all available methods")
    print("  • Run custom_events.py to generate sample data to query")
