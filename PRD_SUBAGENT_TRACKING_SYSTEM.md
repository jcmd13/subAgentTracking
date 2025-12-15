# Product Requirements Document: SubAgent Tracking System

**Version**: 1.0  
**Date**: 2025-12-15  
**Author**: Roo Architect  
**Status**: Active Development (v0.1.0 MVP)

---

## Executive Summary

### Vision Statement
SubAgent Tracking System is **"git for AI agents"** - a universal tracking, observability, and recovery system for Claude Code agentic workflows that provides complete history, perfect recovery, and data-driven optimization.

### Problem Statement
Claude Code multi-agent workflows suffer from:
- **Context Loss**: Session crashes lose all work (no recovery)
- **Token Waste**: Hitting token limits requires rebuilding entire context (150k+ tokens)
- **Debugging Blindness**: No visibility into "why did the agent do that?"
- **No Learning**: Same mistakes repeated across sessions
- **Performance Mystery**: No metrics to identify bottlenecks
- **Collaboration Gaps**: No way to hand off work between sessions/developers

### Solution Overview
A three-tier tracking system that logs every agent action, creates periodic state snapshots, and provides intelligent recovery with **85-90% token savings** on recovery operations.

### Success Metrics
- ✅ **Never lose work**: 100% recovery success rate
- ✅ **Token savings**: >85% reduction on recovery operations
- ✅ **Setup time**: <15 minutes (including OAuth)
- ✅ **Performance**: <1ms logging overhead per event
- ✅ **Test coverage**: >85% (currently achieved)
- ✅ **Adoption**: Used in >50% of Claude Code projects (future goal)

---

## Current State Assessment

### What's Working (70% Foundation Complete)

#### Core Infrastructure ✅
- **Activity Logger** ([`activity_logger.py`](src/core/activity_logger.py)): 1,100 lines, 87% coverage
  - 7 event types (agent_invocation, tool_usage, file_operation, decision, error, context_snapshot, validation)
  - Thread-based async writer (<1ms overhead)
  - JSONL format with gzip compression
  - Schema validation with Pydantic
  
- **Snapshot Manager** ([`snapshot_manager.py`](src/core/snapshot_manager.py)): 93% coverage
  - Auto-triggers (every 10 agents OR 20k tokens)
  - JSON snapshots with compression
  - Recovery in <50ms (target: <1s)
  - Git integration for change tracking
  
- **Analytics DB** ([`analytics_db.py`](src/core/analytics_db.py)): 98% coverage
  - SQLite with 7 indexed tables
  - Event ingestion >3000/sec (target: >1000/sec)
  - Query latency <5ms (target: <10ms)
  - Complete query interface for performance metrics

- **Configuration System** ([`config.py`](src/core/config.py)): 91% coverage
  - Centralized config management
  - Environment variable support
  - Path management for all tracking directories

- **Event Schemas** ([`schemas.py`](src/core/schemas.py)): 100% coverage
  - Pydantic models for all 7 event types
  - Comprehensive field validation

#### Test Suite ✅
- **279 tests** across 6,809 lines of test code
- **85% overall coverage** (exceeds 70% target)
- **631 tests passing** (some failures in integration)
- Performance benchmarks all exceeded targets

### What's Missing (0% User-Facing Features)

#### Critical Blockers ❌
1. **Phase 0 Bugs** (MUST FIX FIRST):
   - [`BackupManager`](src/core/backup_manager.py) missing core methods (`is_available()`, `authenticate()`, `backup_session()`)
   - Deprecated `datetime.utcnow()` usage (needs `datetime.now(timezone.utc)`)
   - Thread safety issues on `_parent_event_stack` (needs ContextVars)
   
2. **No CLI** (Phase 1, 2 weeks):
   - No `subagent` command-line tool
   - No task management (`task add/list/show`)
   - No status display (`subagent status`)
   - No log viewer (`subagent logs --follow`)

3. **No MCP Integration** (Phase 7, 1 week):
   - Cannot integrate with Claude Code via MCP server
   - No tool handlers for Claude Code tools
   - No end-to-end workflow testing

4. **Incomplete Provider Adapters** (Phase 3, 1 week):
   - Stubs exist for Claude, Gemini, Ollama
   - No actual API integration
   - Fallback manager implemented but untested

#### Storage Migration ⚠️
- Project uses **`.claude/`** directory (AI-specific)
- Should migrate to **`.subagent/`** (AI-agnostic)
- Backward compatibility needed for existing users
- Migration path: `SUBAGENT_MIGRATE_LEGACY=1` env var

---

## Product Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     USER INTERFACE LAYER                        │
│  CLI (subagent cmd) │ MCP Server │ Web Dashboard (future)      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    ORCHESTRATION LAYER                          │
│  Agent Coordinator │ Model Router │ Task Decomposer            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      TRACKING LAYER                             │
│  Activity Logger │ Snapshot Manager │ Analytics Engine         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      STORAGE LAYER                              │
│  Local (JSONL/JSON) │ Google Drive │ AWS S3 (future)           │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Agent Action
    ↓
Activity Logger (async, <1ms)
    ↓
Event Queue
    ↓ (background thread)
JSONL Write + Analytics DB
    ↓ (trigger check)
Snapshot Manager (every 10 agents OR 20k tokens)
    ↓ (session end)
Backup Manager → Google Drive
```

### Three-Tier Storage Strategy

#### Tier 1: Local Storage (Fast)
- **Location**: `.subagent/` (migrating from `.claude/`)
- **Contents**: 
  - `logs/`: Activity logs (JSONL, gzip compressed)
  - `state/`: Snapshots (JSON, tar.gz compressed)
  - `analytics/`: SQLite database
  - `handoffs/`: Session handoff summaries
- **Retention**: Current + previous session only
- **Size**: ~20 MB max
- **Performance**: <1ms writes, <50ms snapshots

#### Tier 2: Google Drive (Sync)
- **Structure**: `SubAgentTracking/Phase_N/sessions/session_ID/`
- **Contents**:
  - `activity.jsonl.gz` (compressed logs)
  - `snapshots.tar.gz` (compressed snapshots)
  - `handoff.md` (human-readable summary)
  - `analytics_snapshot.db` (SQLite dump)
- **Retention**: Current + previous phase (2 phases)
- **Size**: ~500 MB per phase
- **Cost**: Free (2TB Google Drive)

#### Tier 3: AWS S3 Glacier (Archive - Future)
- **Storage Class**: Glacier Deep Archive
- **Contents**: Completed phases >2 back
- **Retention**: Forever
- **Size**: ~200 MB per phase (compressed)
- **Cost**: $0.001/GB/month

---

## Feature Specifications

### Feature Set by Phase

#### Phase 0: Critical Bug Fixes (1 week) 🟠 IN PROGRESS
**Status**: 60% complete (storage migration + some bug fixes done)

**Must-Fix Issues**:
1. **BackupManager Methods** (0.1.1):
   - Implement `is_available()` → check credentials exist
   - Implement `authenticate()` → OAuth flow
   - Implement `backup_session()` → upload to Drive
   - Est: 4h

2. **Datetime Deprecation** (0.1.2): ✅ COMPLETE
   - Replace all `datetime.utcnow()` with `datetime.now(timezone.utc)`
   - Update test fixtures
   - Est: 1h

3. **Thread Safety** (0.1.3): ✅ COMPLETE
   - Use ContextVars for `_parent_event_stack`
   - Add thread-local storage tests
   - Est: 3h

4. **Exception Handling** (0.2.1): 🟠 PARTIAL
   - Create custom exception hierarchy
   - Harden backup_manager error handling
   - Est: 4h remaining

**Exit Criteria**:
- [ ] All 631+ tests pass
- [ ] BackupManager fully functional
- [ ] No deprecated datetime usage
- [ ] Thread-safe event logging
- [ ] Clean install on fresh machine works

#### Phase 1: Human Interface (CLI) (2 weeks) ⬜ BLOCKED
**Goal**: Enable human developers to interact with the tracking system

**Features**:
1. **CLI Skeleton** (1.1):
   - `subagent init` → creates `.subagent/` directory structure
   - `subagent status [--json] [--watch]` → shows system state
   - `subagent --help` → command reference
   - Implementation: typer framework
   - Est: 8h

2. **Configuration System** (1.2):
   - YAML config file loading (`.subagent/config.yaml`)
   - Validation and defaults
   - Environment variable override
   - Est: 6h

3. **Task Management** (1.3-1.4):
   - Task data structures (schema, storage, unique IDs)
   - `subagent task add "description" [-p PRIORITY]`
   - `subagent task list [--json] [--open]`
   - `subagent task show <task_id>`
   - Storage: `.subagent/tasks/tasks.json`
   - Est: 14h

4. **Log Viewer** (1.6):
   - `subagent logs [--follow] [--count N] [--task-id ID]`
   - Tail activity logs with filtering
   - Color-coded output
   - Est: 4h

**Exit Criteria**:
- [ ] `pip install -e .` makes `subagent` command available
- [ ] All CLI commands functional
- [ ] Help text comprehensive
- [ ] Works on macOS, Linux, Windows

#### Phase 2: Persistent State (1 week) 🟢 COMPLETE
**Status**: Implemented

**Features** ✅:
- Session management with unique IDs
- State persistence layer (atomic saves, crash recovery)
- Handoff protocol implementation
- Handoff integration test (Claude → file → Gemini)

#### Phase 3: Provider Adapters (1 week) 🟠 IN PROGRESS
**Goal**: Enable multi-LLM support for cost optimization

**Features**:
1. **Provider Base Class** (3.1): ✅ COMPLETE
   - Abstract interface for all providers
   - Common error handling

2. **Provider Implementations** (3.2-3.4): 🟠 STUBS EXIST
   - **Claude Provider**: Anthropic API integration
   - **Ollama Provider**: Local models + minimax-m2:cloud
   - **Gemini Provider**: Google API integration
   - Each provider: 6-8h implementation

3. **Fallback Manager** (3.5): ✅ COMPLETE
   - Auto-switch on failure/rate limit
   - Fallback chain: Claude → Gemini → MiniMax M2 → Ollama local
   - Est: 8h

**Multi-LLM Strategy**:
| LLM | Use Case | Cost | % of Tasks |
|-----|----------|------|------------|
| Claude Sonnet 3.5 | Complex reasoning | $20/mo (fixed) | 20% |
| Gemini 2.0 Flash | Standard code | Free (5 RPM) | 40% |
| MiniMax M2 | Web research, code review | Free | 30% |
| Perplexity Pro | Real-time search | $5 credits/mo | 10% |
| Ollama local | Private/offline | Free | As needed |

**Exit Criteria**:
- [ ] All 3 providers functional with real API calls
- [ ] Fallback manager tested in production
- [ ] Token usage tracked per provider
- [ ] Cost optimization demonstrated (5x more AI for same $40/mo)

#### Phase 7: MCP Integration (1 week) ⬜ BLOCKED
**Goal**: Integrate with Claude Code via MCP server

**Features**:
1. **MCP Server Core** (7.1):
   - Protocol compliance (Model Context Protocol)
   - Server initialization and lifecycle
   - Tool registration
   - Est: 12h

2. **MCP Tool Handlers** (7.2):
   - All tools from spec (read, write, edit, bash, etc.)
   - Tool interception for logging
   - Permission checking
   - Est: 12h

3. **Claude Code Integration Test** (7.3):
   - End-to-end workflow test
   - Slash command testing
   - Subagent spawning
   - Est: 8h

**Exit Criteria**:
- [ ] MCP server starts and responds to Claude Code
- [ ] All tools accessible via slash commands
- [ ] Subagents spawn and execute correctly
- [ ] Full workflow (spawn → work → handoff → resume) works

#### Phase 4: Agent Lifecycle (1 week) ⬜ BLOCKED
**Goal**: Manage agent spawning, monitoring, and lifecycle controls

**Features**:
1. **Agent Data Structures** (4.1):
   - Agent schema, storage, registry
   - Unique agent IDs and metadata
   - Est: 6h

2. **Agent Spawner** (4.2):
   - Create agents with configured model
   - Configuration management
   - Start/initialize agents
   - Est: 10h

3. **Agent Monitor** (4.3):
   - Track progress in real-time
   - Health monitoring
   - Activity tracking
   - Est: 8h

4. **Lifecycle Controls** (4.4):
   - Pause/resume agent execution
   - Kill/terminate agents
   - Switch between agents
   - Est: 8h

5. **Budget Enforcement** (4.5):
   - Token limits per agent
   - Time limits
   - Cost limits
   - Graceful termination on budget exceeded
   - Est: 6h

**Exit Criteria**:
- [ ] Agents spawn with configured model
- [ ] Progress tracked in real-time
- [ ] Agents can be paused/resumed/killed
- [ ] Budget exceeded → graceful termination

#### Phase 5: Permissions & Security (1 week) ⬜ BLOCKED
**Goal**: Implement security controls and permission system

**Features**:
1. **Permission System** (5.1):
   - Tool access permissions
   - File access restrictions
   - Capability-based security
   - Est: 10h

2. **Tool Interception** (5.2):
   - Validate before execute
   - Log all tool calls
   - Block unauthorized operations
   - Est: 8h

3. **Protected Test Suite** (5.3):
   - Prevent test modification
   - Detect tampering attempts
   - Read-only test access
   - Est: 8h

**Exit Criteria**:
- [ ] Tool calls checked against permissions
- [ ] File access limited to allowed paths
- [ ] Test modification detected and blocked

#### Phase 6: Quality Gates (1 week) ⬜ BLOCKED
**Goal**: Automated quality checks before accepting work

**Features**:
1. **Gate Framework** (6.1):
   - Gate runner infrastructure
   - Result storage and reporting
   - Est: 8h

2. **Test Gate** (6.2):
   - Run pytest with protected tests
   - Verify no test modifications
   - Est: 4h

3. **Coverage Gate** (6.3):
   - Enforce coverage thresholds
   - Block merge if below target
   - Est: 4h

4. **Diff Review Gate** (6.4):
   - AI-based comparison of task vs work
   - Verify requirements met
   - Est: 8h

5. **Secret Scan Gate** (6.5):
   - Detect hardcoded credentials
   - Block commits with secrets
   - Est: 4h

**Exit Criteria**:
- [ ] Gates run in isolated environment
- [ ] Required gates block merge
- [ ] Test modification attempts flagged
- [ ] Coverage below threshold fails

#### Phase 8: Metrics & Value Proof (1 week) ⬜ BLOCKED
**Goal**: Demonstrate cost savings and value delivered

**Features**:
1. **Cost Tracking** (8.1):
   - Per-task cost tracking
   - Per-session aggregation
   - Project-level summaries
   - Est: 6h

2. **Naive Comparison** (8.2):
   - Estimate "Claude-only" cost
   - Calculate actual multi-LLM cost
   - Show savings percentage
   - Est: 8h

3. **Quality Metrics** (8.3):
   - Test pass rates over time
   - Coverage trends
   - Error rate tracking
   - Est: 6h

4. **Value Report Generator** (8.4):
   - Markdown reports
   - Charts and visualizations
   - ROI calculations
   - Est: 8h

**Exit Criteria**:
- [ ] Cost tracked accurately per model
- [ ] "Saved X% vs naive approach" calculated
- [ ] Reports exportable as Markdown

#### Phase 9: Task Decomposition (1 week) ⬜ BLOCKED
**Goal**: AI-powered task decomposition for context optimization

**Features**:
1. **Decomposition Engine** (9.1):
   - AI-powered task splitting
   - Dependency detection
   - Subtask generation
   - Est: 12h

2. **Decomposition Strategies** (9.2):
   - Sequential decomposition
   - Parallel decomposition
   - Hybrid approaches
   - Est: 8h

3. **Context Splitting** (9.3):
   - Minimal context per subtask
   - Context inheritance
   - Token optimization
   - Est: 10h

**Exit Criteria**:
- [ ] Complex tasks auto-decompose
- [ ] Dependencies tracked and respected
- [ ] Token savings achieved (30-50% reduction)

#### Phase 10: Tracker Agent (1 week) ⬜ BLOCKED
**Goal**: Specialized agent for progress tracking and reporting

**Features**:
1. **Tracker Agent Implementation** (10.1):
   - Autonomous progress monitoring
   - Cross-session tracking
   - Stall detection
   - Est: 10h

2. **Progress Calculation** (10.2):
   - Task aggregation
   - Completion estimation
   - Velocity tracking
   - Est: 6h

3. **Status Reports** (10.3):
   - On-demand reports
   - Scheduled updates
   - Markdown summaries
   - Est: 6h

**Exit Criteria**:
- [ ] Progress tracked across sessions
- [ ] Stalled tasks detected automatically
- [ ] Reports generated accurately

#### Phase 11: Prompt Library (1 week) ⬜ BLOCKED
**Goal**: Reusable prompt templates for common agent patterns

**Features**:
1. **Prompt Template System** (11.1):
   - Template loading and composition
   - Variable substitution
   - Template versioning
   - Est: 8h

2. **Role Templates** (11.2):
   - Planner role
   - Coder role
   - Tester role
   - Reviewer role
   - Est: 8h

3. **Skill Templates** (11.3):
   - Python expertise
   - Testing proficiency
   - Security awareness
   - Documentation skills
   - Est: 6h

**Exit Criteria**:
- [ ] Templates load and compose correctly
- [ ] Roles produce appropriate behavior
- [ ] Skills enhance base capabilities

#### Phase 12: Polish & Release (1 week) ⬜ BLOCKED
**Goal**: Final polish and production release

**Features**:
1. **Error Handling Audit** (12.1):
   - Review all exception paths
   - Ensure graceful degradation
   - User-friendly error messages
   - Est: 8h

2. **Performance Optimization** (12.2):
   - Profile critical paths
   - Optimize bottlenecks
   - Benchmark final performance
   - Est: 8h

3. **Documentation** (12.3):
   - Complete README
   - Setup guides
   - API reference
   - Video tutorials
   - Est: 16h

4. **Release Preparation** (12.4):
   - PyPI package setup
   - GitHub release
   - Community launch
   - Est: 4h

**Exit Criteria**:
- [ ] No unhandled exceptions
- [ ] All operations fast (<100ms except API)
- [ ] Documentation complete
- [ ] `pip install subagent-control` works

---

### Advanced Features (Already Implemented)

#### Orchestration Layer ✅
**File**: [`src/orchestration/agent_coordinator.py`](src/orchestration/agent_coordinator.py)

**Scout-Plan-Build Pattern**:
- **Scout Phase**: Fast exploration with weak-tier models
- **Plan Phase**: Strategic planning with base/strong tier
- **Build Phase**: Implementation with appropriate tier selection

**Features**:
- Dependency tracking and resolution
- Parallel execution of independent agents (2-4x speedup)
- Context management and optimization (30-50% token reduction)
- Workflow status tracking
- Agent coordination overhead: <5ms

#### Observability Layer ✅
**Files**: [`src/observability/`](src/observability/)

**Analytics Engine** ([`analytics_engine.py`](src/observability/analytics_engine.py)):
- Pattern detection (recurring failures, bottlenecks, inefficiencies)
- Cost analysis (token usage, expensive operations)
- Performance regression detection
- Optimization recommendations

**Fleet Monitor** ([`fleet_monitor.py`](src/observability/fleet_monitor.py)):
- Multi-agent health monitoring
- Resource utilization tracking
- Capacity planning

**Insight Engine** ([`insight_engine.py`](src/observability/insight_engine.py)):
- Automated insight generation
- Trend analysis
- Actionable recommendations

**Realtime Monitor** ([`realtime_monitor.py`](src/observability/realtime_monitor.py)):
- Live agent activity tracking
- Real-time performance metrics
- Alert generation

**Dashboard Server** ([`dashboard_server.py`](src/observability/dashboard_server.py)):
- Web-based dashboard
- Real-time visualization
- Interactive analytics

---

## User Stories

### As a Solo Developer

**Story 1: Crash Recovery**
```
GIVEN I am working on a complex refactoring task
WHEN Claude Code crashes unexpectedly
THEN I can resume from the last snapshot in <10 seconds
AND I lose no more than 5 minutes of work
AND the recovery uses only 5k tokens (vs 150k rebuild)
```

**Story 2: Token Limit Handoff**
```
GIVEN I am approaching the 200k token limit
WHEN the system detects 90% usage (180k tokens)
THEN it auto-generates a handoff summary
AND I can resume in a new session with only 8k tokens
AND I continue exactly where I left off
```

**Story 3: Debugging Agent Decisions**
```
GIVEN an agent made a surprising choice
WHEN I review the activity log
THEN I can see the exact decision point with rationale
AND I can see all available options that were considered
AND I can trace the chain of events that led to the decision
```

### As a Team Lead

**Story 4: End-of-Phase Review**
```
GIVEN my team completed Phase 1 (4 weeks of work)
WHEN I run the phase review
THEN I get a comprehensive insights report showing:
  - Agent performance metrics (success rates, avg duration)
  - Tool effectiveness (which tools were most/least effective)
  - Error patterns (most common failures and resolutions)
  - Token costs breakdown (cost per agent, per task)
  - Actionable recommendations (3+ data-driven improvements)
AND the review completes in <5 minutes
```

**Story 5: Cost Optimization**
```
GIVEN I want to reduce LLM costs
WHEN I review the analytics dashboard
THEN I can see token usage by agent and provider
AND I can identify opportunities to use cheaper models
AND I can implement multi-LLM routing to save 85% on simple tasks
```

### As a New User

**Story 6: Quick Setup**
```
GIVEN I have a fresh Python environment
WHEN I run the setup commands
THEN the entire system is ready in <15 minutes
AND I can log my first event immediately
AND backups work (if I completed OAuth setup)
```

---

## Technical Requirements

### Performance Requirements

| Metric | Target | Current Status |
|--------|--------|----------------|
| **Event logging overhead** | <1ms | ✅ <1ms |
| **Snapshot creation** | <100ms | ✅ <50ms |
| **Snapshot restoration** | <1s | ✅ <50ms |
| **Event ingestion rate** | >1000/sec | ✅ >3000/sec |
| **Query latency** | <10ms | ✅ <5ms |
| **Test coverage** | >70% | ✅ 85% |
| **CLI response time** | <500ms | ⏳ Not impl |
| **Backup upload** | <2 min | ⏳ Broken |

### Scalability Requirements

| Dimension | Target | Notes |
|-----------|--------|-------|
| **Events per session** | 100k+ | SQLite handles 3k inserts/sec |
| **Sessions per phase** | 50+ | ~500MB per phase on Google Drive |
| **Phases per project** | 10+ | Archive to S3 after phase 2 |
| **Concurrent agents** | 5+ | Thread-safe logging |
| **File size limits** | 1GB+ | Streaming compression for large files |

### Security Requirements

1. **Credential Storage**:
   - All OAuth tokens in `.subagent/credentials/` (git-ignored)
   - Encryption at rest (future)
   - No credentials in logs (automatic PII redaction)

2. **Cloud Backup**:
   - OAuth 2.0 for Google Drive (scope: `drive.file` only)
   - User can revoke access anytime
   - All data encrypted in transit (HTTPS)

3. **Privacy**:
   - Local-first design (works 100% offline)
   - Cloud backup is optional
   - User controls all data deletion

### Compatibility Requirements

- **Python**: 3.10+ (required)
- **OS**: macOS, Linux, Windows (Windows partially tested)
- **Claude Code**: Any version (MCP integration required)
- **Google Drive**: Personal or Workspace account
- **Browser**: Any modern browser (for OAuth flow)

---

## Dependencies & Integration

### Core Dependencies

```python
# requirements.txt (MVP)
google-api-python-client >= 2.100.0  # Google Drive API
google-auth-oauthlib >= 1.1.0        # OAuth authentication
pandas >= 2.0.0                      # Data processing
pydantic >= 2.0.0                    # Schema validation
pytest >= 7.4.0                      # Testing
black >= 23.9.0                      # Code formatting
typer >= 0.9.0                       # CLI framework (Phase 1)
```

### Future Dependencies

```python
# Optional (mature phase)
pymongo >= 4.5.0      # MongoDB Atlas
boto3 >= 1.28.0       # AWS S3
fastapi >= 0.104.0    # Web dashboard
websockets >= 12.0    # Real-time collaboration
```

### Integration Points

1. **Claude Code** (via MCP server):
   - Tool interception
   - Slash command handling
   - Subagent spawning

2. **Google Drive API**:
   - OAuth 2.0 authentication
   - Folder management
   - File upload/download

3. **Git** (optional):
   - Track uncommitted changes
   - Include git hashes in snapshots
   - Detect dirty working directory

4. **SQLite**:
   - Local analytics database
   - Zero-config embedded DB

---

## Implementation Roadmap

### Timeline Summary (14 weeks total)

| Phase | Name | Duration | Status | Dependencies |
|-------|------|----------|--------|--------------|
| **0** | Critical Bug Fixes | 1 week | 🟠 60% | None |
| **1** | Human Interface (CLI) | 2 weeks | ⬜ Blocked | Phase 0 |
| **2** | Persistent State | 1 week | 🟢 Complete | Phase 1 |
| **3** | Provider Adapters | 1 week | 🟠 Stubs | Phase 2 |
| **4** | Agent Lifecycle | 1 week | ⬜ Blocked | Phase 3 |
| **5** | Permissions & Security | 1 week | ⬜ Blocked | Phase 4 |
| **6** | Quality Gates | 1 week | ⬜ Blocked | Phase 5 |
| **7** | MCP Integration | 1 week | ⬜ Blocked | Phase 6 |
| **8** | Metrics & Value Proof | 1 week | ⬜ Blocked | Phase 7 |
| **9** | Task Decomposition | 1 week | ⬜ Blocked | Phase 8 |
| **10** | Tracker Agent | 1 week | ⬜ Blocked | Phase 9 |
| **11** | Prompt Library | 1 week | ⬜ Blocked | Phase 10 |
| **12** | Polish & Release | 1 week | ⬜ Blocked | Phase 11 |

### Critical Path (Next 4 Weeks)

**Week 1: Complete Phase 0**
- Fix BackupManager (4h)
- Harden exception handling (4h)
- Verify all 631 tests pass
- Clean install test on fresh machine

**Week 2-3: Implement Phase 1 (CLI)**
- CLI skeleton with typer (8h)
- Configuration system (6h)
- Task management (14h)
- Status display (6h)
- Log viewer (4h)

**Week 4: Complete Phase 3 (Providers)**
- Claude provider implementation (8h)
- Ollama provider implementation (6h)
- Gemini provider implementation (6h)
- Integration testing (8h)

### Release Plan

| Version | Date | Milestone | Features |
|---------|------|-----------|----------|
| v0.1.0 | 2025-11-12 | MVP Released | Core tracking, snapshots, analytics (✅ Complete) |
| v0.2.0 | 2025-12-20 | CLI Ready | Task management, log viewer, status display |
| v0.3.0 | 2026-01-03 | Multi-LLM | All 3 providers working, cost optimization |
| v0.4.0 | 2026-01-31 | MCP Integration | Claude Code integration, subagent spawning |
| v1.0.0 | 2026-02-28 | Production Ready | All 12 phases complete, full polish |

---

## Success Criteria

### MVP Success Checklist (v0.1.0) ✅ COMPLETE

- [x] Activity logging with 7 event types
- [x] State snapshots (auto-triggered)
- [x] SQLite analytics database
- [x] Test coverage >85%
- [x] Performance targets exceeded
- [x] Documentation complete

### Phase 1 Success Checklist (v0.2.0)

- [ ] `pip install -e .` makes `subagent` command available
- [ ] `subagent init` creates directory structure
- [ ] `subagent status` shows system state
- [ ] `subagent task add/list/show` works
- [ ] `subagent logs --follow` tails activity
- [ ] Help text is comprehensive

### Production Success Checklist (v1.0.0)

- [ ] Fresh `pip install` on new machine succeeds
- [ ] Integrates with Claude Code via MCP server
- [ ] Slash commands spawn and control subagents
- [ ] Live review of work in progress
- [ ] Automatic handoff on failure/token exhaustion
- [ ] Auto-fallback to alternative models (Claude → Gemini → Ollama)
- [ ] Cost comparison: "This saved X% vs naive approach"
- [ ] State survives unexpected failure, internet loss

### Adoption Metrics (Post-Launch)

| Metric | 3 Months | 6 Months | 12 Months |
|--------|----------|----------|-----------|
| **GitHub Stars** | 100+ | 500+ | 1000+ |
| **Active Projects** | 10+ | 50+ | 100+ |
| **Community PRs** | 3+ | 10+ | 25+ |
| **Documentation Views** | 1000+ | 5000+ | 10000+ |

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Google Drive API rate limits** | MEDIUM | HIGH | Implement exponential backoff, queue uploads |
| **SQLite performance at scale** | LOW | MEDIUM | Plan MongoDB migration path, test with 100k+ events |
| **Snapshot size growth** | MEDIUM | MEDIUM | Implement snapshot diffing (only save changes) |
| **Token context reconstruction accuracy** | MEDIUM | HIGH | Extensive testing, checksums, redundant context |
| **OAuth token expiration** | LOW | MEDIUM | Auto-refresh, clear error messages |

### Dependency Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Google Drive API changes** | LOW | HIGH | Use stable API version, abstract behind interface |
| **Python version compatibility** | LOW | MEDIUM | Test on 3.10-3.12, avoid bleeding-edge features |
| **Claude Code API changes** | MEDIUM | HIGH | MCP protocol is stable, monitor Claude releases |

### Project Risks

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| **Scope creep** | MEDIUM | HIGH | Strict adherence to roadmap, phase gates |
| **Testing gaps** | MEDIUM | HIGH | Require >70% coverage per module |
| **Documentation drift** | HIGH | MEDIUM | Update docs with every PR, quarterly audit |

---

## Open Questions & Decisions Needed

### Architecture Decisions

1. **Storage Migration Strategy**:
   - **Question**: How to migrate existing `.claude/` users to `.subagent/`?
   - **Options**:
     - A) Force migration (breaking change)
     - B) Symlink approach (backward compatible)
     - C) Support both forever (maintenance burden)
   - **Recommendation**: Option B (symlink via `SUBAGENT_MIGRATE_LEGACY=1`)
   - **Status**: ✅ DECIDED (implemented)

2. **CLI Framework**:
   - **Question**: Which CLI framework to use?
   - **Options**: Click, Typer, argparse
   - **Recommendation**: Typer (modern, type-safe, easy to test)
   - **Status**: ✅ DECIDED (documented in roadmap)

3. **Web Dashboard**:
   - **Question**: Build web dashboard in Phase 2 or defer to v2.0?
   - **Options**:
     - A) Phase 2 (adds 2 weeks)
     - B) Post-v1.0.0 (optional feature)
   - **Recommendation**: Option B (defer to reduce scope)
   - **Status**: ⏳ NEEDS DECISION

### Product Decisions

4. **Pricing Model**:
   - **Question**: Keep 100% free, or add paid tier?
   - **Options**:
     - A) Free forever (open source)
     - B) Free + paid cloud hosting tier
     - C) Freemium (advanced features paid)
   - **Recommendation**: Option A for v1.0, revisit at 1000+ users
   - **Status**: ⏳ NEEDS DECISION

5. **Multi-Developer Support**:
   - **Question**: Support multi-developer collaboration in v1.0?
   - **Options**:
     - A) Yes (Phase 10, adds 1 week)
     - B) No (defer to v2.0)
   - **Recommendation**: Option A (Phase 10 already allocated)
   - **Status**: ✅ DECIDED (in roadmap)

---

## Code Review Findings

**Status**: Comprehensive code review completed
**Detailed Report**: See [`CODE_REVIEW_FINDINGS.md`](CODE_REVIEW_FINDINGS.md)

### Executive Summary

The codebase demonstrates **solid architectural foundations** with 85% test coverage and excellent performance (all targets exceeded by 2-3x). However, several critical issues must be addressed in Phase 0 before building user-facing features.

**Overall Code Quality**: B+ (Good foundation, needs Phase 0 fixes)

| Aspect | Assessment | Details |
|--------|------------|---------|
| Architecture | ⭐⭐⭐⭐☆ | Well-designed event-driven system |
| Test Coverage | ⭐⭐⭐⭐⭐ | 85% overall (exceeds 70% target) |
| Performance | ⭐⭐⭐⭐⭐ | All targets exceeded 2-3x |
| Thread Safety | ⭐⭐⭐☆☆ | Issues in snapshot_manager |
| Error Handling | ⭐⭐⭐⭐☆ | Generally good, needs standardization |

### Critical Issues (Phase 0 Blockers)

1. **BackupManager Authentication** 🔴
   - Issue: [`authenticate()`](src/core/backup_manager.py:347) not integrated with upload methods
   - Impact: Backup features unreliable, may fail silently
   - Effort: 4h

2. **Thread Safety in SnapshotManager** 🔴
   - Issue: Global state variables ([`_snapshot_counter`](src/core/snapshot_manager.py:47)) not protected by locks
   - Impact: Race conditions, potential counter duplication
   - Effort: 3h

3. **Logger Initialization** 🟠
   - Issue: Module logger defined at end of file ([`activity_logger.py:1418`](src/core/activity_logger.py:1418))
   - Impact: Violates conventions, confuses static analyzers
   - Effort: 0.5h

4. **Inconsistent Error Handling** 🟠
   - Issue: Mix of exceptions, None returns, and silent failures
   - Impact: Difficult to debug, unexpected behavior
   - Effort: 4h

**Total Phase 0 Effort**: 12 hours

### Performance Benchmarks (Actual vs Target)

| Metric | Target | Achieved | Status |
|--------|--------|----------|--------|
| Event logging overhead | <1ms | <1ms | ✅ Met |
| Snapshot creation | <100ms | <50ms | ✅ **2x better** |
| Snapshot restoration | <1s | <50ms | ✅ **20x better** |
| Event ingestion rate | >1000/sec | >3000/sec | ✅ **3x better** |
| Query latency | <10ms | <5ms | ✅ **2x better** |

### Test Coverage by Module

| Module | Lines | Coverage | Grade |
|--------|-------|----------|-------|
| [`schemas.py`](src/core/schemas.py) | 421 | 100% | ✅ Excellent |
| [`analytics_db.py`](src/core/analytics_db.py) | ~800 | 98% | ✅ Excellent |
| [`snapshot_manager.py`](src/core/snapshot_manager.py) | 807 | 93% | ✅ Very Good |
| [`config.py`](src/core/config.py) | 449 | 91% | ✅ Very Good |
| [`activity_logger.py`](src/core/activity_logger.py) | 1418 | 87% | ✅ Good |
| **Overall** | **~6800** | **85%** | ✅ **Exceeds Target** |

### Positive Findings ✅

1. **Excellent Schema Design** - 100% coverage, comprehensive Pydantic validation
2. **Performance Excellence** - All targets exceeded by significant margins
3. **Clean Architecture** - Event-driven design with good separation of concerns
4. **Strong Type Safety** - Comprehensive type hints throughout
5. **Good Documentation** - Docstrings on all public functions

### Recommendations

**Immediate (Phase 0)**:
- ✅ Fix BackupManager authentication integration (4h)
- ✅ Add thread safety to snapshot_manager (3h)
- ✅ Standardize error handling patterns (4h)
- ✅ Move logger definitions to module top (0.5h)

**Before Phase 1**:
- ⚠️ Implement backup hash verification (2h)
- ⚠️ Add integration tests for backup workflow (4h)
- ⚠️ Document threading model explicitly (2h)

**Technical Debt (Post-MVP)**:
- 🔵 Reduce global state for better testability
- 🔵 Consider dependency injection pattern
- 🔵 Encrypt credentials at rest

### Security Assessment

**✅ Good Practices**:
- Credentials git-ignored
- OAuth 2.0 with minimal scope (`drive.file` only)
- No hardcoded secrets
- Thread-safe logging with ContextVars

**⚠️ Needs Improvement**:
- Tokens stored in plaintext (acceptable for MVP, encrypt in v1.0)
- No automatic PII redaction in logs (planned feature)
- Token refresh logic not extensively tested

### Migration Status (`.claude/` → `.subagent/`)

**✅ Complete**:
- Config supports both directories
- Symlink creation via `SUBAGENT_MIGRATE_LEGACY=1`
- Backward compatibility maintained
- Documentation updated

**⏳ Remaining**:
- Update some test fixtures to use new paths
- Add migration guide for existing users

---

## Appendix

### Glossary

- **Agent**: An LLM-powered worker that performs a specific task
- **Event**: A logged action (7 types: agent_invocation, tool_usage, etc.)
- **Snapshot**: A point-in-time checkpoint of project state
- **Handoff**: Summary document for session transition
- **Phase**: A major milestone in project development (e.g., Phase 1 = MVP)
- **Session**: A single continuous work period (Claude Code instance)
- **MCP**: Model Context Protocol (standard for LLM tool integration)
- **JSONL**: JSON Lines format (one JSON object per line)

### References

- **Documentation**: 
  - [`PROJECT_MANIFEST.md`](PROJECT_MANIFEST.md) - Complete project overview
  - [`AGENTS.md`](AGENTS.md) - Agent guide for AI developers
  - [`CLAUDE.md`](CLAUDE.md) - Claude Code integration guide
  - [`IMPLEMENTATION_ROADMAP.md`](IMPLEMENTATION_ROADMAP.md) - Implementation checklist
  - [`DEVELOPMENT_ROADMAP.md`](DEVELOPMENT_ROADMAP.md) - Detailed development plan

- **Code**:
  - [`src/core/activity_logger.py`](src/core/activity_logger.py) - Event logging system
  - [`src/core/snapshot_manager.py`](src/core/snapshot_manager.py) - State snapshots
  - [`src/core/analytics_db.py`](src/core/analytics_db.py) - Analytics queries
  - [`src/core/backup_manager.py`](src/core/backup_manager.py) - Google Drive backup

- **Tests**:
  - [`tests/test_activity_logger.py`](tests/test_activity_logger.py) - Activity logger tests
  - [`tests/test_snapshot_manager.py`](tests/test_snapshot_manager.py) - Snapshot tests
  - [`tests/test_analytics_db.py`](tests/test_analytics_db.py) - Analytics tests

### Changelog

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-15 | Initial PRD created from documentation analysis |

---

**Document Status**: DRAFT - Ready for review  
**Next Steps**: Code review → PRD refinement → Implementation kickoff