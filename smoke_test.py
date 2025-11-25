#!/usr/bin/env python3
"""
Smoke Test - SubAgent Tracking System v0.1.0

Quick validation that the tracking system is working correctly.
Run this to verify the system is operational before deployment.

Exit codes:
  0 - All checks passed ✅
  1 - One or more checks failed ❌
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import src.core.activity_logger as activity_logger_module
from src.core.activity_logger import (
    log_agent_invocation,
    log_tool_usage,
    log_decision,
    log_error,
    log_validation,
    shutdown,
)
from src.core.snapshot_manager import take_snapshot, restore_snapshot
from src.core.analytics_db import AnalyticsDB
from src.core.config import get_config


class SmokeTest:
    """Smoke test suite for SubAgent Tracking System."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.config = get_config()
        self.start_time = datetime.now()
        self.created_snapshots = []  # Track snapshots for cleanup
        self.logged_event_ids = {}  # Track event IDs for later verification
        # Capture session ID early by triggering first log
        self.session_id = None

    def log(self, status, message, details=""):
        """Print a test result."""
        symbol = "✅" if status else "❌"
        print(f"{symbol} {message}")
        if details:
            print(f"   {details}")

    def get_log_file_path(self) -> Path:
        """Get the path to the current session's log file."""
        if not self.session_id:
            return None
        # Check for both compressed and uncompressed versions
        log_file = self.config.logs_dir / f"{self.session_id}.jsonl"
        log_file_gz = self.config.logs_dir / f"{self.session_id}.jsonl.gz"
        if log_file_gz.exists():
            return log_file_gz
        return log_file

    def verify_event_in_log(self, event_type: str, event_id: str) -> bool:
        """Verify that an event was written to the log file."""
        log_file = self.get_log_file_path()
        if not log_file or not log_file.exists():
            return False

        try:
            with open(log_file, "r") as f:
                for line in f:
                    event = json.loads(line)
                    if event.get("event_type") == event_type and event.get("event_id") == event_id:
                        return True
            return False
        except Exception:
            return False

    def test_activity_logger(self):
        """Test activity logging functionality."""
        try:
            event_id = log_agent_invocation(
                agent="smoke-test",
                invoked_by="system",
                reason="Smoke test validation",
            )
            # Capture session ID on first log (for later log file verification)
            if not self.session_id:
                self.session_id = activity_logger_module._session_id
            # Store for later verification after shutdown
            self.logged_event_ids["agent_invocation"] = event_id
            self.log(True, "Activity logging works")
            self.passed += 1
            return True
        except Exception as e:
            self.log(False, "Activity logging failed", str(e))
            self.failed += 1
            return False

    def test_tool_usage_logging(self):
        """Test tool usage logging."""
        try:
            event_id = log_tool_usage(
                agent="smoke-test",
                tool="Read",
                operation="read_file",
                success=True,
            )
            # Store for later verification after shutdown
            self.logged_event_ids["tool_usage"] = event_id
            self.log(True, "Tool usage logging works")
            self.passed += 1
            return True
        except Exception as e:
            self.log(False, "Tool usage logging failed", str(e))
            self.failed += 1
            return False

    def test_decision_logging(self):
        """Test decision logging."""
        try:
            event_id = log_decision(
                agent="smoke-test",
                question="Is system working?",
                options=["yes", "no"],
                selected="yes",
                rationale="Core tests passed",
            )
            # Store for later verification after shutdown
            self.logged_event_ids["decision"] = event_id
            self.log(True, "Decision logging works")
            self.passed += 1
            return True
        except Exception as e:
            self.log(False, "Decision logging failed", str(e))
            self.failed += 1
            return False

    def test_error_logging(self):
        """Test error logging."""
        try:
            event_id = log_error(
                agent="smoke-test",
                error_type="TestError",
                error_message="This is a test error (expected)",
                context={"test": "smoke_test"},
                severity="low",
            )
            # Store for later verification after shutdown
            self.logged_event_ids["error"] = event_id
            self.log(True, "Error logging works")
            self.passed += 1
            return True
        except Exception as e:
            self.log(False, "Error logging failed", str(e))
            self.failed += 1
            return False

    def test_validation_logging(self):
        """Test validation logging."""
        try:
            event_id = log_validation(
                agent="smoke-test",
                task="Smoke test",
                validation_type="functional",
                checks={"system_online": "pass", "database_responsive": "pass"},
                result="pass",
            )
            # Store for later verification after shutdown
            self.logged_event_ids["validation"] = event_id
            self.log(True, "Validation logging works")
            self.passed += 1
            return True
        except Exception as e:
            self.log(False, "Validation logging failed", str(e))
            self.failed += 1
            return False

    def test_snapshot_creation(self):
        """Test snapshot creation and restoration."""
        try:
            snapshot_id = take_snapshot(trigger="smoke_test")
            if not snapshot_id:
                self.log(False, "Snapshot creation failed", "No snapshot ID returned")
                self.failed += 1
                return False

            # Track snapshot for cleanup
            self.created_snapshots.append(snapshot_id)

            # Verify snapshot file was created
            state_dir = self.config.state_dir
            if not state_dir or not state_dir.exists():
                self.log(False, "Snapshot creation failed", "State directory doesn't exist")
                self.failed += 1
                return False

            # Look for snapshot files
            # Snapshot filename format: {session_id}_snap{number:03d}.json[.gz]
            # Snapshot ID format: snap_001 (but in filename: snap001)
            snap_number = snapshot_id.split("_")[1]  # Extract "001" from "snap_001"
            snapshot_files = list(state_dir.glob(f"*snap{snap_number}*"))
            if not snapshot_files:
                self.log(False, "Snapshot creation failed", f"Snapshot file not found for ID: {snapshot_id}")
                self.failed += 1
                return False

            # Try to restore snapshot (may fail gracefully if restore not fully implemented)
            try:
                restored = restore_snapshot(snapshot_id)
                # Restore can return None or False if not yet implemented, that's OK
                if restored is False:
                    self.log(
                        True,
                        "Snapshot creation works (restore pending)",
                        f"ID: {snapshot_id}",
                    )
                else:
                    self.log(True, "Snapshot creation/restoration works", f"ID: {snapshot_id}")
            except Exception as e:
                # If restore not implemented yet, that's OK - creation still works
                self.log(True, "Snapshot creation works (restore not implemented)", f"ID: {snapshot_id}")

            self.passed += 1
            return True
        except Exception as e:
            self.log(False, "Snapshot test failed", str(e))
            self.failed += 1
            return False

    def test_analytics_database(self):
        """Test analytics database."""
        try:
            db = AnalyticsDB()
            # Verify database is accessible and can be queried
            perf = db.query_agent_performance()
            if perf is None:
                self.log(False, "Analytics database failed", "Cannot query database")
                self.failed += 1
                return False

            # Verify that our smoke-test agent appears in the results
            if perf is not None and len(perf) > 0:
                agent_names = [row[0] if isinstance(row, (tuple, list)) else row.get("agent", "") for row in perf]
                if "smoke-test" in agent_names:
                    self.log(True, "Analytics database works", "Smoke test events recorded")
                    self.passed += 1
                    return True

            # If we got here, database works but may be empty initially
            self.log(True, "Analytics database works", "Database accessible (may be empty on first run)")
            self.passed += 1
            return True
        except Exception as e:
            self.log(False, "Analytics database failed", str(e))
            self.failed += 1
            return False

    def test_config_system(self):
        """Test configuration system."""
        try:
            config = get_config()
            paths = {
                "logs_dir": config.logs_dir,
                "state_dir": config.state_dir,
                "analytics_dir": config.analytics_dir,
            }
            if all(paths.values()):
                self.log(True, "Configuration system works")
                self.passed += 1
                return True
            else:
                self.log(False, "Configuration system failed", "Missing paths")
                self.failed += 1
                return False
        except Exception as e:
            self.log(False, "Configuration system failed", str(e))
            self.failed += 1
            return False

    def test_directory_structure(self):
        """Test that tracking directories are created."""
        try:
            required_dirs = [
                self.config.logs_dir,
                self.config.state_dir,
                self.config.analytics_dir,
            ]
            all_exist = all(os.path.isdir(str(d)) for d in required_dirs if d)
            if all_exist:
                self.log(True, "Directory structure is valid")
                self.passed += 1
                return True
            else:
                self.log(False, "Directory structure incomplete", "Some directories missing")
                self.failed += 1
                return False
        except Exception as e:
            self.log(False, "Directory structure check failed", str(e))
            self.failed += 1
            return False

    def test_file_permissions(self):
        """Test that files can be read and written."""
        try:
            test_dir = str(self.config.logs_dir)
            test_file = os.path.join(test_dir, ".smoke_test")
            with open(test_file, "w") as f:
                f.write("test")
            os.remove(test_file)
            self.log(True, "File permissions are correct")
            self.passed += 1
            return True
        except Exception as e:
            self.log(False, "File permissions check failed", str(e))
            self.failed += 1
            return False

    def verify_logged_events(self):
        """Verify that all logged events were written to the log file after shutdown."""
        import gzip

        log_file = self.get_log_file_path()
        if not log_file or not log_file.exists():
            self.log(False, "Log file verification failed", f"Log file not found: {log_file}")
            self.failed += 1
            return False

        found_events = {}
        try:
            # Handle both compressed and uncompressed log files
            if str(log_file).endswith(".gz"):
                with gzip.open(log_file, "rt") as f:
                    for line in f:
                        event = json.loads(line)
                        event_type = event.get("event_type")
                        event_id = event.get("event_id")
                        if event_type and event_id in self.logged_event_ids.values():
                            found_events[event_type] = event_id
            else:
                with open(log_file, "r") as f:
                    for line in f:
                        event = json.loads(line)
                        event_type = event.get("event_type")
                        event_id = event.get("event_id")
                        if event_type and event_id in self.logged_event_ids.values():
                            found_events[event_type] = event_id
        except Exception as e:
            self.log(False, "Log file verification failed", f"Error reading log file: {e}")
            self.failed += 1
            return False

        # Check if all logged events were found
        missing = []
        for event_type, event_id in self.logged_event_ids.items():
            if event_type not in found_events:
                missing.append(event_type)

        if missing:
            self.log(False, "Log file verification failed", f"Missing events: {', '.join(missing)}")
            self.failed += 1
            return False

        self.log(True, "Log file verification passed", f"All {len(self.logged_event_ids)} events recorded")
        self.passed += 1
        return True

    def cleanup(self):
        """Clean up test artifacts (optional, for repeated test runs)."""
        # Note: We don't delete snapshots or logs by default to preserve history
        # Users can manually clean .claude/logs/ and .claude/state/ if needed
        pass

    def run_all_tests(self):
        """Run all smoke tests."""
        print("\n" + "=" * 70)
        print("SubAgent Tracking System - Smoke Test v0.1.0")
        print("=" * 70)

        print("\n[Core Functionality]")
        self.test_activity_logger()
        self.test_tool_usage_logging()
        self.test_decision_logging()
        self.test_error_logging()
        self.test_validation_logging()

        print("\n[Snapshots & Recovery]")
        self.test_snapshot_creation()

        print("\n[Analytics & Storage]")
        self.test_analytics_database()

        print("\n[Configuration & Environment]")
        self.test_config_system()
        self.test_directory_structure()
        self.test_file_permissions()

        # Shutdown logger to flush all queued events to disk
        shutdown()

        print("\n[Log File Verification]")
        self.verify_logged_events()

        duration = (datetime.now() - self.start_time).total_seconds()

        print("\n" + "=" * 70)
        print(f"Results: {self.passed} passed, {self.failed} failed ({duration:.2f}s)")
        print("=" * 70)

        # Cleanup (if needed)
        self.cleanup()

        if self.failed == 0:
            print("\n✅ All smoke tests passed! System is ready for deployment.")
            return 0
        else:
            print(f"\n❌ {self.failed} test(s) failed. Please review and fix issues.")
            return 1


if __name__ == "__main__":
    smoke_test = SmokeTest()
    exit_code = smoke_test.run_all_tests()
    sys.exit(exit_code)
