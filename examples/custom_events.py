"""
Advanced Event Logging Example - SubAgent Tracking System

This example demonstrates advanced usage patterns for logging different event
types and using context managers for automatic tracking.

Use this when you need more control over what gets logged and when.
"""

import sys
import os
import time

# Add the project root to path (adjust based on your project structure)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.activity_logger import (
    log_agent_invocation,
    log_tool_usage,
    log_file_operation,
    log_decision,
    log_error,
    log_validation,
    log_context_snapshot,
)
from src.core.snapshot_manager import take_snapshot


def example_agent_invocations():
    """
    Demonstrates logging different types of agent invocations.
    """
    print("\n" + "=" * 60)
    print("Example 1: Agent Invocations")
    print("=" * 60)

    # Simple agent invocation
    print("\n[1] Simple agent invocation:")
    log_agent_invocation(
        agent="config-architect",
        invoked_by="orchestrator",
        reason="Task 1.1: Implement structured logging",
    )
    print("✅ Logged: config-architect invoked")

    # Agent invocation with context
    print("\n[2] Agent invocation with context:")
    log_agent_invocation(
        agent="refactor-agent",
        invoked_by="config-architect",
        reason="Refactor authentication module",
        context={
            "task_id": "T-1.5",
            "module": "auth.py",
            "complexity": "high",
            "estimated_tokens": 50000,
        },
    )
    print("✅ Logged: refactor-agent invoked with context")

    # Agent invocation with agent status tracking
    print("\n[3] Agent invocation tracking status:")
    log_agent_invocation(
        agent="test-engineer",
        invoked_by="orchestrator",
        reason="Run integration tests",
        agent_status="in_progress",
    )
    print("✅ Logged: test-engineer status tracking")


def example_tool_usage():
    """
    Demonstrates logging tool usage with context managers.
    """
    print("\n" + "=" * 60)
    print("Example 2: Tool Usage Tracking")
    print("=" * 60)

    # Manual tool logging
    print("\n[1] Manual tool usage logging:")
    log_tool_usage(
        agent="refactor-agent",
        tool="Read",
        tool_type="file_operation",
        file_path="src/auth.py",
        status="success",
        duration_ms=45,
    )
    print("✅ Logged: Read tool usage")

    # Tool usage with context manager (automatic duration tracking)
    print("\n[2] Tool usage with context manager:")
    with log_tool_usage(
        agent="refactor-agent",
        tool="Edit",
        tool_type="file_operation",
        file_path="src/auth.py",
    ) as tool_event:
        # Simulate some work
        time.sleep(0.1)
        print("  - Editing file...")
    print("✅ Logged: Edit tool usage (duration automatically tracked)")

    # Multiple tools in sequence
    print("\n[3] Multiple tool calls:")
    tools_used = ["Read", "Edit", "Write", "Bash"]
    for tool_name in tools_used:
        log_tool_usage(
            agent="orchestrator",
            tool=tool_name,
            tool_type="execution",
            status="success",
        )
    print(f"✅ Logged: {len(tools_used)} tool calls")


def example_file_operations():
    """
    Demonstrates logging file operations.
    """
    print("\n" + "=" * 60)
    print("Example 3: File Operations")
    print("=" * 60)

    # Read operation
    print("\n[1] Read operation:")
    log_file_operation(
        agent="refactor-agent",
        operation="read",
        file_path="src/auth.py",
        status="success",
        lines_affected=245,
    )
    print("✅ Logged: Read operation on src/auth.py")

    # Write operation
    print("\n[2] Write operation:")
    log_file_operation(
        agent="refactor-agent",
        operation="write",
        file_path="src/auth_new.py",
        status="success",
        lines_affected=310,
        git_aware=True,
    )
    print("✅ Logged: Write operation on src/auth_new.py")

    # Multiple file operations
    print("\n[3] Multiple file operations:")
    files = [
        ("src/models/user.py", "edit"),
        ("src/models/session.py", "edit"),
        ("tests/test_auth.py", "write"),
    ]
    for file_path, operation in files:
        log_file_operation(
            agent="refactor-agent", operation=operation, file_path=file_path
        )
    print(f"✅ Logged: {len(files)} file operations")


def example_decisions():
    """
    Demonstrates logging decision points in agent execution.
    """
    print("\n" + "=" * 60)
    print("Example 4: Decision Logging")
    print("=" * 60)

    # Which agent to use
    print("\n[1] Agent selection decision:")
    log_decision(
        agent="orchestrator",
        question="Which agent should handle authentication refactoring?",
        options=["refactor-agent", "security-auditor", "test-engineer"],
        selected="refactor-agent",
        rationale="Code refactoring is its specialty; security auditor handles review",
        confidence=0.95,
    )
    print("✅ Logged: Agent selection decision")

    # Implementation approach decision
    print("\n[2] Implementation approach decision:")
    log_decision(
        agent="refactor-agent",
        question="Use async or sync authentication flow?",
        options=["async_with_tokens", "sync_with_cache", "hybrid_approach"],
        selected="async_with_tokens",
        rationale="Async prevents blocking; compatible with existing token system",
        confidence=0.88,
    )
    print("✅ Logged: Implementation approach decision")

    # Error recovery decision
    print("\n[3] Error recovery decision:")
    log_decision(
        agent="error-handler",
        question="How to handle authentication timeout?",
        options=["retry_with_backoff", "fallback_to_cache", "fail_fast"],
        selected="retry_with_backoff",
        rationale="User should not lose work; backoff prevents overload",
    )
    print("✅ Logged: Error recovery decision")


def example_error_handling():
    """
    Demonstrates logging errors and error recovery.
    """
    print("\n" + "=" * 60)
    print("Example 5: Error Logging")
    print("=" * 60)

    # Simple error
    print("\n[1] Error logging:")
    log_error(
        agent="refactor-agent",
        error_type="SyntaxError",
        message="Invalid Python syntax in generated code",
        context={"file": "src/auth.py", "line": 42, "attempted_fix": "Added missing colon"},
        severity="high",
    )
    print("✅ Logged: Syntax error")

    # Error with recovery
    print("\n[2] Error with recovery attempt:")
    log_error(
        agent="backup-manager",
        error_type="ConnectionError",
        message="Google Drive connection timeout",
        context={"service": "google_drive", "timeout_seconds": 30},
        attempted_fix="Retry with exponential backoff",
        fix_successful=True,
        severity="medium",
    )
    print("✅ Logged: Connection error with successful recovery")

    # Error that caused failure
    print("\n[3] Unrecovered error:")
    log_error(
        agent="test-engineer",
        error_type="TestFailure",
        message="5 integration tests failed",
        context={"tests_failed": 5, "tests_total": 120},
        severity="critical",
        fix_successful=False,
    )
    print("✅ Logged: Test failure (unrecovered)")


def example_validation():
    """
    Demonstrates logging validation results.
    """
    print("\n" + "=" * 60)
    print("Example 6: Validation Logging")
    print("=" * 60)

    # Code quality validation
    print("\n[1] Code quality validation:")
    log_validation(
        agent="refactor-agent",
        task="Refactor authentication module",
        checks={
            "syntax_valid": True,
            "imports_correct": True,
            "type_hints_present": True,
            "tests_passing": True,
            "performance_acceptable": True,
        },
        result="PASS",
        details="All checks passed. Code is ready for deployment.",
    )
    print("✅ Logged: Code quality validation (PASS)")

    # Integration test validation
    print("\n[2] Integration test validation:")
    log_validation(
        agent="test-engineer",
        task="Integration testing",
        checks={
            "end_to_end_workflow": True,
            "error_handling": True,
            "concurrent_operations": True,
            "performance_under_load": False,
        },
        result="PARTIAL",
        details="3/4 checks passed. Need to optimize for high concurrency.",
    )
    print("✅ Logged: Integration test validation (PARTIAL)")

    # Final pre-deployment validation
    print("\n[3] Pre-deployment validation:")
    log_validation(
        agent="security-auditor",
        task="Security audit before deployment",
        checks={
            "no_sql_injection": True,
            "no_xss_vulnerabilities": True,
            "credentials_secured": True,
            "rate_limiting": True,
            "audit_logging": True,
        },
        result="PASS",
        details="System is secure for production deployment.",
    )
    print("✅ Logged: Security validation (PASS)")


def example_context_snapshots():
    """
    Demonstrates logging context snapshots at key points.
    """
    print("\n" + "=" * 60)
    print("Example 7: Context Snapshots")
    print("=" * 60)

    # Snapshot before major operation
    print("\n[1] Context snapshot before refactoring:")
    log_context_snapshot(
        agent="refactor-agent",
        reason="Before major refactoring operation",
        context_summary={
            "current_file": "src/auth.py",
            "lines_of_code": 245,
            "dependencies": 8,
            "estimated_complexity": "high",
        },
    )
    print("✅ Logged: Context snapshot (before refactoring)")

    # Snapshot after operation
    print("\n[2] Context snapshot after completion:")
    log_context_snapshot(
        agent="refactor-agent",
        reason="After successful refactoring",
        context_summary={
            "files_modified": 5,
            "lines_added": 120,
            "lines_removed": 180,
            "tests_passing": 95,
            "coverage_improved": True,
        },
    )
    print("✅ Logged: Context snapshot (after refactoring)")


def example_combined_workflow():
    """
    Demonstrates a realistic workflow combining multiple event types.
    """
    print("\n" + "=" * 60)
    print("Example 8: Combined Workflow")
    print("=" * 60)

    print("\nSimulating a realistic refactoring workflow:")

    # Step 1: Agent invocation
    print("\n[Step 1] Invoking refactor agent...")
    log_agent_invocation(
        agent="refactor-agent",
        invoked_by="orchestrator",
        reason="Refactor authentication module for better performance",
    )

    # Step 2: Decision
    print("[Step 2] Making design decision...")
    log_decision(
        agent="refactor-agent",
        question="Architecture approach?",
        options=["async_jwt", "sync_session", "hybrid"],
        selected="async_jwt",
    )

    # Step 3: File operations
    print("[Step 3] Reading source file...")
    log_file_operation(
        agent="refactor-agent", operation="read", file_path="src/auth.py"
    )

    # Step 4: Tool usage
    print("[Step 4] Editing file...")
    with log_tool_usage(
        agent="refactor-agent", tool="Edit", file_path="src/auth.py"
    ):
        time.sleep(0.05)

    # Step 5: Context snapshot
    print("[Step 5] Taking progress snapshot...")
    log_context_snapshot(
        agent="refactor-agent",
        reason="Checkpoint after initial changes",
        context_summary={"progress": "50%", "files_modified": 1},
    )

    # Step 6: Validation
    print("[Step 6] Validating changes...")
    log_validation(
        agent="refactor-agent",
        task="Refactor auth module",
        checks={"syntax": True, "imports": True, "tests": True},
        result="PASS",
    )

    print("\n✅ Workflow complete! All events logged.")

    # Create a snapshot at the end
    print("\n[Step 7] Creating final snapshot...")
    snapshot_id = take_snapshot(trigger="workflow_complete")
    print(f"✅ Final snapshot: {snapshot_id}")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Advanced Event Logging Examples")
    print("=" * 60)

    example_agent_invocations()
    example_tool_usage()
    example_file_operations()
    example_decisions()
    example_error_handling()
    example_validation()
    example_context_snapshots()
    example_combined_workflow()

    print("\n" + "=" * 60)
    print("✅ All examples completed!")
    print("=" * 60)
    print("\nNext steps:")
    print("  • See analytics_queries.py to query the logged data")
    print("  • Check .claude/logs/ for the activity log")
    print("  • Check .claude/state/ for snapshots")
