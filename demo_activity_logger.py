#!/usr/bin/env python3
"""
Activity Logger Demo - Complete Feature Showcase

Demonstrates all features of the activity logger in a realistic scenario.
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
    tool_usage_context,
    agent_invocation_context,
    get_current_session_id,
    get_event_count,
)


def simulate_real_workflow():
    """Simulate a realistic multi-agent workflow."""
    print("=" * 70)
    print("Activity Logger Demo - Realistic Workflow Simulation")
    print("=" * 70)
    print()

    # Initialize
    initialize(session_id="demo_realistic_workflow")
    session_id = get_current_session_id()
    print(f"Session ID: {session_id}\n")

    # 1. Orchestrator invoked by user
    print("1. User invokes orchestrator...")
    with agent_invocation_context(
        "orchestrator",
        "user",
        "Implement activity logging system",
        context={
            "tokens_before": 5000,
            "current_phase": "Phase 1, Week 1",
        }
    ) as evt_id:
        print(f"   Event ID: {evt_id}\n")
        time.sleep(0.01)

        # 2. Orchestrator makes decision
        print("2. Orchestrator decides which agent to invoke...")
        log_decision(
            agent="orchestrator",
            question="Which agent should implement the activity logger?",
            options=[
                {
                    "choice": "config-architect",
                    "reasoning": "Activity logger is core infrastructure",
                    "confidence": 0.95
                },
                {
                    "choice": "refactor-agent",
                    "reasoning": "Could refactor existing logging",
                    "confidence": 0.30
                }
            ],
            selected="config-architect",
            rationale="Best match for infrastructure work, highest confidence"
        )
        print("   Decision logged\n")

        # 3. Config-architect invoked
        print("3. Orchestrator invokes config-architect...")
        with agent_invocation_context(
            "config-architect",
            "orchestrator",
            "Implement activity_logger.py with 7 event types",
            context={
                "tokens_before": 8000,
                "task": "Task 1.1: Activity Logging"
            }
        ) as evt_id:
            print(f"   Event ID: {evt_id}\n")
            time.sleep(0.01)

            # 4. Config-architect reads documentation
            print("4. Config-architect reads documentation...")
            with tool_usage_context(
                "config-architect",
                "Read",
                "Read AGENT_TRACKING_SYSTEM.md for event schemas"
            ):
                time.sleep(0.02)
            print("   Tool usage logged\n")

            # 5. Config-architect writes file
            print("5. Config-architect writes activity_logger.py...")
            with tool_usage_context(
                "config-architect",
                "Write",
                "Create src/core/activity_logger.py"
            ):
                time.sleep(0.03)

            log_file_operation(
                agent="config-architect",
                operation="write",
                file_path="src/core/activity_logger.py",
                size_bytes=35000,
                lines=1100,
                hash_after="a1b2c3d4e5f6...",
                diff_summary="Created complete activity logging system with 7 event types"
            )
            print("   File operation logged\n")

            # 6. Performance test fails
            print("6. Performance test fails budget...")
            log_error(
                agent="config-architect",
                error_type="PerformanceError",
                message="Event logging latency exceeds budget: 2.5ms > 1.0ms target",
                severity="warning",
                recoverable=True,
                context={
                    "measured_latency_ms": 2.5,
                    "target_latency_ms": 1.0,
                    "test": "rapid_logging_test"
                },
                attempted_fix="Switched from asyncio to threading.Queue for better sync performance",
                fix_successful=True,
                fix_result={
                    "new_latency_ms": 0.4,
                    "meets_budget": True
                }
            )
            print("   Error and recovery logged\n")

            # 7. Run validation
            print("7. Config-architect validates implementation...")
            log_validation(
                agent="config-architect",
                validation_type="implementation_complete",
                result="PASS",
                checks=[
                    {"name": "7_event_types", "pass": True},
                    {"name": "schema_validation", "pass": True},
                    {"name": "thread_safety", "pass": True},
                    {"name": "performance_budget", "pass": True, "actual": 0.4, "required": 1.0},
                    {"name": "test_coverage", "pass": False, "actual": 65, "required": 80}
                ],
                target={
                    "component": "activity_logger.py",
                    "metric": "completeness"
                },
                action_required="Add 15% more test coverage"
            )
            print("   Validation logged\n")

    # 8. Context snapshot
    print("8. Taking context snapshot...")
    log_context_snapshot(
        trigger="every_10_agents",
        snapshot={
            "tokens_used": 45000,
            "tokens_remaining": 155000,
            "agents_invoked": 2,
            "tasks_completed": 1,
            "files_modified": 1,
            "current_phase": "Phase 1, Week 1",
            "current_task": "Task 1.1: Activity Logging (Complete)",
            "active_agents": ["orchestrator", "config-architect"],
            "key_context": [
                "Implemented activity_logger.py with 7 event types",
                "Fixed performance issue (2.5ms -> 0.4ms)",
                "Validation: PASS (need more test coverage)"
            ]
        }
    )
    print("   Snapshot logged\n")

    # 9. Summary
    event_count = get_event_count()
    print("=" * 70)
    print(f"Demo Complete!")
    print(f"  Session: {session_id}")
    print(f"  Total events logged: {event_count}")
    print(f"  Log file: .claude/logs/{session_id}.jsonl.gz")
    print("=" * 70)

    # Shutdown
    shutdown()


if __name__ == "__main__":
    simulate_real_workflow()
