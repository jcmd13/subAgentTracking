# SubAgent Control System - Complete Project Specification

**Version:** 1.0.0  
**Created:** 2025-12-06  
**Author:** Project CEO (Claude) + John Davis  
**Status:** Planning Complete, Ready for Implementation

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Problem Statement](#2-problem-statement)
3. [Solution Overview](#3-solution-overview)
4. [Architecture](#4-architecture)
5. [Core Concepts](#5-core-concepts)
6. [Data Schemas](#6-data-schemas)
7. [Component Specifications](#7-component-specifications)
8. [Implementation Phases](#8-implementation-phases)
9. [API Reference](#9-api-reference)
10. [Integration Guide](#10-integration-guide)
11. [Testing Strategy](#11-testing-strategy)
12. [Success Metrics](#12-success-metrics)
13. [Risk Analysis](#13-risk-analysis)
14. [Appendices](#14-appendices)

---

## 1. Executive Summary

### 1.1 Mission

Enable solo developers to safely delegate work to AI agents with full visibility, control, quality assurance, and cost optimization.

### 1.2 Key Differentiators

| Capability | Description |
|------------|-------------|
| **Control, Not Just Tracking** | Enforce permissions, budgets, and quality gates—not just log events |
| **Seamless Handoff** | Any AI can resume work from any other AI's failure point |
| **Model Agnostic** | Works with Claude, Gemini, Ollama, OpenAI, and others |
| **Context Splitting** | Complex tasks decomposed into focused subtasks for specialized agents |
| **Live Collaboration** | Human can inspect, intervene, and guide work in real-time |
| **Provable Value** | Quantifiable cost savings and quality improvements |

### 1.3 MVP Success Criteria

The system is not complete until ALL of these work:

- [ ] Fresh `pip install` on new machine succeeds
- [ ] Integrates with Claude Code via MCP server
- [ ] Slash commands spawn and control subagents
- [ ] Live review of work in progress
- [ ] Automatic handoff on failure/token exhaustion
- [ ] Auto-fallback to alternative models
- [ ] Cost comparison: "This saved X% vs naive approach"
- [ ] State survives unexpected failure, internet loss

---

## 2. Problem Statement

### 2.1 The Solo Developer's Dilemma

Solo developers using AI coding tools ("vibe coding") face systematic challenges:

1. **No Quality Gates**: AI can modify tests to make them pass instead of fixing code
2. **Context Explosion**: Long conversations degrade quality and inflate costs
3. **No Recovery**: Session crashes lose all context and progress
4. **No Visibility**: Can't see what AI is doing until it's done
5. **Vendor Lock-in**: Stuck when one provider hits limits or fails
6. **No Proof of Value**: Can't quantify if AI assistance is actually helping

### 2.2 Why Existing Solutions Fail

| Approach | Problem |
|----------|---------|
| Naive prompting | No guardrails, no recovery, no cost control |
| Long conversations | Context bloat, hallucinations, expensive |
| Manual checkpointing | Tedious, error-prone, still loses context |
| Single-model dependence | Outages and limits halt all work |

### 2.3 The Reward Hacking Problem

When the same AI writes code AND evaluates its quality:
- It can modify tests instead of fixing code
- It can claim success without verification
- It can optimize for appearing successful vs being successful

**Solution:** Separation of privilege. Workers cannot grade their own work.

---

## 3. Solution Overview

### 3.1 The Control Hierarchy

```
┌─────────────────────────────────────────────────────────────────────┐
│                         HUMAN OPERATOR                               │
│  - Defines tasks and acceptance criteria                            │
│  - Reviews work and approves merges                                 │
│  - Can intervene at any time                                        │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR (Current AI Session)                 │
│  - Decomposes complex tasks into subtasks                           │
│  - Assigns subtasks to appropriate models                           │
│  - Monitors progress and enforces budgets                           │
│  - Triggers quality gates before accepting work                     │
│  - Generates handoff state on session end                           │
└─────────────────────────────────────────────────────────────────────┘
                                │
                    ┌───────────┼───────────┐
                    ▼           ▼           ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   WORKER        │ │   WORKER        │ │   WORKER        │
│   SUBAGENT      │ │   SUBAGENT      │ │   SUBAGENT      │
│                 │ │                 │ │                 │
│ Focused task    │ │ Focused task    │ │ Focused task    │
│ Limited scope   │ │ Limited scope   │ │ Limited scope   │
│ Budget capped   │ │ Budget capped   │ │ Budget capped   │
└─────────────────┘ └─────────────────┘ └─────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    TRACKER AGENT (Progress Monitor)                  │
│  - Maintains project state across sessions                          │
│  - Updates progress on task completion                              │
│  - Generates status reports                                         │
│  - Detects stalled or failed tasks                                  │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    QUALITY GATES (Immutable)                         │
│  - Tests from protected branch (workers cannot modify)              │
│  - Static analysis, coverage, type checking                         │
│  - Diff review (did it do what was asked?)                          │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PERSISTENT STATE                                  │
│  - Survives session crashes, internet loss, token exhaustion        │
│  - Enables any AI to continue any other AI's work                   │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Agent Roles

| Role | Responsibility | Model Tier |
|------|----------------|------------|
| **Orchestrator** | Decompose tasks, assign work, enforce policies | Current session AI |
| **Worker** | Execute focused subtasks | Cheap/fast (Haiku, Ollama) |
| **Tracker** | Maintain state, report progress | Cheap/fast (Haiku, Ollama) |
| **Reviewer** | Evaluate work quality | Base tier (Sonnet, Gemini Pro) |
| **Planner** | Design complex features | Strong tier (Opus, GPT-4) |

### 3.3 Context Splitting Strategy

Complex features are decomposed into focused subtasks:

```
Feature: "Implement user authentication"
    │
    ├── Subtask 1: "Design auth data models"
    │   └── Worker A (Planner model, ~5k tokens)
    │
    ├── Subtask 2: "Implement User model"
    │   └── Worker B (Coder model, ~10k tokens)
    │
    ├── Subtask 3: "Implement password hashing"
    │   └── Worker C (Coder model, ~8k tokens)
    │
    ├── Subtask 4: "Implement JWT token generation"
    │   └── Worker D (Coder model, ~8k tokens)
    │
    ├── Subtask 5: "Implement login endpoint"
    │   └── Worker E (Coder model, ~10k tokens)
    │
    ├── Subtask 6: "Write unit tests"
    │   └── Worker F (Test writer model, ~15k tokens)
    │
    └── Subtask 7: "Integration review"
        └── Worker G (Reviewer model, ~10k tokens)

Total: ~66k tokens across 7 focused contexts
vs Naive: ~150k tokens in one bloated context
Savings: 56%
```

---

## 4. Architecture

### 4.1 System Components

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER INTERFACES                               │
├─────────────────┬─────────────────┬─────────────────────────────────┤
│   CLI Tool      │   MCP Server    │   (Future: Web Dashboard)       │
│   `subagent`    │   For AI tools  │                                 │
└────────┬────────┴────────┬────────┴─────────────────────────────────┘
         │                 │
         └────────┬────────┘
                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      ORCHESTRATION LAYER                             │
├─────────────────┬─────────────────┬─────────────────────────────────┤
│  State Machine  │  Task Manager   │  Handoff Protocol               │
│  (Workflows)    │  (Queue/Assign) │  (AI-to-AI Transfer)            │
├─────────────────┼─────────────────┼─────────────────────────────────┤
│  Permissions    │  Budget         │  Lifecycle                      │
│  (Access Ctrl)  │  (Token/Cost)   │  (Start/Stop/Kill)              │
└────────┬────────┴────────┬────────┴────────┬────────────────────────┘
         │                 │                 │
         ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      EXECUTION LAYER                                 │
├─────────────────┬─────────────────┬─────────────────────────────────┤
│  Provider       │  Spawner        │  Monitor                        │
│  Adapters       │  (Create Agent) │  (Watch Progress)               │
│  Claude/Gemini/ │                 │                                 │
│  Ollama/OpenAI  │                 │                                 │
└────────┬────────┴────────┬────────┴────────┬────────────────────────┘
         │                 │                 │
         ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      QUALITY LAYER                                   │
├─────────────────┬─────────────────┬─────────────────────────────────┤
│  Gate Runner    │  Diff Analyzer  │  Test Runner                    │
│  (Enforce)      │  (Task vs Work) │  (Protected)                    │
└────────┬────────┴────────┬────────┴────────┬────────────────────────┘
         │                 │                 │
         ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      PERSISTENCE LAYER                               │
├─────────────────┬─────────────────┬─────────────────────────────────┤
│  State Store    │  Activity Log   │  Analytics DB                   │
│  (JSON files)   │  (JSONL)        │  (SQLite)                       │
└─────────────────┴─────────────────┴─────────────────────────────────┘
```

### 4.2 Directory Structure

```
project-root/
├── .subagent/                      # All subagent system data
│   │
│   ├── config.yaml                 # User configuration
│   │
│   ├── state/                      # Current system state
│   │   ├── orchestrator.json       # Active orchestrator state
│   │   ├── queue.json              # Task queue
│   │   └── agents.json             # Active agent registry
│   │
│   ├── sessions/                   # Session-specific data
│   │   └── {session_id}/           # e.g., 20251206_143022_claude_sonnet
│   │       ├── session.json        # Session metadata
│   │       ├── tasks/              # Tasks created this session
│   │       │   └── {task_id}.json
│   │       ├── agents/             # Agents spawned this session  
│   │       │   └── {agent_id}.json
│   │       └── log.jsonl           # Session activity log
│   │
│   ├── tasks/                      # All tasks (cross-session)
│   │   └── {task_id}.json          # Full task state
│   │
│   ├── handoffs/                   # AI-to-AI handoff documents
│   │   └── {handoff_id}.md         # Human + AI readable
│   │
│   ├── quality/                    # Quality gate results
│   │   └── {task_id}/
│   │       ├── tests.json
│   │       ├── coverage.json
│   │       └── review.json
│   │
│   ├── analytics/                  # Metrics and history
│   │   ├── tracking.db             # SQLite database
│   │   └── reports/                # Generated reports
│   │
│   └── prompts/                    # Prompt library
│       ├── roles/                  # Role-based prompts
│       │   ├── planner.md
│       │   ├── coder.md
│       │   ├── tester.md
│       │   └── reviewer.md
│       └── skills/                 # Skill-based prompts
│           ├── python.md
│           ├── testing.md
│           └── security.md
│
└── (rest of project files)
```

### 4.3 Package Structure

```
subagent-control/
├── pyproject.toml
├── README.md
├── LICENSE
│
├── src/
│   └── subagent/
│       ├── __init__.py             # Public API exports
│       ├── __main__.py             # CLI entry point
│       │
│       ├── cli/                    # Command-line interface
│       │   ├── __init__.py
│       │   ├── main.py             # Click/Typer app
│       │   ├── commands/
│       │   │   ├── init.py         # subagent init
│       │   │   ├── status.py       # subagent status
│       │   │   ├── task.py         # subagent task add/list/show
│       │   │   ├── agent.py        # subagent agent spawn/list/kill
│       │   │   ├── review.py       # subagent review
│       │   │   └── handoff.py      # subagent handoff
│       │   └── formatters.py       # Output formatting
│       │
│       ├── mcp/                    # MCP server for AI tools
│       │   ├── __init__.py
│       │   ├── server.py           # MCP server implementation
│       │   ├── tools.py            # Tool definitions
│       │   └── handlers.py         # Tool handlers
│       │
│       ├── core/                   # Core infrastructure (from existing)
│       │   ├── __init__.py
│       │   ├── config.py           # Configuration management
│       │   ├── schemas.py          # Pydantic models
│       │   ├── activity_logger.py  # Event logging
│       │   ├── snapshot_manager.py # State snapshots
│       │   └── analytics_db.py     # SQLite analytics
│       │
│       ├── orchestration/          # Orchestration layer
│       │   ├── __init__.py
│       │   ├── state_machine.py    # Workflow state management
│       │   ├── task_manager.py     # Task queue and assignment
│       │   ├── decomposer.py       # Task decomposition logic
│       │   ├── handoff.py          # Handoff protocol
│       │   ├── permissions.py      # Access control
│       │   ├── budget.py           # Token/cost budgets
│       │   └── lifecycle.py        # Agent lifecycle control
│       │
│       ├── execution/              # Agent execution
│       │   ├── __init__.py
│       │   ├── spawner.py          # Create agent instances
│       │   ├── monitor.py          # Watch agent progress
│       │   ├── fallback.py         # Model fallback logic
│       │   └── providers/          # AI provider adapters
│       │       ├── __init__.py
│       │       ├── base.py         # Abstract interface
│       │       ├── claude.py       # Anthropic Claude
│       │       ├── gemini.py       # Google Gemini
│       │       ├── ollama.py       # Ollama local
│       │       └── openai.py       # OpenAI compatible
│       │
│       ├── quality/                # Quality enforcement
│       │   ├── __init__.py
│       │   ├── gates.py            # Gate definitions
│       │   ├── runner.py           # Execute quality gates
│       │   ├── diff_analyzer.py    # Compare task vs result
│       │   └── test_runner.py      # Protected test execution
│       │
│       ├── tracking/               # Progress tracking
│       │   ├── __init__.py
│       │   ├── tracker_agent.py    # Tracker agent logic
│       │   ├── progress.py         # Progress calculation
│       │   └── reporter.py         # Status reports
│       │
│       └── metrics/                # Cost and value metrics
│           ├── __init__.py
│           ├── cost_tracker.py     # Token/$ accounting
│           ├── comparator.py       # Naive vs actual comparison
│           └── value_reporter.py   # ROI reports
│
├── tests/
│   ├── conftest.py
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
└── examples/
    ├── basic_usage.py
    ├── claude_code_integration.md
    └── multi_model_workflow.py
```

---

## 5. Core Concepts

### 5.1 Session

A session represents one continuous interaction with the system, typically one AI conversation.

**Session ID Format:** `{YYYYMMDD}_{HHMMSS}_{provider}_{model}`

Example: `20251206_143022_anthropic_claude-sonnet-4`

```json
{
  "session_id": "20251206_143022_anthropic_claude-sonnet-4",
  "started_at": "2025-12-06T14:30:22Z",
  "provider": "anthropic",
  "model": "claude-sonnet-4",
  "role": "orchestrator",
  "status": "active",
  "tokens_used": 45231,
  "cost_usd": 0.68,
  "tasks_created": ["task_20251206_143022_001", "task_20251206_143022_002"],
  "agents_spawned": ["agent_20251206_143522_haiku_001"]
}
```

### 5.2 Task

A task is a unit of work with clear acceptance criteria and constraints.

**Task ID Format:** `task_{session_timestamp}_{sequence}`

Example: `task_20251206_143022_001`

Tasks can be:
- **Top-level**: Defined by human ("Implement auth module")
- **Subtasks**: Decomposed by orchestrator ("Implement User model")

```json
{
  "task_id": "task_20251206_143022_001",
  "parent_task_id": null,
  "session_id": "20251206_143022_anthropic_claude-sonnet-4",
  "created_at": "2025-12-06T14:30:25Z",
  
  "definition": {
    "title": "Implement user authentication module",
    "description": "Create a complete auth system with login, logout, and JWT tokens",
    "acceptance_criteria": [
      "User model with email, password_hash, created_at",
      "POST /auth/login returns JWT on valid credentials",
      "POST /auth/logout invalidates token",
      "All endpoints have input validation",
      "Unit test coverage >80%"
    ],
    "priority": 1,
    "estimated_tokens": 50000,
    "deadline": null
  },
  
  "constraints": {
    "max_tokens": 60000,
    "max_time_minutes": 120,
    "max_cost_usd": 1.00,
    "allowed_tools": ["read", "write", "edit", "bash"],
    "allowed_paths": ["src/auth/**", "tests/auth/**"],
    "forbidden_paths": ["tests/fixtures/**", ".env*", "*.secret"],
    "required_quality_gates": ["tests_pass", "coverage_80", "no_secrets"]
  },
  
  "decomposition": {
    "strategy": "sequential_with_parallel",
    "subtasks": [
      {
        "task_id": "task_20251206_143022_001_a",
        "title": "Design auth data models",
        "depends_on": [],
        "estimated_tokens": 5000
      },
      {
        "task_id": "task_20251206_143022_001_b",
        "title": "Implement User model",
        "depends_on": ["task_20251206_143022_001_a"],
        "estimated_tokens": 10000
      }
    ]
  },
  
  "execution": {
    "status": "in_progress",
    "progress_percent": 35,
    "assigned_agent": "agent_20251206_143522_haiku_001",
    "started_at": "2025-12-06T14:35:22Z",
    "tokens_used": 17500,
    "cost_usd": 0.26
  },
  
  "progress": {
    "completed_steps": [
      {
        "description": "Created User model in src/auth/models.py",
        "timestamp": "2025-12-06T14:40:00Z",
        "files": ["src/auth/models.py"],
        "agent": "agent_20251206_143522_haiku_001"
      }
    ],
    "current_step": "Implementing password hashing utilities",
    "remaining_steps": [
      "Create JWT token utilities",
      "Implement login endpoint",
      "Implement logout endpoint",
      "Write unit tests"
    ]
  },
  
  "files": {
    "created": ["src/auth/models.py", "src/auth/__init__.py"],
    "modified": [],
    "git_branch": "feature/task_20251206_143022_001"
  },
  
  "quality": {
    "gates_passed": [],
    "gates_failed": [],
    "gates_pending": ["tests_pass", "coverage_80", "no_secrets"],
    "last_quality_run": null
  },
  
  "context": {
    "key_decisions": [
      "Using bcrypt for password hashing (industry standard)",
      "JWT tokens expire in 24 hours (configurable)"
    ],
    "dependencies_added": ["bcrypt", "pyjwt"],
    "related_files": ["src/core/config.py", "requirements.txt"],
    "notes": "User requested argon2 but bcrypt chosen for compatibility"
  },
  
  "recovery": {
    "last_checkpoint": "2025-12-06T14:50:00Z",
    "checkpoint_file": ".subagent/sessions/20251206_143022_anthropic_claude-sonnet-4/checkpoints/task_001_cp_003.json",
    "resume_instructions": "Continue implementing hash_password() in src/auth/utils.py line 23"
  }
}
```

### 5.3 Agent

An agent is an AI instance executing a specific task.

**Agent ID Format:** `agent_{session_timestamp}_{model_short}_{sequence}`

Example: `agent_20251206_143522_haiku_001`

```json
{
  "agent_id": "agent_20251206_143522_haiku_001",
  "session_id": "20251206_143022_anthropic_claude-sonnet-4",
  "created_at": "2025-12-06T14:35:22Z",
  
  "configuration": {
    "provider": "anthropic",
    "model": "claude-3-haiku-20240307",
    "role": "worker",
    "system_prompt_template": "coder",
    "skills": ["python", "testing"],
    "temperature": 0.3
  },
  
  "assignment": {
    "task_id": "task_20251206_143022_001_b",
    "assigned_at": "2025-12-06T14:35:22Z",
    "assigned_by": "orchestrator"
  },
  
  "permissions": {
    "tools": ["read", "write", "edit"],
    "paths_allowed": ["src/auth/**"],
    "paths_forbidden": ["tests/**", ".env"],
    "can_spawn_subagents": false,
    "can_modify_tests": false,
    "can_access_network": false
  },
  
  "budget": {
    "max_tokens": 15000,
    "tokens_used": 8234,
    "max_time_minutes": 30,
    "time_elapsed_minutes": 12,
    "max_cost_usd": 0.05,
    "cost_usd": 0.02
  },
  
  "status": {
    "state": "running",
    "health": "healthy",
    "last_activity": "2025-12-06T14:47:15Z",
    "current_action": "Writing src/auth/utils.py"
  },
  
  "metrics": {
    "actions_completed": 15,
    "files_created": 2,
    "files_modified": 1,
    "errors_encountered": 0,
    "retries": 0
  }
}
```

### 5.4 Handoff

A handoff is a document that enables any AI to continue work from where another AI stopped.

**Handoff ID Format:** `handoff_{timestamp}_{from_model}_{reason}`

Example: `handoff_20251206_150000_claude-sonnet_token_limit`

```markdown
---
handoff_id: handoff_20251206_150000_claude-sonnet_token_limit
created_at: 2025-12-06T15:00:00Z
reason: token_limit_reached

from_session:
  session_id: 20251206_143022_anthropic_claude-sonnet-4
  model: claude-sonnet-4
  tokens_used: 198542
  tokens_limit: 200000

system_state:
  active_tasks: 2
  completed_tasks: 3
  pending_tasks: 5
  active_agents: 1
---

# Handoff Summary

## What Was Accomplished

### Completed Tasks
1. **task_20251206_143022_001_a**: Design auth data models ✅
   - Created data model specifications
   - Decided on bcrypt for password hashing
   
2. **task_20251206_143022_001_b**: Implement User model ✅
   - Created `src/auth/models.py` with User class
   - Added email validation, password hashing
   
3. **task_20251206_143022_001_c**: Implement JWT utilities ✅
   - Created `src/auth/jwt.py` with token generation/validation

### In-Progress Task
**task_20251206_143022_001_d**: Implement login endpoint
- Status: 60% complete
- Current file: `src/auth/routes.py`
- Last edit: Line 47 (login function)
- Remaining:
  - Complete error handling in login()
  - Add rate limiting
  - Add request logging

### Pending Tasks
- task_20251206_143022_001_e: Implement logout endpoint
- task_20251206_143022_001_f: Write unit tests
- task_20251206_143022_001_g: Integration testing

## Active Agents

### agent_20251206_143522_haiku_001
- Status: Paused (waiting for orchestrator)
- Task: Implementing login endpoint
- Tokens remaining: 6766
- Can be resumed or terminated

## Key Decisions Made

1. **Password Hashing**: Using bcrypt with cost factor 12
   - Reason: Industry standard, good security/performance balance
   
2. **JWT Configuration**: 
   - Algorithm: HS256
   - Expiry: 24 hours
   - Refresh tokens: Not implemented (future task)

3. **Error Handling Pattern**: 
   - Using custom AuthenticationError exception
   - All errors return JSON with `error` and `message` fields

## Files Modified

| File | Status | Description |
|------|--------|-------------|
| src/auth/__init__.py | Created | Package init |
| src/auth/models.py | Created | User model |
| src/auth/jwt.py | Created | JWT utilities |
| src/auth/routes.py | Partial | Login endpoint (60%) |
| src/auth/exceptions.py | Created | Custom exceptions |
| requirements.txt | Modified | Added bcrypt, pyjwt |

## How to Continue

### Immediate Next Steps

1. **Resume task_20251206_143022_001_d**:
   ```
   subagent task resume task_20251206_143022_001_d
   ```
   Or manually:
   - Open `src/auth/routes.py`
   - Continue from line 47
   - Complete the login() error handling
   - Add rate limiting decorator
   - Add logging

2. **After login endpoint complete**:
   - Run quality gates: `subagent quality run task_20251206_143022_001_d`
   - If passes, proceed to logout endpoint

### Context Needed

- Project uses FastAPI (see `src/main.py` for app setup)
- Rate limiting config in `src/core/config.py` (5 req/min for auth)
- Logging setup in `src/core/logging.py`

### Warnings

- Do NOT modify existing tests in `tests/` - they are protected
- The `.env` file contains secrets - do not read or log its contents
- Rate limit decorator is in `src/core/decorators.py`

## Cost Summary

| Metric | This Session | Project Total |
|--------|--------------|---------------|
| Tokens | 198,542 | 542,891 |
| Cost | $2.97 | $8.14 |
| Naive Estimate | $7.50 | $24.50 |
| **Savings** | **60%** | **67%** |

---
*Generated by SubAgent Control System v1.0.0*
*To continue: `subagent handoff resume handoff_20251206_150000_claude-sonnet_token_limit`*
```

---

## 6. Data Schemas

### 6.1 Configuration Schema

```yaml
# .subagent/config.yaml

version: "1.0"

project:
  name: "my-project"
  description: "Project description"
  main_branch: "main"
  
orchestration:
  # Who has final authority
  default_orchestrator: "current_session"  # or specific model
  
  # Human approval requirements
  require_approval:
    task_creation: false      # Auto-create subtasks
    agent_spawn: false        # Auto-spawn workers
    file_write: false         # Auto-allow writes (within permissions)
    merge: true               # ALWAYS require human approval for merge
    
  # Automatic behaviors
  auto_decompose: true        # Auto-split complex tasks
  auto_assign: true           # Auto-assign to available agents
  auto_fallback: true         # Auto-switch models on failure
  
providers:
  # Provider configurations
  anthropic:
    enabled: true
    models:
      - claude-opus-4          # Strong tier
      - claude-sonnet-4        # Base tier
      - claude-haiku-3         # Weak tier
    default_model: "claude-sonnet-4"
    
  google:
    enabled: true
    models:
      - gemini-1.5-pro         # Base tier
      - gemini-1.5-flash       # Weak tier
    default_model: "gemini-1.5-pro"
    api_key_env: "GOOGLE_API_KEY"
    
  ollama:
    enabled: true
    models:
      - llama3.1:70b           # Base tier (local)
      - llama3.1:8b            # Weak tier (local)
      - codellama:34b          # Code specialist
    base_url: "http://localhost:11434"
    default_model: "llama3.1:70b"
    
  openai:
    enabled: false
    models:
      - gpt-4-turbo
      - gpt-3.5-turbo
    api_key_env: "OPENAI_API_KEY"

model_tiers:
  # Task-to-tier mapping
  strong:
    use_for: ["architecture", "security_review", "complex_debugging"]
    models: ["claude-opus-4", "gpt-4-turbo"]
    
  base:
    use_for: ["implementation", "refactoring", "code_review"]
    models: ["claude-sonnet-4", "gemini-1.5-pro", "llama3.1:70b"]
    
  weak:
    use_for: ["simple_tasks", "documentation", "formatting"]
    models: ["claude-haiku-3", "gemini-1.5-flash", "llama3.1:8b"]

fallback:
  # Fallback chain when primary fails
  chain:
    - claude-sonnet-4
    - gemini-1.5-pro
    - llama3.1:70b
  
  triggers:
    - "rate_limit"
    - "token_limit"
    - "api_error"
    - "timeout"

budgets:
  # Default budgets (can be overridden per task)
  default_task:
    max_tokens: 50000
    max_time_minutes: 60
    max_cost_usd: 1.00
    
  default_agent:
    max_tokens: 15000
    max_time_minutes: 30
    max_cost_usd: 0.25

quality_gates:
  # Quality gate definitions
  tests_pass:
    type: "command"
    command: "pytest tests/ -v"
    required: true
    
  coverage_80:
    type: "coverage"
    command: "pytest --cov=src --cov-fail-under=80"
    threshold: 80
    required: true
    
  type_check:
    type: "command"
    command: "mypy src/"
    required: false
    
  lint:
    type: "command"
    command: "flake8 src/"
    required: false
    
  no_secrets:
    type: "scan"
    patterns:
      - "password\\s*=\\s*['\"][^'\"]+['\"]"
      - "api_key\\s*=\\s*['\"][^'\"]+['\"]"
      - "secret\\s*=\\s*['\"][^'\"]+['\"]"
    required: true

permissions:
  # Default permissions for workers
  default_worker:
    tools: ["read", "write", "edit"]
    paths_allowed: ["src/**", "tests/**"]
    paths_forbidden: [".env*", "*.secret", ".subagent/config.yaml"]
    can_spawn_subagents: false
    can_modify_tests: false
    can_run_bash: false
    can_access_network: false
    
  # Elevated permissions (require approval)
  elevated:
    can_run_bash: true
    can_access_network: true

tracking:
  # What to track
  log_level: "info"           # debug, info, warn, error
  log_tool_usage: true
  log_file_operations: true
  log_decisions: true
  log_token_usage: true
  
  # Checkpointing
  checkpoint_interval_tokens: 5000
  checkpoint_interval_minutes: 5
  checkpoint_on_file_write: true
  
  # Retention
  keep_sessions: 30           # days
  keep_handoffs: 90           # days
  keep_analytics: 365         # days
```

### 6.2 State Schemas

See Section 5 (Core Concepts) for Session, Task, Agent, and Handoff schemas.

### 6.3 Event Schemas

Events are logged to track all system activity.

```python
# Base event (all events extend this)
class BaseEvent:
    event_id: str              # Unique event ID
    event_type: str            # Event type
    timestamp: datetime        # When it occurred
    session_id: str            # Which session
    agent_id: Optional[str]    # Which agent (if applicable)
    task_id: Optional[str]     # Which task (if applicable)

# Specific event types
class TaskCreatedEvent(BaseEvent):
    event_type = "task_created"
    task_definition: dict
    created_by: str            # "human" or agent_id

class TaskDecomposedEvent(BaseEvent):
    event_type = "task_decomposed"
    parent_task_id: str
    subtask_ids: List[str]
    decomposition_strategy: str

class AgentSpawnedEvent(BaseEvent):
    event_type = "agent_spawned"
    provider: str
    model: str
    assigned_task_id: str
    budget: dict

class AgentCompletedEvent(BaseEvent):
    event_type = "agent_completed"
    result: str                # "success", "failure", "timeout", "budget_exceeded"
    tokens_used: int
    cost_usd: float
    files_modified: List[str]

class ToolUsedEvent(BaseEvent):
    event_type = "tool_used"
    tool: str
    target: str
    success: bool
    duration_ms: int

class QualityGateEvent(BaseEvent):
    event_type = "quality_gate"
    gate_name: str
    result: str                # "pass", "fail", "skip"
    details: dict

class HandoffCreatedEvent(BaseEvent):
    event_type = "handoff_created"
    handoff_id: str
    reason: str
    from_model: str
    tasks_in_progress: List[str]

class BudgetWarningEvent(BaseEvent):
    event_type = "budget_warning"
    budget_type: str           # "tokens", "time", "cost"
    current: float
    limit: float
    percent_used: float

class FallbackTriggeredEvent(BaseEvent):
    event_type = "fallback_triggered"
    from_model: str
    to_model: str
    reason: str
```

---

## 7. Component Specifications

### 7.1 CLI Tool

#### Commands

```bash
# Initialization
subagent init                          # Initialize in current project
subagent init --from-template=python   # Use project template

# Status
subagent status                        # Show system status
subagent status --json                 # JSON output for scripting

# Task Management
subagent task add "description"        # Add task to queue
subagent task add --file=spec.md       # Add task from file
subagent task list                     # List all tasks
subagent task list --status=pending    # Filter by status
subagent task show <task_id>           # Show task details
subagent task start <task_id>          # Start task execution
subagent task pause <task_id>          # Pause task
subagent task resume <task_id>         # Resume paused task
subagent task cancel <task_id>         # Cancel task

# Agent Management
subagent agent list                    # List active agents
subagent agent show <agent_id>         # Show agent details
subagent agent spawn --task=<id> --model=haiku  # Manually spawn agent
subagent agent pause <agent_id>        # Pause agent
subagent agent resume <agent_id>       # Resume agent
subagent agent kill <agent_id>         # Terminate agent
subagent agent switch <agent_id> --model=gemini  # Switch to different model

# Review & Quality
subagent review <task_id>              # Review task results
subagent review --diff <task_id>       # Show diff
subagent quality run <task_id>         # Run quality gates
subagent quality status <task_id>      # Show gate status
subagent approve <task_id>             # Approve for merge
subagent reject <task_id> --reason="..." # Reject with feedback

# Handoff
subagent handoff create --reason="switching models"  # Create handoff
subagent handoff list                  # List handoffs
subagent handoff show <handoff_id>     # Show handoff details
subagent handoff resume <handoff_id>   # Resume from handoff

# Monitoring
subagent logs                          # Show recent logs
subagent logs --follow                 # Tail logs
subagent logs --agent=<id>             # Filter by agent
subagent watch                         # Live dashboard (TUI)

# Metrics
subagent metrics                       # Show cost/performance summary
subagent metrics --compare             # Compare to naive approach
subagent metrics --export=report.md    # Export report

# Configuration
subagent config show                   # Show current config
subagent config set <key> <value>      # Set config value
subagent config validate               # Validate configuration
```

#### Implementation Notes

- Use `typer` or `click` for CLI framework
- Support both interactive and scriptable (JSON) output
- All commands should work offline (except model API calls)
- Commands should be fast (<100ms for local operations)

### 7.2 MCP Server

The MCP server enables AI tools (Claude Code, etc.) to use subagent functionality.

#### Tool Definitions

```python
# Tool: subagent_status
{
    "name": "subagent_status",
    "description": "Get current status of the subagent system including active tasks, agents, and recent activity",
    "parameters": {
        "type": "object",
        "properties": {
            "verbose": {
                "type": "boolean",
                "description": "Include detailed information",
                "default": False
            }
        }
    }
}

# Tool: subagent_task_create
{
    "name": "subagent_task_create",
    "description": "Create a new task with optional decomposition into subtasks",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Task title"},
            "description": {"type": "string", "description": "Detailed description"},
            "acceptance_criteria": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of acceptance criteria"
            },
            "priority": {"type": "integer", "minimum": 1, "maximum": 5},
            "decompose": {
                "type": "boolean",
                "description": "Auto-decompose into subtasks",
                "default": True
            },
            "constraints": {
                "type": "object",
                "description": "Task constraints (tokens, time, paths)"
            }
        },
        "required": ["title", "description"]
    }
}

# Tool: subagent_spawn
{
    "name": "subagent_spawn",
    "description": "Spawn a worker agent to execute a task",
    "parameters": {
        "type": "object",
        "properties": {
            "task_id": {"type": "string", "description": "Task to assign"},
            "model": {"type": "string", "description": "Model to use (e.g., 'haiku', 'ollama/llama3.1')"},
            "budget_tokens": {"type": "integer", "description": "Token budget"},
            "budget_minutes": {"type": "integer", "description": "Time budget"}
        },
        "required": ["task_id"]
    }
}

# Tool: subagent_agent_control
{
    "name": "subagent_agent_control",
    "description": "Control a running agent (pause, resume, kill, switch model)",
    "parameters": {
        "type": "object",
        "properties": {
            "agent_id": {"type": "string"},
            "action": {
                "type": "string",
                "enum": ["pause", "resume", "kill", "switch_model"]
            },
            "new_model": {"type": "string", "description": "For switch_model action"}
        },
        "required": ["agent_id", "action"]
    }
}

# Tool: subagent_review
{
    "name": "subagent_review",
    "description": "Review completed work from a task",
    "parameters": {
        "type": "object",
        "properties": {
            "task_id": {"type": "string"},
            "include_diff": {"type": "boolean", "default": True},
            "include_quality": {"type": "boolean", "default": True}
        },
        "required": ["task_id"]
    }
}

# Tool: subagent_handoff
{
    "name": "subagent_handoff",
    "description": "Create a handoff document for AI-to-AI transfer",
    "parameters": {
        "type": "object",
        "properties": {
            "reason": {
                "type": "string",
                "enum": ["token_limit", "session_end", "model_switch", "error", "user_request"]
            },
            "notes": {"type": "string", "description": "Additional context for next AI"}
        },
        "required": ["reason"]
    }
}

# Tool: subagent_metrics
{
    "name": "subagent_metrics",
    "description": "Get cost and performance metrics",
    "parameters": {
        "type": "object",
        "properties": {
            "scope": {
                "type": "string",
                "enum": ["session", "task", "project"],
                "default": "session"
            },
            "compare_naive": {"type": "boolean", "default": True}
        }
    }
}
```

### 7.3 State Machine

Manages workflow states and transitions.

```python
class TaskState(Enum):
    CREATED = "created"
    QUEUED = "queued"
    DECOMPOSING = "decomposing"
    READY = "ready"
    ASSIGNED = "assigned"
    RUNNING = "running"
    PAUSED = "paused"
    REVIEW = "review"
    QUALITY_CHECK = "quality_check"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

# Valid state transitions
TASK_TRANSITIONS = {
    TaskState.CREATED: [TaskState.QUEUED, TaskState.DECOMPOSING],
    TaskState.QUEUED: [TaskState.READY, TaskState.CANCELLED],
    TaskState.DECOMPOSING: [TaskState.READY, TaskState.FAILED],
    TaskState.READY: [TaskState.ASSIGNED, TaskState.CANCELLED],
    TaskState.ASSIGNED: [TaskState.RUNNING, TaskState.CANCELLED],
    TaskState.RUNNING: [TaskState.PAUSED, TaskState.REVIEW, TaskState.FAILED],
    TaskState.PAUSED: [TaskState.RUNNING, TaskState.CANCELLED],
    TaskState.REVIEW: [TaskState.QUALITY_CHECK, TaskState.REJECTED, TaskState.RUNNING],
    TaskState.QUALITY_CHECK: [TaskState.APPROVED, TaskState.REJECTED],
    TaskState.APPROVED: [TaskState.COMPLETED],
    TaskState.REJECTED: [TaskState.READY],  # Goes back to queue
    TaskState.COMPLETED: [],  # Terminal
    TaskState.FAILED: [TaskState.READY],  # Can retry
    TaskState.CANCELLED: [],  # Terminal
}

class AgentState(Enum):
    CREATED = "created"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETING = "completing"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"
    SWITCHING = "switching"  # Switching to different model

AGENT_TRANSITIONS = {
    AgentState.CREATED: [AgentState.INITIALIZING],
    AgentState.INITIALIZING: [AgentState.RUNNING, AgentState.FAILED],
    AgentState.RUNNING: [AgentState.PAUSED, AgentState.COMPLETING, AgentState.FAILED, AgentState.TERMINATED, AgentState.SWITCHING],
    AgentState.PAUSED: [AgentState.RUNNING, AgentState.TERMINATED],
    AgentState.COMPLETING: [AgentState.COMPLETED, AgentState.FAILED],
    AgentState.COMPLETED: [],  # Terminal
    AgentState.FAILED: [],  # Terminal
    AgentState.TERMINATED: [],  # Terminal
    AgentState.SWITCHING: [AgentState.INITIALIZING],  # Restart with new model
}
```

### 7.4 Provider Adapters

Abstract interface for AI providers.

```python
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional
from dataclasses import dataclass

@dataclass
class Message:
    role: str  # "user", "assistant", "system"
    content: str

@dataclass  
class ToolCall:
    tool_name: str
    arguments: dict

@dataclass
class CompletionResult:
    content: str
    tool_calls: list[ToolCall]
    tokens_input: int
    tokens_output: int
    finish_reason: str  # "stop", "tool_use", "max_tokens", "error"
    cost_usd: float

class ProviderAdapter(ABC):
    """Abstract base class for AI provider adapters."""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier (e.g., 'anthropic', 'google')."""
        pass
    
    @property
    @abstractmethod
    def available_models(self) -> list[str]:
        """List of available models."""
        pass
    
    @abstractmethod
    async def complete(
        self,
        messages: list[Message],
        model: str,
        system_prompt: Optional[str] = None,
        tools: Optional[list[dict]] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> CompletionResult:
        """Generate a completion."""
        pass
    
    @abstractmethod
    async def complete_stream(
        self,
        messages: list[Message],
        model: str,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming completion."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if provider is available."""
        pass
    
    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        pass
    
    @abstractmethod
    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD."""
        pass
```

### 7.5 Quality Gates

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class GateResult(Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    ERROR = "error"

@dataclass
class GateReport:
    gate_name: str
    result: GateResult
    required: bool
    message: str
    details: Optional[dict] = None
    duration_ms: int = 0

class QualityGate(ABC):
    """Abstract base class for quality gates."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def required(self) -> bool:
        pass
    
    @abstractmethod
    async def run(self, task_id: str, work_dir: str) -> GateReport:
        """Execute the quality gate."""
        pass

class TestsPassGate(QualityGate):
    """Gate that runs pytest and requires all tests to pass."""
    name = "tests_pass"
    required = True
    
    async def run(self, task_id: str, work_dir: str) -> GateReport:
        # Run pytest in isolated environment
        # Use tests from main branch, not working branch
        pass

class CoverageGate(QualityGate):
    """Gate that checks test coverage meets threshold."""
    name = "coverage"
    required = True
    threshold: int = 80
    
    async def run(self, task_id: str, work_dir: str) -> GateReport:
        pass

class NoSecretsGate(QualityGate):
    """Gate that scans for hardcoded secrets."""
    name = "no_secrets"
    required = True
    
    async def run(self, task_id: str, work_dir: str) -> GateReport:
        pass

class DiffReviewGate(QualityGate):
    """Gate that uses AI to review if diff matches task requirements."""
    name = "diff_review"
    required = True
    
    async def run(self, task_id: str, work_dir: str) -> GateReport:
        # Load task definition
        # Generate diff
        # Ask reviewer model: "Does this diff satisfy the acceptance criteria?"
        pass
```

### 7.6 Tracker Agent

The tracker agent maintains project state across sessions.

```python
class TrackerAgent:
    """
    Maintains project state and progress across sessions.
    
    Responsibilities:
    - Update task progress when work completes
    - Detect stalled or failed tasks
    - Generate progress reports
    - Maintain project-level context
    - Sync state to persistent storage
    """
    
    def __init__(self, state_dir: Path):
        self.state_dir = state_dir
        self.model = "claude-haiku"  # Cheap model for tracking
        
    async def on_task_progress(self, task_id: str, progress: dict):
        """Called when a task makes progress."""
        pass
        
    async def on_agent_completed(self, agent_id: str, result: dict):
        """Called when an agent completes work."""
        pass
        
    async def check_stalled_tasks(self) -> list[str]:
        """Return list of tasks that appear stalled."""
        pass
        
    async def generate_status_report(self) -> str:
        """Generate human-readable status report."""
        pass
        
    async def sync_state(self):
        """Persist current state to disk."""
        pass
```

---

## 8. Implementation Phases

### Phase 0: Foundation Stabilization (Week 1)

**Goal:** Existing codebase is reliable and documented.

#### Task 0.1: Environment Verification
- **Description:** Ensure clean install works on fresh machine
- **Acceptance Criteria:**
  - `pip install -e .` succeeds
  - `python -m pytest tests/` passes all tests
  - `python smoke_test.py` passes
- **Estimated Effort:** 4 hours

#### Task 0.2: Fix Hardcoded Paths
- **Description:** Replace all absolute paths with relative/configurable paths
- **Files to Modify:**
  - All `.md` files referencing `/Users/john/`
  - Any source files with hardcoded paths
- **Acceptance Criteria:**
  - No absolute paths in codebase
  - All paths derived from config or relative to project root
- **Estimated Effort:** 2 hours

#### Task 0.3: Clean Up Existing Code
- **Description:** Audit and clean existing `src/core/` modules
- **Tasks:**
  - Add missing `__init__.py` exports
  - Fix any broken imports
  - Remove dead code
  - Ensure all tests pass
- **Acceptance Criteria:**
  - All 631+ tests pass
  - No import errors
  - Public API clearly documented
- **Estimated Effort:** 8 hours

#### Task 0.4: Documentation Audit
- **Description:** Document what currently works (honestly)
- **Deliverables:**
  - Updated README with accurate status
  - CHANGELOG with current state
  - ARCHITECTURE.md with component overview
- **Acceptance Criteria:**
  - Documentation matches reality
  - New developer can understand system in 30 minutes
- **Estimated Effort:** 4 hours

---

### Phase 1: Human Interface (Weeks 2-3)

**Goal:** Developer can interact with the system via CLI and see status.

#### Task 1.1: CLI Skeleton
- **Description:** Create CLI tool with basic commands
- **Commands:**
  - `subagent init`
  - `subagent status`
  - `subagent --version`
  - `subagent --help`
- **Acceptance Criteria:**
  - `pip install` makes `subagent` command available
  - Commands produce useful output
  - JSON output mode works
- **Estimated Effort:** 8 hours

#### Task 1.2: Configuration System
- **Description:** Implement YAML configuration loading/validation
- **Files:**
  - `src/subagent/core/config.py` (extend existing)
  - `.subagent/config.yaml` template
- **Acceptance Criteria:**
  - Config loads from file
  - Validation errors are clear
  - Defaults work without config file
- **Estimated Effort:** 6 hours

#### Task 1.3: Task Data Structures
- **Description:** Implement Task schema and storage
- **Files:**
  - `src/subagent/orchestration/task_manager.py`
  - `src/subagent/core/schemas.py` (extend)
- **Acceptance Criteria:**
  - Tasks can be created, read, updated
  - Tasks persist to JSON files
  - Task IDs are unique and collision-resistant
- **Estimated Effort:** 8 hours

#### Task 1.4: Task CLI Commands
- **Description:** Implement task management commands
- **Commands:**
  - `subagent task add "description"`
  - `subagent task list`
  - `subagent task show <id>`
- **Acceptance Criteria:**
  - Tasks can be created from CLI
  - Task list shows all tasks with status
  - Task details are readable
- **Estimated Effort:** 6 hours

#### Task 1.5: Status Display
- **Description:** Implement comprehensive status output
- **Files:**
  - `src/subagent/cli/commands/status.py`
  - `src/subagent/cli/formatters.py`
- **Acceptance Criteria:**
  - Shows active tasks, agents, recent activity
  - Both human-readable and JSON formats
  - Updates in real-time with `--watch`
- **Estimated Effort:** 6 hours

#### Task 1.6: Log Viewer
- **Description:** Implement log viewing and tailing
- **Commands:**
  - `subagent logs`
  - `subagent logs --follow`
  - `subagent logs --task=<id>`
- **Acceptance Criteria:**
  - Shows recent activity
  - `--follow` updates in real-time
  - Filtering works correctly
- **Estimated Effort:** 4 hours

---

### Phase 2: Persistent State (Week 4)

**Goal:** State survives crashes, handoffs work.

#### Task 2.1: Session Management
- **Description:** Implement session tracking and persistence
- **Files:**
  - `src/subagent/orchestration/session.py`
- **Acceptance Criteria:**
  - Sessions are created with unique IDs
  - Session state persists to disk
  - Sessions can be listed and inspected
- **Estimated Effort:** 6 hours

#### Task 2.2: State Persistence Layer
- **Description:** Reliable state save/load with crash recovery
- **Files:**
  - `src/subagent/orchestration/state_store.py`
- **Acceptance Criteria:**
  - State saves atomically (no partial writes)
  - State loads correctly after crash
  - Checkpoints created automatically
- **Estimated Effort:** 8 hours

#### Task 2.3: Handoff Protocol Implementation
- **Description:** Implement handoff document generation and parsing
- **Files:**
  - `src/subagent/orchestration/handoff.py`
- **Acceptance Criteria:**
  - Handoff documents generated on session end
  - Handoffs contain all info needed to continue
  - `subagent handoff resume` works
- **Estimated Effort:** 12 hours

#### Task 2.4: Handoff Integration Test
- **Description:** End-to-end test of handoff flow
- **Test Scenario:**
  1. Start task with Claude
  2. Simulate token exhaustion
  3. Generate handoff
  4. Resume with Gemini
  5. Verify work continues correctly
- **Acceptance Criteria:**
  - Test passes reliably
  - Context preserved across handoff
  - No data loss
- **Estimated Effort:** 8 hours

---

### Phase 3: Provider Adapters (Week 5)

**Goal:** Can spawn agents on multiple AI providers.

#### Task 3.1: Provider Base Class
- **Description:** Define abstract provider interface
- **Files:**
  - `src/subagent/execution/providers/base.py`
- **Acceptance Criteria:**
  - Interface covers all required operations
  - Async support
  - Streaming support
- **Estimated Effort:** 4 hours

#### Task 3.2: Claude Provider
- **Description:** Implement Anthropic Claude adapter
- **Files:**
  - `src/subagent/execution/providers/claude.py`
- **Acceptance Criteria:**
  - All Claude models supported
  - Tool use works
  - Streaming works
  - Cost calculation accurate
- **Estimated Effort:** 8 hours

#### Task 3.3: Ollama Provider
- **Description:** Implement Ollama local adapter
- **Files:**
  - `src/subagent/execution/providers/ollama.py`
- **Acceptance Criteria:**
  - All local models supported
  - Works offline
  - Health check detects Ollama availability
- **Estimated Effort:** 6 hours

#### Task 3.4: Gemini Provider
- **Description:** Implement Google Gemini adapter
- **Files:**
  - `src/subagent/execution/providers/gemini.py`
- **Acceptance Criteria:**
  - All Gemini models supported
  - Tool use works
  - Cost calculation accurate
- **Estimated Effort:** 6 hours

#### Task 3.5: Fallback Manager
- **Description:** Implement automatic model fallback
- **Files:**
  - `src/subagent/execution/fallback.py`
- **Acceptance Criteria:**
  - Detects provider failures
  - Automatically switches to next provider
  - Preserves context across switch
- **Estimated Effort:** 8 hours

---

### Phase 4: Agent Lifecycle (Week 6)

**Goal:** Can spawn, monitor, and control agents.

#### Task 4.1: Agent Data Structures
- **Description:** Implement Agent schema and storage
- **Files:**
  - `src/subagent/orchestration/agent_registry.py`
  - `src/subagent/core/schemas.py` (extend)
- **Acceptance Criteria:**
  - Agents can be created, tracked, terminated
  - Agent state persists
  - Agent IDs are unique
- **Estimated Effort:** 6 hours

#### Task 4.2: Agent Spawner
- **Description:** Implement agent creation and initialization
- **Files:**
  - `src/subagent/execution/spawner.py`
- **Acceptance Criteria:**
  - Agents spawn with correct configuration
  - System prompt assembled from templates
  - Permissions enforced from start
- **Estimated Effort:** 10 hours

#### Task 4.3: Agent Monitor
- **Description:** Implement real-time agent monitoring
- **Files:**
  - `src/subagent/execution/monitor.py`
- **Acceptance Criteria:**
  - Progress tracked in real-time
  - Budget usage tracked
  - Activity logged
- **Estimated Effort:** 8 hours

#### Task 4.4: Lifecycle Controls
- **Description:** Implement pause/resume/kill controls
- **Files:**
  - `src/subagent/orchestration/lifecycle.py`
- **Acceptance Criteria:**
  - Agents can be paused without data loss
  - Agents can be resumed from pause
  - Agents can be terminated gracefully
  - Agents can be switched to different model
- **Estimated Effort:** 8 hours

#### Task 4.5: Budget Enforcement
- **Description:** Implement token/time/cost budgets
- **Files:**
  - `src/subagent/orchestration/budget.py`
- **Acceptance Criteria:**
  - Token budget enforced
  - Time budget enforced
  - Cost budget enforced
  - Warnings before limit hit
  - Graceful termination at limit
- **Estimated Effort:** 6 hours

---

### Phase 5: Permissions & Security (Week 7)

**Goal:** Workers cannot escape their sandbox.

#### Task 5.1: Permission System
- **Description:** Implement access control for tools and files
- **Files:**
  - `src/subagent/orchestration/permissions.py`
- **Acceptance Criteria:**
  - Tool permissions enforced
  - File path permissions enforced
  - Violations logged and blocked
- **Estimated Effort:** 10 hours

#### Task 5.2: Tool Interception
- **Description:** Intercept and validate tool calls before execution
- **Files:**
  - `src/subagent/execution/tool_proxy.py`
- **Acceptance Criteria:**
  - All tool calls pass through permission check
  - Forbidden operations blocked
  - Violations logged
- **Estimated Effort:** 8 hours

#### Task 5.3: Protected Test Suite
- **Description:** Ensure workers cannot modify tests
- **Implementation:**
  - Tests run from main branch, not working branch
  - Diff detection for test modifications
  - Automatic rejection if tests modified
- **Acceptance Criteria:**
  - Worker cannot modify tests to pass
  - Test modification detected and blocked
  - Quality gate uses protected tests
- **Estimated Effort:** 8 hours

---

### Phase 6: Quality Gates (Week 8)

**Goal:** Bad work cannot be merged.

#### Task 6.1: Gate Framework
- **Description:** Implement quality gate runner
- **Files:**
  - `src/subagent/quality/runner.py`
  - `src/subagent/quality/gates.py`
- **Acceptance Criteria:**
  - Gates run in isolated environment
  - Results stored and tracked
  - Required gates block merge
- **Estimated Effort:** 8 hours

#### Task 6.2: Test Gate
- **Description:** Implement pytest gate
- **Files:**
  - `src/subagent/quality/gates/tests.py`
- **Acceptance Criteria:**
  - Runs pytest on protected tests
  - Captures pass/fail/skip counts
  - Reports failures clearly
- **Estimated Effort:** 4 hours

#### Task 6.3: Coverage Gate
- **Description:** Implement coverage threshold gate
- **Files:**
  - `src/subagent/quality/gates/coverage.py`
- **Acceptance Criteria:**
  - Measures coverage accurately
  - Configurable threshold
  - Reports coverage by file
- **Estimated Effort:** 4 hours

#### Task 6.4: Diff Review Gate
- **Description:** Implement AI-based diff review
- **Files:**
  - `src/subagent/quality/gates/diff_review.py`
- **Acceptance Criteria:**
  - Compares diff to task requirements
  - Detects off-task work
  - Detects test modification attempts
- **Estimated Effort:** 8 hours

#### Task 6.5: Secret Scan Gate
- **Description:** Implement hardcoded secret detection
- **Files:**
  - `src/subagent/quality/gates/secrets.py`
- **Acceptance Criteria:**
  - Detects common secret patterns
  - Configurable patterns
  - Clear reporting
- **Estimated Effort:** 4 hours

---

### Phase 7: MCP Integration (Week 9)

**Goal:** Works with Claude Code and other AI tools.

#### Task 7.1: MCP Server Core
- **Description:** Implement MCP server
- **Files:**
  - `src/subagent/mcp/server.py`
- **Acceptance Criteria:**
  - MCP protocol compliant
  - Tools discoverable
  - Handles requests correctly
- **Estimated Effort:** 12 hours

#### Task 7.2: MCP Tool Handlers
- **Description:** Implement handlers for all tools
- **Files:**
  - `src/subagent/mcp/handlers.py`
  - `src/subagent/mcp/tools.py`
- **Acceptance Criteria:**
  - All tools from spec implemented
  - Error handling robust
  - Responses well-formatted
- **Estimated Effort:** 12 hours

#### Task 7.3: Claude Code Integration Test
- **Description:** End-to-end test with Claude Code
- **Test Scenario:**
  1. Install MCP server
  2. Configure Claude Code
  3. Use slash commands to spawn agents
  4. Monitor progress
  5. Review and approve
- **Acceptance Criteria:**
  - Integration works smoothly
  - All tools accessible
  - User experience is good
- **Estimated Effort:** 8 hours

---

### Phase 8: Metrics & Value Proof (Week 10)

**Goal:** Quantifiable proof of value.

#### Task 8.1: Cost Tracking
- **Description:** Accurate cost tracking per task/session/project
- **Files:**
  - `src/subagent/metrics/cost_tracker.py`
- **Acceptance Criteria:**
  - Tokens tracked accurately
  - Cost calculated per provider
  - Historical costs stored
- **Estimated Effort:** 6 hours

#### Task 8.2: Naive Comparison
- **Description:** Estimate what naive approach would cost
- **Files:**
  - `src/subagent/metrics/comparator.py`
- **Algorithm:**
  - Estimate total context if no decomposition
  - Calculate cost at base model rates
  - Compare to actual cost with decomposition + cheap models
- **Acceptance Criteria:**
  - Comparison is reasonable and defensible
  - Shows savings percentage
  - Explains methodology
- **Estimated Effort:** 8 hours

#### Task 8.3: Quality Metrics
- **Description:** Track quality improvements over time
- **Metrics:**
  - Test pass rate before/after gates
  - Coverage improvements
  - Error rates
  - Rework frequency
- **Acceptance Criteria:**
  - Metrics stored historically
  - Trends visible
  - Improvements quantified
- **Estimated Effort:** 6 hours

#### Task 8.4: Value Report Generator
- **Description:** Generate comprehensive value reports
- **Files:**
  - `src/subagent/metrics/reporter.py`
- **Output:**
  - Markdown report with charts
  - Cost savings summary
  - Quality improvements
  - Recommendations
- **Acceptance Criteria:**
  - Report is clear and convincing
  - Data is accurate
  - Actionable insights included
- **Estimated Effort:** 8 hours

---

### Phase 9: Task Decomposition (Week 11)

**Goal:** Complex tasks automatically split into focused subtasks.

#### Task 9.1: Decomposition Engine
- **Description:** AI-powered task decomposition
- **Files:**
  - `src/subagent/orchestration/decomposer.py`
- **Acceptance Criteria:**
  - Complex tasks split intelligently
  - Dependencies identified
  - Subtasks are appropriately sized
- **Estimated Effort:** 12 hours

#### Task 9.2: Decomposition Strategies
- **Description:** Implement multiple decomposition strategies
- **Strategies:**
  - Sequential (A → B → C)
  - Parallel (A, B, C simultaneously)
  - Hybrid (some parallel, some sequential)
- **Acceptance Criteria:**
  - Strategy selected based on task type
  - Dependencies respected
  - Parallelism maximized where safe
- **Estimated Effort:** 8 hours

#### Task 9.3: Context Splitting
- **Description:** Intelligent context distribution to subtasks
- **Files:**
  - `src/subagent/orchestration/context_splitter.py`
- **Acceptance Criteria:**
  - Each subtask gets minimal necessary context
  - No critical context lost
  - Token savings achieved
- **Estimated Effort:** 10 hours

---

### Phase 10: Tracker Agent (Week 12)

**Goal:** Project state maintained across all sessions.

#### Task 10.1: Tracker Agent Implementation
- **Description:** Implement persistent tracker agent
- **Files:**
  - `src/subagent/tracking/tracker_agent.py`
- **Acceptance Criteria:**
  - Tracks all task progress
  - Updates state on events
  - Detects stalled tasks
- **Estimated Effort:** 10 hours

#### Task 10.2: Progress Calculation
- **Description:** Accurate progress estimation
- **Files:**
  - `src/subagent/tracking/progress.py`
- **Acceptance Criteria:**
  - Progress calculated from completed/remaining steps
  - Subtask progress aggregates to parent
  - Progress is reliable indicator
- **Estimated Effort:** 6 hours

#### Task 10.3: Status Reports
- **Description:** Generate status reports on demand
- **Files:**
  - `src/subagent/tracking/reporter.py`
- **Acceptance Criteria:**
  - Reports show current state clearly
  - Identify blocked tasks
  - Recommend next actions
- **Estimated Effort:** 6 hours

---

### Phase 11: Prompt Library (Week 13)

**Goal:** Composable, specialized agent configurations.

#### Task 11.1: Prompt Template System
- **Description:** Implement prompt template loading and composition
- **Files:**
  - `src/subagent/prompts/template_engine.py`
- **Acceptance Criteria:**
  - Templates load from YAML/MD files
  - Variables substituted correctly
  - Templates composable
- **Estimated Effort:** 8 hours

#### Task 11.2: Role Templates
- **Description:** Create base role templates
- **Templates:**
  - `planner.md` - Designs solutions
  - `coder.md` - Implements code
  - `tester.md` - Writes tests
  - `reviewer.md` - Reviews work
- **Acceptance Criteria:**
  - Roles produce appropriate behavior
  - Clear separation of concerns
  - Reusable across projects
- **Estimated Effort:** 8 hours

#### Task 11.3: Skill Templates
- **Description:** Create skill templates
- **Templates:**
  - `python.md` - Python expertise
  - `testing.md` - Testing expertise
  - `security.md` - Security awareness
  - `documentation.md` - Documentation skills
- **Acceptance Criteria:**
  - Skills enhance base roles
  - Can combine multiple skills
  - Project-specific skills supported
- **Estimated Effort:** 6 hours

---

### Phase 12: Polish & Documentation (Week 14)

**Goal:** Production-ready release.

#### Task 12.1: Error Handling Audit
- **Description:** Ensure all errors handled gracefully
- **Acceptance Criteria:**
  - No unhandled exceptions
  - User-friendly error messages
  - Recovery suggestions provided
- **Estimated Effort:** 8 hours

#### Task 12.2: Performance Optimization
- **Description:** Optimize hot paths
- **Focus Areas:**
  - State persistence (async)
  - Log writing (buffered)
  - Provider calls (connection pooling)
- **Acceptance Criteria:**
  - No operation takes >100ms (except API calls)
  - Memory usage reasonable
  - No memory leaks
- **Estimated Effort:** 8 hours

#### Task 12.3: Documentation
- **Description:** Comprehensive documentation
- **Deliverables:**
  - README with quick start
  - Full user guide
  - API reference
  - Architecture guide
  - Troubleshooting guide
- **Acceptance Criteria:**
  - New user can start in <10 minutes
  - All features documented
  - Examples for common use cases
- **Estimated Effort:** 16 hours

#### Task 12.4: Release Preparation
- **Description:** Prepare for public release
- **Tasks:**
  - Version bumping
  - Changelog update
  - PyPI publishing
  - GitHub release
- **Acceptance Criteria:**
  - `pip install subagent-control` works
  - Release notes complete
  - Installation verified on fresh machine
- **Estimated Effort:** 4 hours

---

## 9. API Reference

### 9.1 Python API

```python
from subagent import (
    # Core
    init_project,
    get_status,
    
    # Tasks
    create_task,
    get_task,
    list_tasks,
    start_task,
    pause_task,
    cancel_task,
    
    # Agents
    spawn_agent,
    get_agent,
    list_agents,
    pause_agent,
    resume_agent,
    kill_agent,
    
    # Handoffs
    create_handoff,
    resume_from_handoff,
    
    # Quality
    run_quality_gates,
    get_quality_report,
    
    # Metrics
    get_cost_summary,
    get_value_report,
)

# Example usage
from subagent import create_task, spawn_agent, run_quality_gates

# Create a task
task = create_task(
    title="Implement user authentication",
    description="Create auth module with login/logout",
    acceptance_criteria=[
        "User model exists",
        "Login returns JWT",
        "Tests pass with >80% coverage"
    ],
    constraints={
        "max_tokens": 50000,
        "allowed_paths": ["src/auth/**"]
    }
)

# Spawn an agent to work on it
agent = spawn_agent(
    task_id=task.id,
    model="haiku",
    budget_tokens=15000
)

# Wait for completion, then run quality gates
report = run_quality_gates(task.id)
if report.all_passed:
    print("Ready for merge!")
```

### 9.2 CLI Reference

See Section 7.1 for complete CLI command reference.

### 9.3 MCP Tool Reference

See Section 7.2 for complete MCP tool definitions.

---

## 10. Integration Guide

### 10.1 Claude Code Integration

```json
// ~/.config/claude/claude_desktop_config.json
{
  "mcpServers": {
    "subagent": {
      "command": "python",
      "args": ["-m", "subagent.mcp.server"],
      "env": {
        "SUBAGENT_PROJECT_DIR": "/path/to/project"
      }
    }
  }
}
```

### 10.2 VS Code Integration (Future)

```json
// .vscode/settings.json
{
  "subagent.enabled": true,
  "subagent.autoStart": true,
  "subagent.dashboard": true
}
```

### 10.3 CI/CD Integration

```yaml
# .github/workflows/subagent.yaml
name: SubAgent Quality Gates

on:
  pull_request:
    branches: [main]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run SubAgent Quality Gates
        run: |
          pip install subagent-control
          subagent quality run --ci
```

---

## 11. Testing Strategy

### 11.1 Unit Tests

- Every module has corresponding test file
- Mock external dependencies (APIs, file system)
- Target: 90% code coverage

### 11.2 Integration Tests

- Test component interactions
- Use real file system, mock APIs
- Test state persistence and recovery

### 11.3 End-to-End Tests

- Full workflows with real (or simulated) AI
- Test handoff scenarios
- Test failure recovery

### 11.4 Test Data

```
tests/
├── fixtures/
│   ├── tasks/           # Sample task definitions
│   ├── handoffs/        # Sample handoff documents
│   ├── configs/         # Test configurations
│   └── projects/        # Sample project structures
```

---

## 12. Success Metrics

### 12.1 MVP Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Fresh install success | 100% | Automated test on clean VM |
| Handoff success rate | 95%+ | Context preserved across AI switch |
| Cost savings vs naive | 40%+ | Measured on sample projects |
| Quality gate catch rate | 90%+ | Bad code blocked before merge |
| User time to first task | <10 min | From install to first agent spawned |

### 12.2 Long-term Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Rework rate | <20% | Tasks needing re-execution |
| Model fallback success | 95%+ | Seamless switch on failure |
| Test pass rate improvement | 20%+ | Before/after quality gates |
| User satisfaction | 4.5/5 | Survey |

---

## 13. Risk Analysis

### 13.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Provider API changes | Medium | Medium | Abstract provider interface |
| Performance bottlenecks | Medium | Medium | Profile and optimize early |
| State corruption | Low | High | Atomic writes, checksums |
| Context loss on handoff | Medium | High | Comprehensive handoff protocol |

### 13.2 Product Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Too complex to use | Medium | High | CLI-first, progressive disclosure |
| No proven value | Medium | High | Metrics and comparison from day 1 |
| Scope creep | High | Medium | Strict MVP criteria |

---

## 14. Appendices

### 14.1 Glossary

| Term | Definition |
|------|------------|
| **Orchestrator** | The AI session coordinating work (usually the current conversation) |
| **Worker** | A subagent executing a specific task |
| **Tracker** | Agent responsible for maintaining project state |
| **Handoff** | Document enabling AI-to-AI work transfer |
| **Quality Gate** | Automated check that must pass before merge |
| **Context Splitting** | Decomposing large tasks into focused subtasks |

### 14.2 Related Documentation

- Existing codebase: `/Users/john.davis/Documents/GitHub/subAgentTracking/`
- Training materials: `/Users/john.davis/Documents/GitHub/subAgentTracking-training/`

### 14.3 Change Log

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-06 | Initial specification |

---

*This document is the authoritative specification for the SubAgent Control System. Any AI or developer can use this to understand requirements, architecture, and implementation approach.*

*To implement: Start with Phase 0, proceed sequentially. Each phase builds on the previous. The system is not complete until all MVP success criteria are met.*
