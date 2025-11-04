"""
SubAgent Tracking System - Test Suite

This package contains all tests for the SubAgent Tracking System.

Test Organization:
- test_schemas.py: Event schema validation tests
- test_config.py: Configuration management tests
- test_activity_logger.py: Activity logging tests
- test_snapshot_manager.py: Snapshot and recovery tests
- test_backup_manager.py: Google Drive backup tests
- test_analytics_db.py: Analytics database tests
- test_integration.py: End-to-end integration tests
- test_performance.py: Performance benchmarking tests

Usage:
    # Run all tests
    pytest tests/

    # Run specific test file
    pytest tests/test_schemas.py

    # Run with coverage
    pytest tests/ --cov=src --cov-report=html
"""

__version__ = "0.1.0-alpha"
