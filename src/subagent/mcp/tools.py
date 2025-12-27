"""MCP tool definitions for SubAgent."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional


def _schema(properties: Dict[str, Any], required: Optional[List[str]] = None) -> Dict[str, Any]:
    schema: Dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


_TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "name": "subagent_status",
        "description": "Get current status of the subagent system including active tasks, agents, and recent activity",
        "inputSchema": _schema(
            {
                "verbose": {
                    "type": "boolean",
                    "description": "Include detailed information",
                    "default": False,
                }
            }
        ),
    },
    {
        "name": "subagent_task_create",
        "description": "Create a new task with optional decomposition into subtasks",
        "inputSchema": _schema(
            {
                "title": {"type": "string", "description": "Task title"},
                "description": {"type": "string", "description": "Detailed description"},
                "acceptance_criteria": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of acceptance criteria",
                },
                "priority": {"type": "integer", "minimum": 1, "maximum": 5},
                "decompose": {
                    "type": "boolean",
                    "description": "Auto-decompose into subtasks",
                    "default": True,
                },
                "constraints": {
                    "type": "object",
                    "description": "Task constraints (tokens, time, paths)",
                },
                "context": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Additional task context",
                },
                "task_type": {"type": "string", "description": "Task type/category"},
                "deadline": {"type": "string", "description": "Deadline (ISO or freeform)"},
            },
            required=["title", "description"],
        ),
    },
    {
        "name": "subagent_spawn",
        "description": "Spawn a worker agent to execute a task",
        "inputSchema": _schema(
            {
                "task_id": {"type": "string", "description": "Task to assign"},
                "model": {
                    "type": "string",
                    "description": "Model to use (e.g., 'haiku', 'ollama/llama3.1')",
                },
                "budget_tokens": {"type": "integer", "description": "Token budget"},
                "budget_minutes": {"type": "integer", "description": "Time budget"},
                "permission_profile": {"type": "string", "description": "Permission profile"},
            },
            required=["task_id"],
        ),
    },
    {
        "name": "subagent_agent_control",
        "description": "Control a running agent (pause, resume, kill, switch model)",
        "inputSchema": _schema(
            {
                "agent_id": {"type": "string"},
                "action": {
                    "type": "string",
                    "enum": ["pause", "resume", "kill", "switch_model"],
                },
                "new_model": {"type": "string", "description": "For switch_model action"},
                "reason": {"type": "string", "description": "Reason for control action"},
            },
            required=["agent_id", "action"],
        ),
    },
    {
        "name": "subagent_review",
        "description": "Review completed work from a task",
        "inputSchema": _schema(
            {
                "task_id": {"type": "string"},
                "include_diff": {"type": "boolean", "default": True},
                "include_quality": {"type": "boolean", "default": True},
                "max_diff_chars": {"type": "integer", "default": 8000},
            },
            required=["task_id"],
        ),
    },
    {
        "name": "subagent_handoff",
        "description": "Create a handoff document for AI-to-AI transfer",
        "inputSchema": _schema(
            {
                "reason": {
                    "type": "string",
                    "enum": ["token_limit", "session_end", "model_switch", "error", "user_request"],
                },
                "notes": {"type": "string", "description": "Additional context for next AI"},
            },
            required=["reason"],
        ),
    },
    {
        "name": "subagent_metrics",
        "description": "Get cost and performance metrics",
        "inputSchema": _schema(
            {
                "scope": {
                    "type": "string",
                    "enum": ["session", "task", "project"],
                    "default": "session",
                },
                "compare_naive": {"type": "boolean", "default": True},
            }
        ),
    },
]


for tool in _TOOL_DEFINITIONS:
    tool.setdefault("parameters", deepcopy(tool.get("inputSchema", {})))


def get_tool_definitions() -> List[Dict[str, Any]]:
    """Return tool definitions for MCP discovery."""
    return deepcopy(_TOOL_DEFINITIONS)


def get_tool_definition(name: str) -> Optional[Dict[str, Any]]:
    """Look up a tool definition by name."""
    for tool in _TOOL_DEFINITIONS:
        if tool.get("name") == name:
            return deepcopy(tool)
    return None


__all__ = ["get_tool_definitions", "get_tool_definition"]
