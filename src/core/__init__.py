"""
SubAgent Tracking System - Core Module

This module provides the core tracking, observability, and recovery functionality
for Claude Code agentic workflows.

Key Components:
- activity_logger: Event logging system (JSONL format)
- snapshot_manager: State checkpoint system (JSON format)
- backup_manager: Google Drive cloud backup
- analytics_db: SQLite analytics database
- phase_review: End-of-phase analysis and insights
- config: Configuration management

Version: 0.1.0-alpha
"""

__version__ = "0.1.0-alpha"
__author__ = "SubAgent Tracking Team"

# Core components will be imported here as they're implemented
# from .config import Config, get_config
# from .activity_logger import log_agent_invocation, log_tool_usage, log_decision, log_validation, log_error
# from .snapshot_manager import take_snapshot, restore_snapshot, create_handoff_summary
# from .backup_manager import backup_session, restore_session, test_connection
# from .analytics_db import query_agent_performance, query_tool_effectiveness, query_error_patterns
# from .phase_review import run_phase_review

__all__ = [
    "__version__",
    # Config
    # Activity Logger
    # Snapshot Manager
    # Backup Manager
    # Analytics DB
    # Phase Review
]
