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
import tempfile
import shutil
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.activity_logger import (
    log_agent_invocation,
    log_tool_usage,
    log_decision,
    log_error,
    log_validation,
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

    def log(self, status, message, details=""):
        """Print a test result."""
        symbol = "✅" if status else "❌"
        print(f"{symbol} {message}")
        if details:
            print(f"   {details}")

    def test_activity_logger(self):
        """Test activity logging functionality."""
        try:
            log_agent_invocation(
                agent="smoke-test",
                invoked_by="system",
                reason="Smoke test validation",
            )
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
            log_tool_usage(
                agent="smoke-test",
                tool="Read",
                tool_type="file_operation",
                status="success",
            )
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
            log_decision(
                agent="smoke-test",
                question="Is system working?",
                options=["yes", "no"],
                selected="yes",
            )
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
            log_error(
                agent="smoke-test",
                error_type="TestError",
                message="This is a test error (expected)",
                severity="low",
            )
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
            log_validation(
                agent="smoke-test",
                task="Smoke test",
                checks={"system_online": True, "database_responsive": True},
                result="PASS",
            )
            self.log(True, "Validation logging works")
            self.passed += 1
            return True
        except Exception as e:
            self.log(False, "Validation logging failed", str(e))
            self.failed += 1
            return False

    def test_snapshot_creation(self):
        """Test snapshot creation."""
        try:
            snapshot_id = take_snapshot(trigger="smoke_test")
            if snapshot_id:
                self.log(True, "Snapshot creation works", f"ID: {snapshot_id}")
                self.passed += 1
                return True
            else:
                self.log(False, "Snapshot creation failed", "No snapshot ID returned")
                self.failed += 1
                return False
        except Exception as e:
            self.log(False, "Snapshot creation failed", str(e))
            self.failed += 1
            return False

    def test_analytics_database(self):
        """Test analytics database."""
        try:
            db = AnalyticsDB()
            summary = db.get_session_summary()
            if summary:
                self.log(True, "Analytics database works")
                self.passed += 1
                return True
            else:
                self.log(False, "Analytics database failed", "No session summary")
                self.failed += 1
                return False
        except Exception as e:
            self.log(False, "Analytics database failed", str(e))
            self.failed += 1
            return False

    def test_config_system(self):
        """Test configuration system."""
        try:
            config = get_config()
            paths = {
                "log_path": config.get("activity_log_path"),
                "db_path": config.get("analytics_db_path"),
                "state_path": config.get("snapshot_dir"),
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
                self.config.get("logs_dir"),
                self.config.get("state_dir"),
                self.config.get("analytics_dir"),
            ]
            all_exist = all(os.path.isdir(d) for d in required_dirs if d)
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
            test_dir = self.config.get("logs_dir")
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

        duration = (datetime.now() - self.start_time).total_seconds()

        print("\n" + "=" * 70)
        print(f"Results: {self.passed} passed, {self.failed} failed ({duration:.2f}s)")
        print("=" * 70)

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
