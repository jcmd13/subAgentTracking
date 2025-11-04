# Agent Tracking & Observability System

**Purpose**: Comprehensive tracking of all agent activities, changes, context, and decisions to prevent loss of work and enable intelligent recovery from errors or token limits.

**Last Updated**: 2025-10-29

---

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Core Tracking Components](#core-tracking-components)
3. [Activity Log Schema](#activity-log-schema)
4. [Session State Management](#session-state-management)
5. [Performance & Tool Analytics](#performance--tool-analytics)
6. [Recovery Protocols](#recovery-protocols)
7. [Implementation Guide](#implementation-guide)

---

## System Architecture

### The Three-Layer Tracking System

```
┌─────────────────────────────────────────────────────────────┐
│                    Layer 1: Real-Time Activity Log           │
│  (Timestamped structured logs of every agent action)        │
│  File: .claude/logs/session_YYYYMMDD_HHMMSS.jsonl          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                 Layer 2: Session State Snapshots             │
│  (Periodic checkpoints of project state + context)          │
│  File: .claude/state/session_YYYYMMDD_HHMMSS_state.json    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│               Layer 3: Historical Analytics DB               │
│  (Aggregated metrics for learning and optimization)         │
│  File: .claude/analytics/agent_metrics.db (SQLite)          │
└─────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Write-Once, Read-Many**: All tracking files are append-only or versioned
2. **Structured Data**: All logs use JSON/JSONL for machine parseability
3. **Human-Readable Summaries**: Each session generates markdown summary
4. **Automatic Recovery**: System can reconstruct state from logs
5. **Zero Performance Impact**: Async logging, no blocking operations

---

## Core Tracking Components

### 1. Activity Log (`.claude/logs/`)

**Purpose**: Timestamped record of EVERY agent action

**Format**: JSON Lines (`.jsonl`) - one event per line

**What Gets Logged**:
- ✅ Agent invocations (which agent, why, by whom)
- ✅ Tool usage (which tool, parameters, duration, success/failure)
- ✅ File operations (read, write, edit with diffs)
- ✅ Decisions made (rationale, alternatives considered)
- ✅ Errors encountered (stack trace, context, attempted fixes)
- ✅ Context snapshots (token usage before/after each agent)
- ✅ Agent communication (orchestrator → subagent messages)
- ✅ Validation results (pass/fail, metrics, corrections)

**Benefits**:
- 📊 Complete audit trail of development session
- 🔍 Debug agent behavior ("why did it choose that tool?")
- 📈 Track performance improvements over time
- 🔄 Enable perfect session replay/continuation

### 2. Session State (`.claude/state/`)

**Purpose**: Periodic snapshots of complete project state

**Format**: JSON with metadata + compressed context

**What Gets Captured**:
- 🎯 Current phase/week/task from PROJECT_STATUS.md
- 📝 Active todos and completion status
- 📂 Modified files since session start (with git hashes)
- 🧠 Agent context summaries (key findings, decisions)
- 🎲 User intent and session goal
- 📊 Token budget remaining
- ⚡ Performance baselines at snapshot time

**Snapshot Triggers**:
- Every 10 agent invocations
- Every 20k tokens consumed
- Before high-risk operations (major refactors)
- On user request ("checkpoint progress")
- After completing each roadmap task

**Benefits**:
- 💾 Resume from any point if session crashes
- 🔄 Jump between different approaches (branches in time)
- 📊 See project evolution over time
- 🎯 Restore context without re-reading entire codebase

### 3. Analytics Database (`.claude/analytics/`)

**Purpose**: Long-term learning and optimization

**Format**: SQLite database with historical metrics

**Tables**:
- `agent_performance` - Per-agent metrics (speed, quality, token efficiency)
- `tool_usage` - Tool effectiveness tracking
- `error_patterns` - Recurring failures and solutions
- `file_hotspots` - Most frequently modified files
- `decision_quality` - Track which approaches worked best
- `session_outcomes` - Success metrics per session

**Queries Enabled**:
- "Which agent is fastest for component extraction?"
- "Which tools cause the most errors?"
- "What's the average token cost for implementing a plugin?"
- "Which validation checks catch the most issues?"

**Benefits**:
- 📈 Continuous improvement of agent prompts
- 🎯 Data-driven agent selection by orchestrator
- 🔍 Identify inefficient patterns
- 💡 Surface best practices automatically

---

## Activity Log Schema

### Event Types and Schemas

#### 1. Agent Invocation Event

```json
{
  "event_type": "agent_invocation",
  "timestamp": "2025-10-29T15:30:45.123Z",
  "session_id": "session_20251029_153000",
  "event_id": "evt_001",
  "parent_event_id": null,
  "agent": {
    "name": "orchestrator",
    "invoked_by": "user",
    "reason": "User requested to start Phase 1"
  },
  "context": {
    "tokens_before": 5000,
    "tokens_after": 8000,
    "tokens_consumed": 3000,
    "files_in_context": ["ROADMAP.md", "PROJECT_STATUS.md"]
  },
  "metadata": {
    "user_request": "Let's start Phase 1",
    "expected_outcome": "Plan and execute Phase 1, Week 1 tasks"
  }
}
```

#### 2. Tool Usage Event

```json
{
  "event_type": "tool_usage",
  "timestamp": "2025-10-29T15:30:47.456Z",
  "session_id": "session_20251029_153000",
  "event_id": "evt_002",
  "parent_event_id": "evt_001",
  "agent": "orchestrator",
  "tool": {
    "name": "Task",
    "subagent_type": "project-manager",
    "description": "Get current project status",
    "parameters": {
      "prompt": "Read PROJECT_STATUS.md and report current phase/task status"
    }
  },
  "execution": {
    "start_time": "2025-10-29T15:30:47.456Z",
    "end_time": "2025-10-29T15:30:49.123Z",
    "duration_ms": 1667,
    "success": true,
    "error": null
  },
  "result": {
    "summary": "Phase 0 complete, Phase 1 not started",
    "tokens_consumed": 2500,
    "files_accessed": ["PROJECT_STATUS.md"]
  }
}
```

#### 3. File Operation Event

```json
{
  "event_type": "file_operation",
  "timestamp": "2025-10-29T15:31:15.789Z",
  "session_id": "session_20251029_153000",
  "event_id": "evt_003",
  "parent_event_id": "evt_002",
  "agent": "config-architect",
  "operation": {
    "type": "write",
    "file_path": "src/core/logger.py",
    "size_bytes": 3456,
    "lines": 128,
    "hash_before": null,
    "hash_after": "a1b2c3d4e5f6...",
    "diff_summary": "Created new structured logging system"
  },
  "context": {
    "task": "Task 1.1: Implement Structured Logging",
    "rationale": "Foundation for performance tracking and debugging"
  }
}
```

#### 4. Decision Event

```json
{
  "event_type": "decision",
  "timestamp": "2025-10-29T15:30:50.000Z",
  "session_id": "session_20251029_153000",
  "event_id": "evt_004",
  "parent_event_id": "evt_001",
  "agent": "orchestrator",
  "decision": {
    "question": "Which agent should handle structured logging implementation?",
    "options": [
      {
        "choice": "config-architect",
        "reasoning": "Logging is infrastructure, matches agent expertise",
        "confidence": 0.95
      },
      {
        "choice": "refactor-agent",
        "reasoning": "Could handle, but not primary focus",
        "confidence": 0.30
      }
    ],
    "selected": "config-architect",
    "rationale": "Best match for infrastructure work, highest confidence"
  }
}
```

#### 5. Error Event

```json
{
  "event_type": "error",
  "timestamp": "2025-10-29T15:32:00.000Z",
  "session_id": "session_20251029_153000",
  "event_id": "evt_005",
  "parent_event_id": "evt_003",
  "agent": "config-architect",
  "error": {
    "type": "ValidationError",
    "message": "Performance budget exceeded: 450ms > 200ms target",
    "severity": "warning",
    "recoverable": true,
    "context": {
      "file": "src/core/logger.py",
      "function": "format_log_entry",
      "measured_latency_ms": 450,
      "target_latency_ms": 200
    },
    "stack_trace": "...",
    "attempted_fix": "Optimized JSON serialization, switched to orjson",
    "fix_successful": true,
    "fix_result": {
      "new_latency_ms": 120,
      "meets_budget": true
    }
  }
}
```

#### 6. Context Snapshot Event

```json
{
  "event_type": "context_snapshot",
  "timestamp": "2025-10-29T15:35:00.000Z",
  "session_id": "session_20251029_153000",
  "event_id": "evt_010",
  "parent_event_id": null,
  "trigger": "every_10_agents",
  "snapshot": {
    "tokens_used": 45000,
    "tokens_remaining": 155000,
    "agents_invoked": 10,
    "tasks_completed": 2,
    "files_modified": 5,
    "current_phase": "Phase 1, Week 1",
    "current_task": "Task 1.2: Configuration Management",
    "active_agents": ["orchestrator", "config-architect"],
    "key_context": [
      "Completed structured logging (Task 1.1)",
      "Working on configuration system (Task 1.2)",
      "Performance: All tasks under 4s budget so far"
    ]
  }
}
```

#### 7. Validation Event

```json
{
  "event_type": "validation",
  "timestamp": "2025-10-29T15:33:00.000Z",
  "session_id": "session_20251029_153000",
  "event_id": "evt_007",
  "parent_event_id": "evt_003",
  "agent": "orchestrator",
  "validation": {
    "type": "performance_budget",
    "target": {
      "component": "src/core/logger.py",
      "metric": "format_latency_ms",
      "threshold": 200,
      "measured": 120
    },
    "result": "PASS",
    "checks": [
      {"name": "latency_budget", "pass": true},
      {"name": "memory_usage", "pass": true},
      {"name": "test_coverage", "pass": false, "actual": 65, "required": 80}
    ],
    "action_required": "Add 15% more test coverage"
  }
}
```

---

## Session State Management

### State Snapshot Schema

```json
{
  "snapshot_metadata": {
    "snapshot_id": "snap_20251029_153500",
    "session_id": "session_20251029_153000",
    "timestamp": "2025-10-29T15:35:00.000Z",
    "snapshot_number": 3,
    "trigger": "every_20k_tokens"
  },
  "project_state": {
    "current_phase": "Phase 1, Week 1",
    "current_task": "Task 1.2: Configuration Management",
    "overall_completion": "8%",
    "phase_1_completion": "10%"
  },
  "session_progress": {
    "start_time": "2025-10-29T15:30:00.000Z",
    "elapsed_minutes": 5,
    "user_goal": "Start Phase 1 and complete Week 1 foundation tasks",
    "completed_tasks": [
      "Task 1.1: Structured Logging System"
    ],
    "in_progress_tasks": [
      "Task 1.2: Configuration Management"
    ],
    "next_tasks": [
      "Task 1.3: Project Reorganization"
    ]
  },
  "context_summary": {
    "tokens_used": 45000,
    "tokens_remaining": 155000,
    "token_efficiency": "2500 tokens/task avg",
    "agents_invoked": 10,
    "files_in_context": [
      "PROJECT_STATUS.md",
      "ROADMAP.md",
      "optimized_stt_server_v3.py",
      "src/core/logger.py",
      "src/core/config.py"
    ]
  },
  "file_changes": {
    "created": [
      {
        "path": "src/core/logger.py",
        "hash": "a1b2c3d4...",
        "size_bytes": 3456,
        "lines": 128,
        "created_by": "config-architect",
        "purpose": "Structured logging foundation"
      }
    ],
    "modified": [
      {
        "path": "PROJECT_STATUS.md",
        "hash_before": "x1x2x3x4...",
        "hash_after": "y1y2y3y4...",
        "modified_by": "project-manager",
        "change_summary": "Marked Task 1.1 complete"
      }
    ],
    "deleted": []
  },
  "agent_context": {
    "orchestrator": {
      "key_decisions": [
        "Assigned Task 1.1 to config-architect",
        "Validated performance budget (PASS)"
      ],
      "active_workflow": "Phase 1 Week 1 execution",
      "pending_validations": ["test_coverage for logger.py"]
    },
    "config-architect": {
      "completed_work": [
        "Created src/core/logger.py with JSON structured logging"
      ],
      "findings": [
        "Used structlog library for performance",
        "Achieved 120ms latency (60% under budget)"
      ],
      "recommendations": [
        "Add test coverage to reach 80% minimum"
      ]
    },
    "project-manager": {
      "tracked_changes": [
        "Task 1.1 marked complete",
        "Phase 1 progress: 0% → 10%"
      ],
      "next_recommendations": [
        "Task 1.2: Configuration Management via config-architect"
      ]
    }
  },
  "performance_metrics": {
    "avg_task_latency_ms": 3200,
    "latency_budget_met": true,
    "tasks_completed": 1,
    "tasks_failed": 0,
    "avg_tokens_per_task": 2500
  },
  "known_issues": [
    {
      "issue": "Logger test coverage at 65%, need 80%",
      "severity": "medium",
      "blocking": false,
      "assigned_to": "test-engineer",
      "status": "pending"
    }
  ],
  "recovery_info": {
    "can_resume_from_here": true,
    "resume_instruction": "Continue with Task 1.2 (Configuration Management)",
    "context_needed": [
      "PROJECT_STATUS.md",
      "ROADMAP.md Phase 1 Week 1",
      "src/core/logger.py (for reference)"
    ]
  }
}
```

### Snapshot Storage Strategy

**File Naming**: `.claude/state/session_YYYYMMDD_HHMMSS_snapNNN.json`

**Retention Policy**:
- Keep all snapshots for current session
- Keep final snapshot for each session indefinitely
- Keep intermediate snapshots for 7 days
- Archive monthly summaries forever

**Recovery Process**:
1. Find latest snapshot for session
2. Load project state, file changes, agent context
3. Resume from `recovery_info.resume_instruction`
4. Replay activity log from snapshot forward (if session continued)

---

## Performance & Tool Analytics

### Agent Performance Tracking

**Metrics per Agent**:
- ⏱️ Average execution time
- 🎯 Success rate (tasks completed vs failed)
- 📊 Token efficiency (tokens used / task)
- ✅ Validation pass rate
- 🔄 Correction frequency (how often orchestrator sends back)
- 📈 Quality score (based on validation metrics)

**SQL Query Example**:
```sql
SELECT
  agent_name,
  AVG(duration_ms) as avg_duration,
  SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate,
  AVG(tokens_consumed) as avg_tokens
FROM agent_performance
WHERE session_date >= DATE('now', '-30 days')
GROUP BY agent_name
ORDER BY success_rate DESC;
```

### Tool Usage Analytics

**Metrics per Tool**:
- 📊 Usage frequency
- ⏱️ Average execution time
- 🎯 Success rate
- ❌ Error patterns
- 🔄 Retry frequency
- 💡 Alternative tool suggestions

**Example Insights**:
```
Tool: Grep
- Usage: 450 times (30% of all tool calls)
- Avg duration: 1200ms
- Success rate: 95%
- Common error: "Pattern not found" (3% of cases)
- Suggestion: Use Glob first to narrow search scope → 40% faster
```

### Error Pattern Analysis

**Track**:
- Error frequency by type
- Which agents encounter which errors
- Which files cause errors most often
- Successful vs failed fix attempts
- Time to resolution

**Example Pattern**:
```
Error: "Performance budget exceeded"
- Frequency: 12 occurrences
- Agents: config-architect (8), refactor-agent (4)
- Files: src/core/logger.py (5), src/llm/analyzer.py (7)
- Fix success rate: 92%
- Common fix: Switch to faster library (orjson, msgpack)
- Avg time to fix: 3 minutes
```

---

## Recovery Protocols

### Scenario 1: Session Crashes (Error/Bug)

**Automatic Recovery**:
1. On restart, Claude Code detects incomplete session
2. Loads latest state snapshot
3. Presents recovery prompt:
   ```
   🔄 Detected incomplete session from 2025-10-29 15:30

   Last snapshot: 2025-10-29 15:35 (snap_003)
   Progress: Phase 1, Week 1, Task 1.2 in progress

   Completed:
   ✅ Task 1.1: Structured Logging

   In Progress:
   🟡 Task 1.2: Configuration Management (config-architect)

   Files changed:
   - src/core/logger.py (created)
   - PROJECT_STATUS.md (updated)

   Resume from here? [Y/n]
   ```

4. If yes → Load context, continue from Task 1.2
5. If no → Show other snapshot options

### Scenario 2: Token Limit Reached

**Graceful Shutdown**:
1. Detect approaching token limit (e.g., 90% used)
2. Trigger emergency snapshot
3. Generate handoff summary:
   ```markdown
   # Session Handoff Summary

   **Session**: session_20251029_153000
   **Status**: Token limit approaching (180k/200k used)
   **Phase**: Phase 1, Week 1, Task 1.4

   ## What Was Accomplished
   - ✅ Task 1.1: Structured Logging (config-architect)
   - ✅ Task 1.2: Configuration Management (config-architect)
   - ✅ Task 1.3: Project Reorganization (refactor-agent)
   - 🟡 Task 1.4: Error Handling (50% complete, refactor-agent)

   ## Current State
   - File: src/core/error_handler.py (in progress)
   - Last action: Created base exception classes
   - Next action: Add error recovery mechanisms

   ## Files Modified This Session
   1. src/core/logger.py (created)
   2. src/core/config.py (created)
   3. src/plugins/ (restructured)
   4. src/core/error_handler.py (in progress)

   ## To Resume
   1. Open new session
   2. Say: "Resume from session_20251029_153000"
   3. System will load context and continue Task 1.4

   ## Key Context for Next Session
   - Performance: All tasks under 4s budget ✅
   - Tests: Coverage at 75% (target: 80%)
   - Known issues: Need to add retry logic to error_handler.py
   ```

4. Save summary to `.claude/handoffs/session_YYYYMMDD_HHMMSS_handoff.md`
5. Exit gracefully

**Resume in New Session**:
1. User says: "Resume from session_20251029_153000"
2. Load handoff summary (1k tokens vs 50k full context)
3. Load latest snapshot
4. Continue exactly where left off

### Scenario 3: User Switches Direction Mid-Session

**Branch Tracking**:
1. User says: "Actually, let's try a different approach to logging"
2. Create branch snapshot:
   ```json
   {
     "branch_metadata": {
       "branch_from": "snap_003",
       "branch_name": "logging_alternate_approach",
       "reason": "User wants to try different logging library",
       "timestamp": "2025-10-29T15:40:00.000Z"
     },
     "parent_state": { ... },
     "divergence_point": "Task 1.1 completion"
   }
   ```
3. Continue on new branch
4. Can return to original branch anytime:
   ```
   Restore from snap_003 (before logging_alternate_approach branch)
   ```

---

## Implementation Guide

### Phase 1: Core Tracking Infrastructure (Week 1)

#### Step 1.1: Activity Logger (Day 1)
**File**: `src/core/activity_logger.py`

**Features**:
- Async JSONL writer
- Event schema validation
- Automatic session ID generation
- Log rotation (1 file per session)

**Usage**:
```python
from src.core.activity_logger import log_agent_invocation, log_tool_usage

# Log agent invocation
log_agent_invocation(
    agent="orchestrator",
    invoked_by="user",
    reason="Start Phase 1",
    user_request="Let's start Phase 1"
)

# Log tool usage
with log_tool_usage(agent="orchestrator", tool="Task", subagent="project-manager"):
    # ... tool execution ...
    pass
```

#### Step 1.2: State Snapshot Manager (Day 2)
**File**: `src/core/snapshot_manager.py`

**Features**:
- Periodic snapshots (configurable triggers)
- Snapshot diffing (only save changes)
- Compression for large contexts
- Recovery interface

**Usage**:
```python
from src.core.snapshot_manager import take_snapshot, restore_snapshot

# Take snapshot
snapshot_id = take_snapshot(
    trigger="every_10_agents",
    context={...},
    files_modified=[...]
)

# Restore
state = restore_snapshot(snapshot_id)
```

#### Step 1.3: Analytics Database (Day 3)
**File**: `src/core/analytics_db.py`

**Features**:
- SQLite schema setup
- Event ingestion from activity logs
- Query interface
- Dashboard generation

**Tables**:
```sql
CREATE TABLE agent_performance (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    session_id TEXT,
    agent_name TEXT,
    task_type TEXT,
    duration_ms INTEGER,
    tokens_consumed INTEGER,
    success BOOLEAN,
    validation_passed BOOLEAN
);

CREATE TABLE tool_usage (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    session_id TEXT,
    agent_name TEXT,
    tool_name TEXT,
    duration_ms INTEGER,
    success BOOLEAN,
    error_type TEXT
);

CREATE TABLE error_patterns (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    error_type TEXT,
    agent_name TEXT,
    file_path TEXT,
    fix_attempted TEXT,
    fix_successful BOOLEAN,
    resolution_time_ms INTEGER
);
```

### Phase 2: Integration with Agent System (Week 2)

#### Step 2.1: Orchestrator Integration
**File**: `.claude/agents/orchestrator-agent.md`

**Add logging hooks**:
```markdown
## Logging Protocol

**Before invoking any agent:**
```python
log_decision(
    question="Which agent for this task?",
    options=[...],
    selected="config-architect",
    rationale="..."
)
```

**After agent completes:**
```python
log_validation(
    agent="config-architect",
    task="Task 1.1",
    checks={...},
    result="PASS"
)
```
```

#### Step 2.2: PM Integration
**File**: `.claude/agents/project-manager-agent.md`

**Add snapshot triggers**:
```markdown
## Snapshot Triggers

**Trigger snapshot when:**
- Task marked complete
- Phase transition
- Every 5 task completions
- User requests checkpoint
```

#### Step 2.3: Subagent Integration
**File**: Each agent prompt (refactor-agent.md, etc.)

**Add logging section**:
```markdown
## Logging Requirements

**Log key decisions:**
- Why you chose specific approach
- Alternatives considered
- Performance measurements
- Files accessed and why

**Log errors immediately:**
- What failed
- What you tried to fix it
- Whether fix worked
```

### Phase 3: Recovery & Handoff UI (Week 3)

#### Step 3.1: Session Resume Command
**Feature**: `/resume <session_id>`

**Behavior**:
1. Load handoff summary (if exists)
2. Load latest snapshot
3. Display progress summary
4. Ask: "Continue from Task X.Y?"

#### Step 3.2: Session History Browser
**Feature**: `/sessions`

**Output**:
```
Recent Sessions:
1. session_20251029_153000 (45 min ago) - Phase 1 Week 1 [80% complete]
2. session_20251029_100000 (6 hours ago) - Planning Phase 1 [100% complete]
3. session_20251028_150000 (1 day ago) - Agent system design [100% complete]

View details: /session <number>
Resume: /resume <number>
```

#### Step 3.3: Analytics Dashboard
**Feature**: `/analytics [agent_name]`

**Output**:
```
📊 Agent Performance (Last 30 Days)

config-architect:
  Tasks completed: 15
  Avg duration: 4.2 minutes
  Token efficiency: 3200 tokens/task
  Success rate: 93%
  Validation pass rate: 87%

Most used tools:
  1. Edit (45%)
  2. Read (30%)
  3. Bash (15%)

Common errors:
  1. Performance budget exceeded (3 times)
     → Fix: Switch to faster libraries (100% success)
```

---

## Best Practices

### For Orchestrator Agent

1. **Log every decision** with rationale
2. **Snapshot before risky operations** (major refactors, deletions)
3. **Generate handoff summary** when token limit approaches
4. **Track validation failures** and correction attempts

### For Specialized Agents

1. **Log entry/exit** with task summary
2. **Log file access rationale** (why reading this file)
3. **Log performance measurements** for critical paths
4. **Log errors immediately** with context

### For Project Manager

1. **Update PROJECT_STATUS.md** on every task transition
2. **Trigger snapshots** on task completions
3. **Maintain ad-hoc change log** for untracked work
4. **Generate weekly summaries** for long-term record

---

## File Structure

```
.claude/
├── logs/
│   ├── session_20251029_153000.jsonl          # Activity log
│   ├── session_20251029_100000.jsonl
│   └── ...
├── state/
│   ├── session_20251029_153000_snap001.json   # Snapshots
│   ├── session_20251029_153000_snap002.json
│   ├── session_20251029_153000_snap003.json
│   └── ...
├── handoffs/
│   ├── session_20251029_153000_handoff.md     # Handoff summaries
│   └── ...
├── analytics/
│   ├── agent_metrics.db                       # SQLite analytics DB
│   └── weekly_summary_2025W44.md              # Weekly reports
└── AGENT_TRACKING_SYSTEM.md                   # This file
```

---

## Benefits Summary

### 🎯 Prevents Loss of Work
- ✅ Complete audit trail of all changes
- ✅ Recover from crashes/errors
- ✅ Resume after token limits
- ✅ Track ad-hoc changes outside plan

### 📊 Improves Agent Performance
- ✅ Identify slow agents → optimize prompts
- ✅ Track tool effectiveness → choose better tools
- ✅ Learn from errors → prevent recurrence
- ✅ Data-driven agent selection

### 💡 Enhances Context Awareness
- ✅ Reduce context via snapshots (90% savings)
- ✅ Intelligent recovery (load only needed context)
- ✅ Branch in time (try different approaches)
- ✅ Long-term project memory

### 🔍 Enables Debugging
- ✅ "Why did it do that?" → check decision log
- ✅ "Where did it fail?" → error event with stack
- ✅ "How long did it take?" → performance metrics
- ✅ "What changed?" → file operation diffs

---

## Token Budget Impact

### Current System (No Tracking)
- Status check: 50k tokens (full codebase scan)
- Error recovery: 100k tokens (re-explain everything)
- Session resume: 150k tokens (rebuild context)

### With Tracking System
- Status check: 5k tokens (read snapshot)
- Error recovery: 10k tokens (load snapshot + recent activity)
- Session resume: 8k tokens (handoff summary + snapshot)

**Average savings: 85-90% token reduction** for recovery/status operations

---

## Implementation Priority

### Must-Have (Week 1)
1. ✅ Activity logger (event logging)
2. ✅ Snapshot manager (state checkpoints)
3. ✅ Handoff summaries (graceful token limit exit)

### Should-Have (Week 2)
4. ✅ Analytics database (long-term learning)
5. ✅ Recovery UI (/resume command)
6. ✅ Agent integration (logging hooks)

### Nice-to-Have (Week 3)
7. ✅ Session browser (/sessions command)
8. ✅ Analytics dashboard (/analytics)
9. ✅ Branching (try different approaches)

---

## Next Steps

1. **Review this system design** - Does it meet your needs?
2. **Prioritize features** - Which parts are most critical?
3. **Implementation plan** - Integrate into Phase 1 roadmap?
4. **Pilot test** - Try activity logging first, validate approach

**Ready to implement?** I can start building this system immediately, starting with the core activity logger and snapshot manager.
