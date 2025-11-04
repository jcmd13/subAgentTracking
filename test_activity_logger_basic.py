#!/usr/bin/env python3
"""
Basic verification script for activity_logger.py

Tests all 7 event types and core functionality.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.activity_logger import (
    initialize,
    shutdown,
    log_agent_invocation,
    log_tool_usage,
    log_file_operation,
    log_decision,
    log_error,
    log_context_snapshot,
    log_validation,
    get_current_session_id,
    get_event_count,
    tool_usage_context,
    agent_invocation_context,
)


def test_basic_logging():
    """Test basic logging functionality."""
    print("Testing Activity Logger...\n")

    # Initialize
    print("1. Initializing logger...")
    initialize()
    session_id = get_current_session_id()
    print(f"   Session ID: {session_id}")

    # Test 1: Agent Invocation
    print("\n2. Testing agent_invocation event...")
    evt1 = log_agent_invocation(
        agent="orchestrator",
        invoked_by="user",
        reason="Test basic logging",
        context={"tokens_before": 1000}
    )
    print(f"   Event ID: {evt1}")

    # Test 2: Tool Usage
    print("\n3. Testing tool_usage event...")
    evt2 = log_tool_usage(
        agent="orchestrator",
        tool="Read",
        description="Read configuration file",
        duration_ms=45.2,
        success=True
    )
    print(f"   Event ID: {evt2}")

    # Test 3: File Operation
    print("\n4. Testing file_operation event...")
    evt3 = log_file_operation(
        agent="config-architect",
        operation="write",
        file_path="src/core/logger.py",
        size_bytes=3456,
        lines=128
    )
    print(f"   Event ID: {evt3}")

    # Test 4: Decision
    print("\n5. Testing decision event...")
    evt4 = log_decision(
        agent="orchestrator",
        question="Which agent for logging?",
        options=[
            {"choice": "config-architect", "reasoning": "Infrastructure work", "confidence": 0.95},
            {"choice": "refactor-agent", "reasoning": "Could handle", "confidence": 0.30}
        ],
        selected="config-architect",
        rationale="Best match for infrastructure"
    )
    print(f"   Event ID: {evt4}")

    # Test 5: Error
    print("\n6. Testing error event...")
    evt5 = log_error(
        agent="config-architect",
        error_type="PerformanceError",
        message="Latency budget exceeded",
        severity="warning",
        context={"measured": 450, "target": 200},
        attempted_fix="Switched to orjson",
        fix_successful=True
    )
    print(f"   Event ID: {evt5}")

    # Test 6: Context Snapshot
    print("\n7. Testing context_snapshot event...")
    evt6 = log_context_snapshot(
        trigger="manual_test",
        snapshot={
            "tokens_used": 5000,
            "agents_invoked": 5,
            "tasks_completed": 1
        }
    )
    print(f"   Event ID: {evt6}")

    # Test 7: Validation
    print("\n8. Testing validation event...")
    evt7 = log_validation(
        agent="orchestrator",
        validation_type="performance_budget",
        result="PASS",
        checks=[
            {"name": "latency_budget", "pass": True},
            {"name": "memory_usage", "pass": True}
        ]
    )
    print(f"   Event ID: {evt7}")

    # Test context managers
    print("\n9. Testing tool_usage_context manager...")
    with tool_usage_context("test-agent", "Bash", "Test command") as evt_id:
        time.sleep(0.05)  # Simulate work
    print(f"   Tool context completed")

    print("\n10. Testing agent_invocation_context manager...")
    with agent_invocation_context("sub-agent", "orchestrator", "Test nested events") as evt_id:
        # This event should have the agent invocation as parent
        log_tool_usage(
            agent="sub-agent",
            tool="Write",
            description="Nested tool usage",
            success=True
        )
    print(f"   Agent context completed")

    # Check event count
    event_count = get_event_count()
    print(f"\n11. Total events logged: {event_count}")

    # Shutdown
    print("\n12. Shutting down logger...")
    shutdown()

    print("\n✅ All tests completed successfully!")
    print(f"\nCheck log file at: .claude/logs/{session_id}.jsonl.gz")


if __name__ == "__main__":
    test_basic_logging()
