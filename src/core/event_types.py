"""
Event Type Definitions & Schema Validation for SubAgentTracking Platform

This module defines all event types used in the system with JSON Schema validation
to ensure payload integrity and consistency.

Design Pattern: Schema-driven validation
Total Event Types: 33 (5 agent + 4 tool + 4 snapshot + 4 session + 3 cost + 2 workflow + 3 task + 2 test + 1 summary + 3 approval + 2 reference)
Validation: JSON Schema with jsonschema library

Links Back To: Main Plan → Phase 1 → Task 1.2
"""

import jsonschema
from typing import Dict, Any, List
from enum import Enum

from src.core.exceptions import EventValidationError

# ============================================================================
# Event Type Constants
# ============================================================================

# Agent Events (5 types)
AGENT_INVOKED = "agent.invoked"
AGENT_COMPLETED = "agent.completed"
AGENT_FAILED = "agent.failed"
AGENT_TIMEOUT = "agent.timeout"
AGENT_HANDOFF = "agent.handoff"

# Tool Events (4 types)
TOOL_USED = "tool.used"
TOOL_ERROR = "tool.error"
TOOL_PERFORMANCE = "tool.performance"
TOOL_QUOTA_EXCEEDED = "tool.quota_exceeded"

# Snapshot Events (4 types)
SNAPSHOT_CREATED = "snapshot.created"
SNAPSHOT_RESTORED = "snapshot.restored"
SNAPSHOT_FAILED = "snapshot.failed"
SNAPSHOT_CLEANUP = "snapshot.cleanup"

# Session Events (4 types)
SESSION_STARTED = "session.started"
SESSION_TOKEN_WARNING = "session.token_warning"
SESSION_HANDOFF_REQUIRED = "session.handoff_required"
SESSION_ENDED = "session.ended"

# Cost Events (3 types)
COST_TRACKED = "cost.tracked"
COST_BUDGET_WARNING = "cost.budget_warning"
COST_OPTIMIZATION_OPPORTUNITY = "cost.optimization_opportunity"

# Workflow Events (2 types) - Added in Phase 2
WORKFLOW_STARTED = "workflow.started"
WORKFLOW_COMPLETED = "workflow.completed"

# Task Lifecycle Events (3 types)
TASK_STARTED = "task.started"
TASK_STAGE_CHANGED = "task.stage_changed"
TASK_COMPLETED = "task.completed"

# Test Telemetry Events (2 types)
TEST_RUN_STARTED = "test.run_started"
TEST_RUN_COMPLETED = "test.run_completed"

# Session Summary Events (1 type)
SESSION_SUMMARY = "session.summary"

# Approval Events (3 types)
APPROVAL_REQUIRED = "approval.required"
APPROVAL_GRANTED = "approval.granted"
APPROVAL_DENIED = "approval.denied"

# Reference Check Events (2 types)
REFERENCE_CHECK_TRIGGERED = "reference_check.triggered"
REFERENCE_CHECK_COMPLETED = "reference_check.completed"

# Base event types (20, per specification)
BASE_EVENT_TYPES = [
    # Agent events
    AGENT_INVOKED, AGENT_COMPLETED, AGENT_FAILED, AGENT_TIMEOUT, AGENT_HANDOFF,
    # Tool events
    TOOL_USED, TOOL_ERROR, TOOL_PERFORMANCE, TOOL_QUOTA_EXCEEDED,
    # Snapshot events
    SNAPSHOT_CREATED, SNAPSHOT_RESTORED, SNAPSHOT_FAILED, SNAPSHOT_CLEANUP,
    # Session events
    SESSION_STARTED, SESSION_TOKEN_WARNING, SESSION_HANDOFF_REQUIRED, SESSION_ENDED,
    # Cost events
    COST_TRACKED, COST_BUDGET_WARNING, COST_OPTIMIZATION_OPPORTUNITY
]

# All event types (includes workflow extensions)
ALL_EVENT_TYPES = BASE_EVENT_TYPES + [
    WORKFLOW_STARTED,
    WORKFLOW_COMPLETED,
    TASK_STARTED,
    TASK_STAGE_CHANGED,
    TASK_COMPLETED,
    TEST_RUN_STARTED,
    TEST_RUN_COMPLETED,
    SESSION_SUMMARY,
    APPROVAL_REQUIRED,
    APPROVAL_GRANTED,
    APPROVAL_DENIED,
    REFERENCE_CHECK_TRIGGERED,
    REFERENCE_CHECK_COMPLETED,
]

# ============================================================================
# Known Agent Names (for validation)
# ============================================================================

KNOWN_AGENTS = [
    "orchestrator-agent",
    "refactor-agent",
    "ui-builder",
    "config-architect",
    "audio-specialist",
    "security-auditor",
    "project-manager-agent",
    "doc-writer",
    "performance-agent",
    "plugin-builder",
    "test-engineer",
    "general-purpose",
    "statusline-setup",
    "Explore",
    "Plan"
]

# ============================================================================
# Known Tool Names (for validation)
# ============================================================================

KNOWN_TOOLS = [
    "Read",
    "Write",
    "Edit",
    "Bash",
    "Glob",
    "Grep",
    "Task",
    "WebFetch",
    "WebSearch",
    "TodoWrite",
    "AskUserQuestion",
    "NotebookEdit",
    "SlashCommand",
    "Skill"
]

# ============================================================================
# Model Tier Definitions (for validation)
# ============================================================================

class ModelTier(str, Enum):
    """Model tier classification"""
    WEAK = "weak"    # Haiku, Ollama local models
    BASE = "base"    # Sonnet, Gemini 2.5 Pro
    STRONG = "strong"  # Opus, GPT-5

# ============================================================================
# JSON Schema Definitions
# ============================================================================

# Schema for AGENT_INVOKED
AGENT_INVOKED_SCHEMA = {
    "type": "object",
    "required": ["agent", "invoked_by", "reason"],
    "properties": {
        "agent": {
            "type": "string",
            "description": "Name of the agent being invoked"
        },
        "invoked_by": {
            "type": "string",
            "description": "Name of the caller (agent or 'user')"
        },
        "reason": {
            "type": "string",
            "minLength": 10,
            "description": "Reason for invocation (must be descriptive)"
        },
        "model_tier": {
            "type": "string",
            "enum": ["weak", "base", "strong"],
            "description": "Model tier to use (optional)"
        },
        "context_tokens": {
            "type": "integer",
            "minimum": 0,
            "description": "Estimated context size in tokens (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for AGENT_COMPLETED
AGENT_COMPLETED_SCHEMA = {
    "type": "object",
    "required": ["agent", "duration_ms", "tokens_used", "exit_code"],
    "properties": {
        "agent": {
            "type": "string",
            "description": "Name of the agent that completed"
        },
        "duration_ms": {
            "type": "integer",
            "minimum": 0,
            "description": "Execution time in milliseconds"
        },
        "tokens_used": {
            "type": "integer",
            "minimum": 0,
            "description": "Total tokens consumed"
        },
        "input_tokens": {
            "type": "integer",
            "minimum": 0,
            "description": "Input tokens (optional)"
        },
        "output_tokens": {
            "type": "integer",
            "minimum": 0,
            "description": "Output tokens (optional)"
        },
        "exit_code": {
            "type": "integer",
            "description": "Exit status (0=success, non-zero=error)"
        },
        "model": {
            "type": "string",
            "description": "Model used (e.g., 'claude-sonnet-4')"
        },
        "result_summary": {
            "type": "string",
            "description": "Brief summary of results (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for AGENT_FAILED
AGENT_FAILED_SCHEMA = {
    "type": "object",
    "required": ["agent", "error_type", "error_msg"],
    "properties": {
        "agent": {
            "type": "string",
            "description": "Name of the agent that failed"
        },
        "error_type": {
            "type": "string",
            "description": "Error category (e.g., 'ValidationError', 'TimeoutError')"
        },
        "error_msg": {
            "type": "string",
            "description": "Error message"
        },
        "retry_count": {
            "type": "integer",
            "minimum": 0,
            "description": "Number of retries attempted (optional)"
        },
        "stack_trace": {
            "type": "string",
            "description": "Stack trace (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for AGENT_TIMEOUT
AGENT_TIMEOUT_SCHEMA = {
    "type": "object",
    "required": ["agent", "timeout_ms"],
    "properties": {
        "agent": {
            "type": "string",
            "description": "Name of the agent that timed out"
        },
        "timeout_ms": {
            "type": "integer",
            "minimum": 0,
            "description": "Timeout threshold in milliseconds"
        },
        "partial_output": {
            "type": "string",
            "description": "Partial output before timeout (optional)"
        },
        "elapsed_ms": {
            "type": "integer",
            "minimum": 0,
            "description": "Time elapsed before timeout (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for AGENT_HANDOFF
AGENT_HANDOFF_SCHEMA = {
    "type": "object",
    "required": ["from_agent", "to_agent", "context_summary"],
    "properties": {
        "from_agent": {
            "type": "string",
            "description": "Agent handing off control"
        },
        "to_agent": {
            "type": "string",
            "description": "Agent receiving control"
        },
        "context_summary": {
            "type": "string",
            "minLength": 20,
            "description": "Summary of context being handed off"
        },
        "handoff_reason": {
            "type": "string",
            "description": "Reason for handoff (optional)"
        },
        "files_modified": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of files modified (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for TOOL_USED
TOOL_USED_SCHEMA = {
    "type": "object",
    "required": ["agent", "tool", "success"],
    "properties": {
        "agent": {
            "type": "string",
            "description": "Agent that used the tool"
        },
        "tool": {
            "type": "string",
            "description": "Tool name (e.g., 'Read', 'Write', 'Edit')"
        },
        "args": {
            "type": "object",
            "description": "Tool arguments (optional)"
        },
        "success": {
            "type": "boolean",
            "description": "Whether tool execution succeeded"
        },
        "duration_ms": {
            "type": "integer",
            "minimum": 0,
            "description": "Execution time in milliseconds (optional)"
        },
        "result_size_bytes": {
            "type": "integer",
            "minimum": 0,
            "description": "Size of result in bytes (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for TOOL_ERROR
TOOL_ERROR_SCHEMA = {
    "type": "object",
    "required": ["agent", "tool", "error_type"],
    "properties": {
        "agent": {
            "type": "string",
            "description": "Agent that encountered tool error"
        },
        "tool": {
            "type": "string",
            "description": "Tool that failed"
        },
        "error_type": {
            "type": "string",
            "description": "Error type (e.g., 'FileNotFoundError')"
        },
        "error_msg": {
            "type": "string",
            "description": "Error message (optional)"
        },
        "attempted_fix": {
            "type": "string",
            "description": "Fix that was attempted (optional)"
        },
        "fix_successful": {
            "type": "boolean",
            "description": "Whether fix worked (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for TOOL_PERFORMANCE
TOOL_PERFORMANCE_SCHEMA = {
    "type": "object",
    "required": ["tool", "duration_ms"],
    "properties": {
        "tool": {
            "type": "string",
            "description": "Tool being measured"
        },
        "duration_ms": {
            "type": "integer",
            "minimum": 0,
            "description": "Execution time in milliseconds"
        },
        "result_size_bytes": {
            "type": "integer",
            "minimum": 0,
            "description": "Size of result (optional)"
        },
        "operation": {
            "type": "string",
            "description": "Specific operation (e.g., 'read_file', 'search') (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for TOOL_QUOTA_EXCEEDED
TOOL_QUOTA_EXCEEDED_SCHEMA = {
    "type": "object",
    "required": ["tool", "quota_type", "limit", "current"],
    "properties": {
        "tool": {
            "type": "string",
            "description": "Tool that exceeded quota"
        },
        "quota_type": {
            "type": "string",
            "description": "Type of quota (e.g., 'api_calls', 'tokens')"
        },
        "limit": {
            "type": "integer",
            "minimum": 0,
            "description": "Quota limit"
        },
        "current": {
            "type": "integer",
            "minimum": 0,
            "description": "Current usage"
        },
        "reset_time": {
            "type": "string",
            "description": "When quota resets (ISO8601) (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for SNAPSHOT_CREATED
SNAPSHOT_CREATED_SCHEMA = {
    "type": "object",
    "required": ["snapshot_id", "trigger", "size_bytes"],
    "properties": {
        "snapshot_id": {
            "type": "string",
            "description": "Unique snapshot identifier"
        },
        "trigger": {
            "type": "string",
            "description": "What triggered snapshot (e.g., 'agent_count_10', 'manual')"
        },
        "size_bytes": {
            "type": "integer",
            "minimum": 0,
            "description": "Snapshot size in bytes"
        },
        "files_changed": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of files included (optional)"
        },
        "git_hash": {
            "type": "string",
            "description": "Git commit hash (optional)"
        },
        "compression": {
            "type": "string",
            "enum": ["none", "gzip", "zstd"],
            "description": "Compression method (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for SNAPSHOT_RESTORED
SNAPSHOT_RESTORED_SCHEMA = {
    "type": "object",
    "required": ["snapshot_id", "restore_strategy"],
    "properties": {
        "snapshot_id": {
            "type": "string",
            "description": "Snapshot being restored"
        },
        "restore_strategy": {
            "type": "string",
            "enum": ["full", "partial", "code_only", "state_only"],
            "description": "Restoration strategy"
        },
        "files_restored": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Files restored (optional)"
        },
        "success": {
            "type": "boolean",
            "description": "Whether restore succeeded (optional)"
        },
        "duration_ms": {
            "type": "integer",
            "minimum": 0,
            "description": "Time to restore (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for SNAPSHOT_FAILED
SNAPSHOT_FAILED_SCHEMA = {
    "type": "object",
    "required": ["trigger", "error_msg"],
    "properties": {
        "trigger": {
            "type": "string",
            "description": "What triggered the failed snapshot"
        },
        "error_msg": {
            "type": "string",
            "description": "Error message"
        },
        "partial_data": {
            "type": "boolean",
            "description": "Whether partial snapshot was saved (optional)"
        },
        "disk_space_available": {
            "type": "integer",
            "minimum": 0,
            "description": "Available disk space in bytes (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for SNAPSHOT_CLEANUP
SNAPSHOT_CLEANUP_SCHEMA = {
    "type": "object",
    "required": ["deleted_count", "space_freed_bytes"],
    "properties": {
        "deleted_count": {
            "type": "integer",
            "minimum": 0,
            "description": "Number of snapshots deleted"
        },
        "space_freed_bytes": {
            "type": "integer",
            "minimum": 0,
            "description": "Disk space freed"
        },
        "retention_policy": {
            "type": "string",
            "description": "Policy used (e.g., 'keep_last_2_sessions') (optional)"
        },
        "oldest_kept": {
            "type": "string",
            "description": "Oldest snapshot kept (ISO8601) (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for SESSION_STARTED
SESSION_STARTED_SCHEMA = {
    "type": "object",
    "required": ["session_id"],
    "properties": {
        "session_id": {
            "type": "string",
            "description": "Unique session identifier"
        },
        "phase": {
            "type": "integer",
            "minimum": 0,
            "description": "Project phase number (optional)"
        },
        "initial_context": {
            "type": "string",
            "description": "Initial context/prompt (optional)"
        },
        "resumed_from": {
            "type": "string",
            "description": "Previous session ID if resuming (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for SESSION_TOKEN_WARNING
SESSION_TOKEN_WARNING_SCHEMA = {
    "type": "object",
    "required": ["session_id", "tokens_used", "tokens_limit", "percent"],
    "properties": {
        "session_id": {
            "type": "string",
            "description": "Session ID"
        },
        "tokens_used": {
            "type": "integer",
            "minimum": 0,
            "description": "Tokens used so far"
        },
        "tokens_limit": {
            "type": "integer",
            "minimum": 0,
            "description": "Token limit for session"
        },
        "percent": {
            "type": "number",
            "minimum": 0,
            "maximum": 100,
            "description": "Percentage of limit used"
        },
        "recommendation": {
            "type": "string",
            "description": "Recommended action (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for SESSION_HANDOFF_REQUIRED
SESSION_HANDOFF_REQUIRED_SCHEMA = {
    "type": "object",
    "required": ["session_id", "reason"],
    "properties": {
        "session_id": {
            "type": "string",
            "description": "Session requiring handoff"
        },
        "reason": {
            "type": "string",
            "enum": ["token_limit", "time_limit", "manual", "error_cascade"],
            "description": "Why handoff is required"
        },
        "handoff_summary": {
            "type": "string",
            "description": "Summary for next session (optional)"
        },
        "snapshot_id": {
            "type": "string",
            "description": "Snapshot ID to restore from (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for SESSION_ENDED
SESSION_ENDED_SCHEMA = {
    "type": "object",
    "required": ["session_id", "duration_minutes", "total_tokens"],
    "properties": {
        "session_id": {
            "type": "string",
            "description": "Session that ended"
        },
        "duration_minutes": {
            "type": "number",
            "minimum": 0,
            "description": "Session duration in minutes"
        },
        "total_tokens": {
            "type": "integer",
            "minimum": 0,
            "description": "Total tokens used"
        },
        "total_cost": {
            "type": "number",
            "minimum": 0,
            "description": "Total cost in USD (optional)"
        },
        "agents_invoked": {
            "type": "integer",
            "minimum": 0,
            "description": "Number of agents invoked (optional)"
        },
        "snapshots_created": {
            "type": "integer",
            "minimum": 0,
            "description": "Number of snapshots created (optional)"
        },
        "exit_reason": {
            "type": "string",
            "description": "Why session ended (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for COST_TRACKED
COST_TRACKED_SCHEMA = {
    "type": "object",
    "required": ["model", "tokens", "cost_usd"],
    "properties": {
        "model": {
            "type": "string",
            "description": "Model name (e.g., 'claude-sonnet-4')"
        },
        "tokens": {
            "type": "integer",
            "minimum": 0,
            "description": "Total tokens (input + output)"
        },
        "input_tokens": {
            "type": "integer",
            "minimum": 0,
            "description": "Input tokens (optional)"
        },
        "output_tokens": {
            "type": "integer",
            "minimum": 0,
            "description": "Output tokens (optional)"
        },
        "cost_usd": {
            "type": "number",
            "minimum": 0,
            "description": "Cost in USD"
        },
        "operation": {
            "type": "string",
            "description": "Operation type (optional)"
        },
        "session_total": {
            "type": "number",
            "minimum": 0,
            "description": "Running session total (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for COST_BUDGET_WARNING
COST_BUDGET_WARNING_SCHEMA = {
    "type": "object",
    "required": ["budget_type", "spent", "limit", "percent"],
    "properties": {
        "budget_type": {
            "type": "string",
            "enum": ["hourly", "daily", "weekly", "monthly", "session"],
            "description": "Budget period type"
        },
        "spent": {
            "type": "number",
            "minimum": 0,
            "description": "Amount spent (USD)"
        },
        "limit": {
            "type": "number",
            "minimum": 0,
            "description": "Budget limit (USD)"
        },
        "percent": {
            "type": "number",
            "minimum": 0,
            "maximum": 100,
            "description": "Percentage of budget used"
        },
        "recommendation": {
            "type": "string",
            "description": "Recommended action (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for COST_OPTIMIZATION_OPPORTUNITY
COST_OPTIMIZATION_OPPORTUNITY_SCHEMA = {
    "type": "object",
    "required": ["recommendation", "potential_savings"],
    "properties": {
        "recommendation": {
            "type": "string",
            "description": "Optimization recommendation"
        },
        "potential_savings": {
            "type": "number",
            "minimum": 0,
            "description": "Estimated savings (USD)"
        },
        "current_model": {
            "type": "string",
            "description": "Current model being used (optional)"
        },
        "suggested_model": {
            "type": "string",
            "description": "Suggested cheaper model (optional)"
        },
        "confidence": {
            "type": "string",
            "enum": ["low", "medium", "high"],
            "description": "Confidence in recommendation (optional)"
        },
        "rationale": {
            "type": "string",
            "description": "Why this optimization is suggested (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for WORKFLOW_STARTED
WORKFLOW_STARTED_SCHEMA = {
    "type": "object",
    "required": ["workflow_id", "task_count"],
    "properties": {
        "workflow_id": {
            "type": "string",
            "description": "Unique workflow identifier"
        },
        "task_count": {
            "type": "integer",
            "minimum": 1,
            "description": "Number of tasks in workflow"
        },
        "metadata": {
            "type": "object",
            "description": "Workflow metadata (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for WORKFLOW_COMPLETED
WORKFLOW_COMPLETED_SCHEMA = {
    "type": "object",
    "required": ["workflow_id", "task_count"],
    "properties": {
        "workflow_id": {
            "type": "string",
            "description": "Unique workflow identifier"
        },
        "task_count": {
            "type": "integer",
            "minimum": 1,
            "description": "Number of tasks in workflow"
        },
        "metadata": {
            "type": "object",
            "description": "Workflow metadata (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for TASK_STARTED
TASK_STARTED_SCHEMA = {
    "type": "object",
    "required": ["task_id", "task_name", "stage"],
    "properties": {
        "task_id": {
            "type": "string",
            "description": "Unique task identifier"
        },
        "task_name": {
            "type": "string",
            "description": "Human-readable task name"
        },
        "stage": {
            "type": "string",
            "description": "Current task stage (e.g., plan, implement, test)"
        },
        "summary": {
            "type": "string",
            "description": "Brief task summary (optional)"
        },
        "eta_minutes": {
            "type": "number",
            "minimum": 0,
            "description": "Estimated minutes to completion (optional)"
        },
        "owner": {
            "type": "string",
            "description": "Agent or user responsible (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for TASK_STAGE_CHANGED
TASK_STAGE_CHANGED_SCHEMA = {
    "type": "object",
    "required": ["task_id", "stage"],
    "properties": {
        "task_id": {
            "type": "string",
            "description": "Unique task identifier"
        },
        "task_name": {
            "type": "string",
            "description": "Human-readable task name (optional)"
        },
        "stage": {
            "type": "string",
            "description": "New task stage"
        },
        "previous_stage": {
            "type": "string",
            "description": "Previous task stage (optional)"
        },
        "summary": {
            "type": "string",
            "description": "Brief stage summary (optional)"
        },
        "progress_pct": {
            "type": "number",
            "minimum": 0,
            "maximum": 100,
            "description": "Progress percentage (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for TASK_COMPLETED
TASK_COMPLETED_SCHEMA = {
    "type": "object",
    "required": ["task_id", "status"],
    "properties": {
        "task_id": {
            "type": "string",
            "description": "Unique task identifier"
        },
        "task_name": {
            "type": "string",
            "description": "Human-readable task name (optional)"
        },
        "status": {
            "type": "string",
            "enum": ["success", "failed", "warning"],
            "description": "Completion status"
        },
        "summary": {
            "type": "string",
            "description": "Completion summary (optional)"
        },
        "duration_ms": {
            "type": "integer",
            "minimum": 0,
            "description": "Task duration in milliseconds (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for TEST_RUN_STARTED
TEST_RUN_STARTED_SCHEMA = {
    "type": "object",
    "required": ["test_suite"],
    "properties": {
        "test_suite": {
            "type": "string",
            "description": "Test suite name (e.g., unit, integration)"
        },
        "task_id": {
            "type": "string",
            "description": "Related task ID (optional)"
        },
        "command": {
            "type": "string",
            "description": "Command executed (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for TEST_RUN_COMPLETED
TEST_RUN_COMPLETED_SCHEMA = {
    "type": "object",
    "required": ["test_suite", "status"],
    "properties": {
        "test_suite": {
            "type": "string",
            "description": "Test suite name"
        },
        "task_id": {
            "type": "string",
            "description": "Related task ID (optional)"
        },
        "status": {
            "type": "string",
            "enum": ["passed", "failed", "warning"],
            "description": "Test run result"
        },
        "duration_ms": {
            "type": "integer",
            "minimum": 0,
            "description": "Duration in milliseconds (optional)"
        },
        "passed": {
            "type": "integer",
            "minimum": 0,
            "description": "Number of tests passed (optional)"
        },
        "failed": {
            "type": "integer",
            "minimum": 0,
            "description": "Number of tests failed (optional)"
        },
        "summary": {
            "type": "string",
            "description": "Short test summary (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for SESSION_SUMMARY
SESSION_SUMMARY_SCHEMA = {
    "type": "object",
    "required": ["summary_type", "summary_text"],
    "properties": {
        "summary_type": {
            "type": "string",
            "enum": ["start", "end"],
            "description": "Summary timing (start/end)"
        },
        "summary_text": {
            "type": "string",
            "description": "Human-readable summary"
        },
        "summary_data": {
            "type": "object",
            "description": "Structured summary data (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for APPROVAL_REQUIRED
APPROVAL_REQUIRED_SCHEMA = {
    "type": "object",
    "required": ["approval_id", "tool", "risk_score", "reasons", "action"],
    "properties": {
        "approval_id": {
            "type": "string",
            "description": "Approval request identifier"
        },
        "tool": {
            "type": "string",
            "description": "Tool name triggering the approval"
        },
        "operation": {
            "type": "string",
            "description": "Operation name (optional)"
        },
        "file_path": {
            "type": "string",
            "description": "Target path (optional)"
        },
        "risk_score": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Normalized risk score"
        },
        "reasons": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Reasons contributing to risk"
        },
        "action": {
            "type": "string",
            "enum": ["required", "blocked"],
            "description": "Approval action taken"
        },
        "agent": {
            "type": "string",
            "description": "Agent requesting approval (optional)"
        },
        "profile": {
            "type": "string",
            "description": "Permission profile used (optional)"
        },
        "requires_network": {
            "type": "boolean",
            "description": "Network access requested (optional)"
        },
        "requires_bash": {
            "type": "boolean",
            "description": "Shell access requested (optional)"
        },
        "modifies_tests": {
            "type": "boolean",
            "description": "Operation modifies tests (optional)"
        },
        "summary": {
            "type": "string",
            "description": "Short summary of the approval request (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for APPROVAL_GRANTED
APPROVAL_GRANTED_SCHEMA = {
    "type": "object",
    "required": ["approval_id", "status"],
    "properties": {
        "approval_id": {
            "type": "string",
            "description": "Approval request identifier"
        },
        "status": {
            "type": "string",
            "enum": ["granted"],
            "description": "Decision status"
        },
        "actor": {
            "type": "string",
            "description": "Actor approving the request (optional)"
        },
        "reason": {
            "type": "string",
            "description": "Decision rationale (optional)"
        },
        "tool": {
            "type": "string",
            "description": "Tool name associated with approval (optional)"
        },
        "operation": {
            "type": "string",
            "description": "Operation name (optional)"
        },
        "file_path": {
            "type": "string",
            "description": "Target path (optional)"
        },
        "risk_score": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Normalized risk score (optional)"
        },
        "reasons": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Reasons contributing to risk (optional)"
        },
        "summary": {
            "type": "string",
            "description": "Short summary of the approval request (optional)"
        },
        "decided_at": {
            "type": "string",
            "description": "Decision timestamp (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for APPROVAL_DENIED
APPROVAL_DENIED_SCHEMA = {
    "type": "object",
    "required": ["approval_id", "status"],
    "properties": {
        "approval_id": {
            "type": "string",
            "description": "Approval request identifier"
        },
        "status": {
            "type": "string",
            "enum": ["denied"],
            "description": "Decision status"
        },
        "actor": {
            "type": "string",
            "description": "Actor denying the request (optional)"
        },
        "reason": {
            "type": "string",
            "description": "Decision rationale (optional)"
        },
        "tool": {
            "type": "string",
            "description": "Tool name associated with approval (optional)"
        },
        "operation": {
            "type": "string",
            "description": "Operation name (optional)"
        },
        "file_path": {
            "type": "string",
            "description": "Target path (optional)"
        },
        "risk_score": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Normalized risk score (optional)"
        },
        "reasons": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Reasons contributing to risk (optional)"
        },
        "summary": {
            "type": "string",
            "description": "Short summary of the approval request (optional)"
        },
        "decided_at": {
            "type": "string",
            "description": "Decision timestamp (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for REFERENCE_CHECK_TRIGGERED
REFERENCE_CHECK_TRIGGERED_SCHEMA = {
    "type": "object",
    "required": ["trigger"],
    "properties": {
        "trigger": {
            "type": "string",
            "description": "Trigger reason (e.g., agent_count_5)"
        },
        "agent_count": {
            "type": "integer",
            "minimum": 0,
            "description": "Agent invocation count (optional)"
        },
        "token_count": {
            "type": "integer",
            "minimum": 0,
            "description": "Token count at trigger (optional)"
        }
    },
    "additionalProperties": True
}

# Schema for REFERENCE_CHECK_COMPLETED
REFERENCE_CHECK_COMPLETED_SCHEMA = {
    "type": "object",
    "required": ["trigger", "requirement_count"],
    "properties": {
        "trigger": {
            "type": "string",
            "description": "Trigger reason"
        },
        "requirement_count": {
            "type": "integer",
            "minimum": 0,
            "description": "Number of requirements surfaced"
        },
        "prompt_length": {
            "type": "integer",
            "minimum": 0,
            "description": "Length of generated prompt (optional)"
        },
        "reference_number": {
            "type": "integer",
            "minimum": 0,
            "description": "Reference check sequence number (optional)"
        }
    },
    "additionalProperties": True
}

# ============================================================================
# Schema Registry (maps event type to schema)
# ============================================================================

EVENT_SCHEMAS: Dict[str, Dict[str, Any]] = {
    # Agent events
    AGENT_INVOKED: AGENT_INVOKED_SCHEMA,
    AGENT_COMPLETED: AGENT_COMPLETED_SCHEMA,
    AGENT_FAILED: AGENT_FAILED_SCHEMA,
    AGENT_TIMEOUT: AGENT_TIMEOUT_SCHEMA,
    AGENT_HANDOFF: AGENT_HANDOFF_SCHEMA,

    # Tool events
    TOOL_USED: TOOL_USED_SCHEMA,
    TOOL_ERROR: TOOL_ERROR_SCHEMA,
    TOOL_PERFORMANCE: TOOL_PERFORMANCE_SCHEMA,
    TOOL_QUOTA_EXCEEDED: TOOL_QUOTA_EXCEEDED_SCHEMA,

    # Snapshot events
    SNAPSHOT_CREATED: SNAPSHOT_CREATED_SCHEMA,
    SNAPSHOT_RESTORED: SNAPSHOT_RESTORED_SCHEMA,
    SNAPSHOT_FAILED: SNAPSHOT_FAILED_SCHEMA,
    SNAPSHOT_CLEANUP: SNAPSHOT_CLEANUP_SCHEMA,

    # Session events
    SESSION_STARTED: SESSION_STARTED_SCHEMA,
    SESSION_TOKEN_WARNING: SESSION_TOKEN_WARNING_SCHEMA,
    SESSION_HANDOFF_REQUIRED: SESSION_HANDOFF_REQUIRED_SCHEMA,
    SESSION_ENDED: SESSION_ENDED_SCHEMA,

    # Cost events
    COST_TRACKED: COST_TRACKED_SCHEMA,
    COST_BUDGET_WARNING: COST_BUDGET_WARNING_SCHEMA,
    COST_OPTIMIZATION_OPPORTUNITY: COST_OPTIMIZATION_OPPORTUNITY_SCHEMA,

    # Workflow events
    WORKFLOW_STARTED: WORKFLOW_STARTED_SCHEMA,
    WORKFLOW_COMPLETED: WORKFLOW_COMPLETED_SCHEMA,

    # Task lifecycle events
    TASK_STARTED: TASK_STARTED_SCHEMA,
    TASK_STAGE_CHANGED: TASK_STAGE_CHANGED_SCHEMA,
    TASK_COMPLETED: TASK_COMPLETED_SCHEMA,

    # Test telemetry events
    TEST_RUN_STARTED: TEST_RUN_STARTED_SCHEMA,
    TEST_RUN_COMPLETED: TEST_RUN_COMPLETED_SCHEMA,

    # Session summary events
    SESSION_SUMMARY: SESSION_SUMMARY_SCHEMA,

    # Approval events
    APPROVAL_REQUIRED: APPROVAL_REQUIRED_SCHEMA,
    APPROVAL_GRANTED: APPROVAL_GRANTED_SCHEMA,
    APPROVAL_DENIED: APPROVAL_DENIED_SCHEMA,

    # Reference check events
    REFERENCE_CHECK_TRIGGERED: REFERENCE_CHECK_TRIGGERED_SCHEMA,
    REFERENCE_CHECK_COMPLETED: REFERENCE_CHECK_COMPLETED_SCHEMA,
}

# ============================================================================
# Validation Functions
# ============================================================================
# Note: EventValidationError is now imported from src.core.exceptions


def validate_event_payload(event_type: str, payload: Dict[str, Any]) -> bool:
    """
    Validate an event payload against its JSON schema.

    Args:
        event_type: Type of event (e.g., "agent.invoked")
        payload: Event payload dictionary

    Returns:
        True if validation succeeds

    Raises:
        EventValidationError: If validation fails with detailed error message

    Example:
        >>> validate_event_payload("agent.invoked", {
        ...     "agent": "test-agent",
        ...     "invoked_by": "user",
        ...     "reason": "Testing validation"
        ... })
        True
    """
    if event_type not in EVENT_SCHEMAS:
        raise EventValidationError(f"Unknown event type: {event_type}")

    schema = EVENT_SCHEMAS[event_type]

    try:
        jsonschema.validate(instance=payload, schema=schema)
        return True
    except jsonschema.ValidationError as e:
        # Build detailed error message
        error_path = " -> ".join(str(p) for p in e.path) if e.path else "root"
        raise EventValidationError(
            f"Validation failed for event type '{event_type}' at {error_path}: {e.message}"
        ) from e


def get_schema(event_type: str) -> Dict[str, Any]:
    """
    Get the JSON schema for an event type.

    Args:
        event_type: Type of event

    Returns:
        JSON schema dictionary

    Raises:
        KeyError: If event type is unknown

    Example:
        >>> schema = get_schema("agent.invoked")
        >>> schema["required"]
        ['agent', 'invoked_by', 'reason']
    """
    if event_type not in EVENT_SCHEMAS:
        raise KeyError(f"Unknown event type: {event_type}")

    return EVENT_SCHEMAS[event_type]


def get_all_event_types() -> List[str]:
    """
    Get list of all defined event types.

    Returns:
        List of event type strings

    Example:
        >>> event_types = get_all_event_types()
        >>> len(event_types)
        33
    """
    return ALL_EVENT_TYPES.copy()


def is_valid_event_type(event_type: str) -> bool:
    """
    Check if an event type is valid.

    Args:
        event_type: Event type to check

    Returns:
        True if event type is defined

    Example:
        >>> is_valid_event_type("agent.invoked")
        True
        >>> is_valid_event_type("invalid.event")
        False
    """
    return event_type in ALL_EVENT_TYPES


def get_required_fields(event_type: str) -> List[str]:
    """
    Get required fields for an event type.

    Args:
        event_type: Event type to check

    Returns:
        List of required field names

    Raises:
        KeyError: If event type is unknown

    Example:
        >>> get_required_fields("agent.invoked")
        ['agent', 'invoked_by', 'reason']
    """
    schema = get_schema(event_type)
    return schema.get("required", [])


def get_optional_fields(event_type: str) -> List[str]:
    """
    Get optional fields for an event type.

    Args:
        event_type: Event type to check

    Returns:
        List of optional field names (properties that are not required)

    Example:
        >>> get_optional_fields("agent.invoked")
        ['model_tier', 'context_tokens']
    """
    schema = get_schema(event_type)
    required = set(schema.get("required", []))
    all_props = set(schema.get("properties", {}).keys())
    return list(all_props - required)
