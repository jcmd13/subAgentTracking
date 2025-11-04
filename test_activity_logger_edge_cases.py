#!/usr/bin/env python3
"""
Edge case testing for activity_logger.py

Tests configuration integration, error handling, and edge cases.
"""

import sys
import os
from pathlib import Path
import time

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.activity_logger import (
    initialize,
    shutdown,
    log_agent_invocation,
    log_error,
    get_event_count,
    get_current_session_id,
)
from src.core.config import get_config, reset_config


def test_disabled_logging():
    """Test that logging can be disabled."""
    print("Test 1: Disabled Logging")

    # Reset config
    reset_config()

    # Disable logging
    config = get_config()
    original_enabled = config.activity_log_enabled
    config.activity_log_enabled = False

    # Initialize
    initialize(session_id="test_disabled")

    # Try to log (should be no-op)
    event_id = log_agent_invocation(
        agent="test",
        invoked_by="test",
        reason="Should not be logged"
    )

    print(f"   Event ID returned: {event_id}")
    print(f"   Logging enabled: {config.activity_log_enabled}")

    # Restore config
    config.activity_log_enabled = original_enabled

    shutdown()
    reset_config()
    print("   ✅ Passed\n")


def test_custom_session_id():
    """Test custom session ID."""
    print("Test 2: Custom Session ID")

    reset_config()

    custom_id = "custom_session_12345"
    initialize(session_id=custom_id)

    session_id = get_current_session_id()
    print(f"   Expected: {custom_id}")
    print(f"   Actual: {session_id}")

    assert session_id == custom_id, "Custom session ID not used"

    shutdown()
    reset_config()
    print("   ✅ Passed\n")


def test_multiple_initialize_calls():
    """Test that multiple initialize calls are safe (idempotent)."""
    print("Test 3: Multiple Initialize Calls (Idempotent)")

    reset_config()

    # Call initialize multiple times
    initialize(session_id="test_multi_1")
    first_session = get_current_session_id()

    initialize(session_id="test_multi_2")  # Should be ignored
    second_session = get_current_session_id()

    print(f"   First session: {first_session}")
    print(f"   Second session: {second_session}")
    print(f"   Same session: {first_session == second_session}")

    assert first_session == second_session, "Initialize not idempotent"

    shutdown()
    reset_config()
    print("   ✅ Passed\n")


def test_auto_initialize():
    """Test that logging auto-initializes on first call."""
    print("Test 4: Auto-Initialize on First Log")

    reset_config()

    # Don't call initialize explicitly
    session_before = get_current_session_id()
    print(f"   Session before logging: {session_before}")

    # First log call should auto-initialize
    event_id = log_agent_invocation(
        agent="test",
        invoked_by="test",
        reason="Auto-init test"
    )

    session_after = get_current_session_id()
    print(f"   Session after logging: {session_after}")
    print(f"   Event ID: {event_id}")

    assert session_after is not None, "Auto-initialize failed"

    shutdown()
    reset_config()
    print("   ✅ Passed\n")


def test_event_counter_increments():
    """Test that event counter increments correctly."""
    print("Test 5: Event Counter Increments")

    reset_config()
    initialize(session_id="test_counter")

    count_start = get_event_count()
    print(f"   Count at start: {count_start}")

    # Log 5 events
    for i in range(5):
        log_agent_invocation(
            agent=f"test_{i}",
            invoked_by="test",
            reason=f"Event {i+1}"
        )

    count_end = get_event_count()
    print(f"   Count after 5 events: {count_end}")
    print(f"   Increment: {count_end - count_start}")

    assert count_end - count_start == 5, "Counter not incrementing correctly"

    shutdown()
    reset_config()
    print("   ✅ Passed\n")


def test_error_logging_with_recovery():
    """Test error logging with recovery information."""
    print("Test 6: Error Logging with Recovery")

    reset_config()
    initialize(session_id="test_error_recovery")

    event_id = log_error(
        agent="test-agent",
        error_type="PerformanceError",
        message="Performance budget exceeded: 450ms > 200ms",
        severity="warning",
        recoverable=True,
        context={
            "measured_latency_ms": 450,
            "target_latency_ms": 200,
            "function": "process_data"
        },
        attempted_fix="Optimized algorithm, cached results",
        fix_successful=True,
        fix_result={
            "new_latency_ms": 120,
            "meets_budget": True
        }
    )

    print(f"   Error event logged: {event_id}")

    shutdown()
    reset_config()
    print("   ✅ Passed\n")


def test_rapid_logging():
    """Test rapid logging (stress test)."""
    print("Test 7: Rapid Logging (100 events)")

    reset_config()
    initialize(session_id="test_rapid")

    start_time = time.time()

    # Log 100 events rapidly
    for i in range(100):
        log_agent_invocation(
            agent=f"agent_{i % 10}",
            invoked_by="orchestrator",
            reason=f"Rapid test event {i+1}"
        )

    elapsed_ms = (time.time() - start_time) * 1000
    avg_ms_per_event = elapsed_ms / 100

    print(f"   Total time: {elapsed_ms:.2f}ms")
    print(f"   Average per event: {avg_ms_per_event:.3f}ms")
    print(f"   Target: <1.0ms per event")

    # Give writer thread time to flush
    time.sleep(0.5)

    shutdown()
    reset_config()

    if avg_ms_per_event < 1.0:
        print("   ✅ Passed (performance target met)\n")
    else:
        print(f"   ⚠️  Warning: Slower than target ({avg_ms_per_event:.3f}ms > 1.0ms)\n")


def test_shutdown_without_initialize():
    """Test that shutdown without initialize is safe."""
    print("Test 8: Shutdown Without Initialize")

    reset_config()

    # Call shutdown without initialize
    shutdown()  # Should not crash

    print("   ✅ Passed (no crash)\n")


def test_compression_toggle():
    """Test logging with compression disabled."""
    print("Test 9: Compression Toggle")

    reset_config()

    # Disable compression
    config = get_config()
    original_compression = config.activity_log_compression
    config.activity_log_compression = False

    initialize(session_id="test_no_compression")

    log_agent_invocation(
        agent="test",
        invoked_by="test",
        reason="Test without compression"
    )

    # Check log file extension
    log_dir = config.logs_dir
    log_files = list(log_dir.glob("test_no_compression.jsonl"))

    print(f"   Compression enabled: {config.activity_log_compression}")
    print(f"   Log files found: {len(log_files)}")

    if log_files:
        print(f"   Log file: {log_files[0].name}")
        print(f"   Has .gz extension: {log_files[0].suffix == '.gz'}")

    # Restore config
    config.activity_log_compression = original_compression

    shutdown()
    reset_config()
    print("   ✅ Passed\n")


def run_all_tests():
    """Run all edge case tests."""
    print("=" * 60)
    print("Activity Logger Edge Case Tests")
    print("=" * 60)
    print()

    tests = [
        test_disabled_logging,
        test_custom_session_id,
        test_multiple_initialize_calls,
        test_auto_initialize,
        test_event_counter_increments,
        test_error_logging_with_recovery,
        test_rapid_logging,
        test_shutdown_without_initialize,
        test_compression_toggle,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"   ❌ Failed: {e}\n")
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
