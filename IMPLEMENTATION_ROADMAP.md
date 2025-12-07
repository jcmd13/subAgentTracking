# SubAgent Control System - Implementation Roadmap

**Version:** 1.0.1  
**Updated:** 2025-12-06  
**Status:** Ready for Implementation

---

## Quick Reference

| Document | Purpose |
|----------|---------|
| `SUBAGENT_CONTROL_SYSTEM_SPEC.md` | Full architecture, data schemas, component specs |
| `PHASE_0_CRITICAL_FIXES.md` | Bug fixes that must complete before Phase 1 |
| This document | Implementation checklist and progress tracking |

---

## Project Status Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CURRENT STATE                                    │
├─────────────────────────────────────────────────────────────────────┤
│  ✅ Core Modules Exist     │  ❌ 3 Critical Bugs                     │
│  ✅ 631 Tests Pass         │  ❌ Backup Feature Broken               │
│  ✅ Good Architecture      │  ❌ No CLI/UI                           │
│  ✅ Config System          │  ❌ No MCP Integration                  │
│  ✅ Event Logging          │  ❌ No Handoff Protocol                 │
│  ✅ Snapshot Manager       │  ❌ No Provider Adapters                │
└─────────────────────────────────────────────────────────────────────┘

Assessment: 70% foundation complete, 0% user-facing features complete
```

---

## Implementation Phases Summary

| Phase | Name | Duration | Status | Dependencies |
|-------|------|----------|--------|--------------|
| **0** | Critical Bug Fixes | 1 week | 🔴 Not Started | None |
| **1** | Human Interface (CLI) | 2 weeks | ⬜ Blocked | Phase 0 |
| **2** | Persistent State | 1 week | ⬜ Blocked | Phase 1 |
| **3** | Provider Adapters | 1 week | ⬜ Blocked | Phase 2 |
| **4** | Agent Lifecycle | 1 week | ⬜ Blocked | Phase 3 |
| **5** | Permissions & Security | 1 week | ⬜ Blocked | Phase 4 |
| **6** | Quality Gates | 1 week | ⬜ Blocked | Phase 5 |
| **7** | MCP Integration | 1 week | ⬜ Blocked | Phase 6 |
| **8** | Metrics & Value Proof | 1 week | ⬜ Blocked | Phase 7 |
| **9** | Task Decomposition | 1 week | ⬜ Blocked | Phase 8 |
| **10** | Tracker Agent | 1 week | ⬜ Blocked | Phase 9 |
| **11** | Prompt Library | 1 week | ⬜ Blocked | Phase 10 |
| **12** | Polish & Release | 1 week | ⬜ Blocked | Phase 11 |

**Total Estimated Duration:** 14 weeks (solo developer)

---

## Phase 0: Critical Bug Fixes

**Duration:** 1 week  
**Status:** 🔴 NOT STARTED  
**Blocker Level:** MUST COMPLETE BEFORE ANY NEW FEATURES

### Critical Issues (System Non-Functional)

| Task | Description | Est. | Status |
|------|-------------|------|--------|
| 0.1.1 | BackupManager missing `is_available()`, `authenticate()`, `backup_session()` | 4h | ⬜ |
| 0.1.2 | Replace deprecated `datetime.utcnow()` with `datetime.now(timezone.utc)` | 1h | ⬜ |
| 0.1.3 | Thread safety on `_parent_event_stack` using ContextVars | 3h | ⬜ |

### High Priority Issues

| Task | Description | Est. | Status |
|------|-------------|------|--------|
| 0.2.1 | Create custom exception hierarchy | 4h | ⬜ |
| 0.2.2 | Make token budget configurable via config | 0.5h | ⬜ |
| 0.2.3 | Fix ValidationEvent type mismatch (case normalization) | 1h | ⬜ |
| 0.2.4 | Fix session duration timezone bug | 1h | ⬜ |

### Medium Priority Issues

| Task | Description | Est. | Status |
|------|-------------|------|--------|
| 0.3.1 | Fix schema validation bypass (don't write invalid events) | 0.5h | ⬜ |
| 0.3.2 | Make file operations atomic (temp + rename) | 1h | ⬜ |
| 0.3.3 | Add retry on snapshot write failure | 1h | ⬜ |
| 0.3.4 | Expand event ID format to 6 digits | 0.25h | ⬜ |

### Design Improvements

| Task | Description | Est. | Status |
|------|-------------|------|--------|
| 0.4.1 | Persist snapshot counter across restarts | 2h | ⬜ |
| 0.4.2 | Refactor circular dependencies with interfaces | 4h | ⬜ |
| 0.4.3 | Thread-safe shutdown (use init lock) | 0.5h | ⬜ |

### Phase 0 Exit Criteria

- [ ] All critical issues fixed and tested
- [ ] All high priority issues fixed and tested
- [ ] All medium priority issues fixed and tested
- [ ] Full test suite passes (631+ tests)
- [ ] Smoke test passes
- [ ] `grep -r "utcnow" src/` returns nothing
- [ ] BackupManager fully functional
- [ ] Clean install on fresh machine works

---

## Phase 1: Human Interface (CLI)

**Duration:** 2 weeks  
**Status:** ⬜ BLOCKED (waiting for Phase 0)

### Tasks

| Task | Description | Est. | Status |
|------|-------------|------|--------|
| 1.1 | CLI skeleton with typer (`subagent init/status/--help`) | 8h | ⬜ |
| 1.2 | Configuration system (YAML loading, validation, defaults) | 6h | ⬜ |
| 1.3 | Task data structures (schema, storage, unique IDs) | 8h | ⬜ |
| 1.4 | Task CLI commands (`task add/list/show`) | 6h | ⬜ |
| 1.5 | Status display (human + JSON formats, `--watch`) | 6h | ⬜ |
| 1.6 | Log viewer (`logs`, `logs --follow`, `logs --task=`) | 4h | ⬜ |

### Phase 1 Exit Criteria

- [ ] `pip install -e .` makes `subagent` command available
- [ ] `subagent init` creates `.subagent/` directory structure
- [ ] `subagent status` shows system state
- [ ] `subagent task add "description"` creates task
- [ ] `subagent task list` shows all tasks
- [ ] `subagent logs --follow` tails activity

---

## Phase 2: Persistent State

**Duration:** 1 week  
**Status:** ⬜ BLOCKED

### Tasks

| Task | Description | Est. | Status |
|------|-------------|------|--------|
| 2.1 | Session management (unique IDs, persistence) | 6h | ⬜ |
| 2.2 | State persistence layer (atomic saves, crash recovery) | 8h | ⬜ |
| 2.3 | Handoff protocol implementation | 12h | ⬜ |
| 2.4 | Handoff integration test (Claude → file → Gemini) | 8h | ⬜ |

### Phase 2 Exit Criteria

- [ ] Sessions tracked with unique IDs
- [ ] State survives process crash
- [ ] Handoff documents generated on session end
- [ ] `subagent handoff resume` continues from handoff

---

## Phase 3: Provider Adapters

**Duration:** 1 week  
**Status:** ⬜ BLOCKED

### Tasks

| Task | Description | Est. | Status |
|------|-------------|------|--------|
| 3.1 | Provider base class (abstract interface) | 4h | ⬜ |
| 3.2 | Claude provider (Anthropic API) | 8h | ⬜ |
| 3.3 | Ollama provider (local models) | 6h | ⬜ |
| 3.4 | Gemini provider (Google API) | 6h | ⬜ |
| 3.5 | Fallback manager (auto-switch on failure) | 8h | ⬜ |

### Phase 3 Exit Criteria

- [ ] Can call Claude API through provider
- [ ] Can call Ollama through provider
- [ ] Can call Gemini through provider
- [ ] Auto-fallback on rate limit/error

---

## Phase 4: Agent Lifecycle

**Duration:** 1 week  
**Status:** ⬜ BLOCKED

### Tasks

| Task | Description | Est. | Status |
|------|-------------|------|--------|
| 4.1 | Agent data structures (schema, storage, registry) | 6h | ⬜ |
| 4.2 | Agent spawner (create, configure, start) | 10h | ⬜ |
| 4.3 | Agent monitor (progress, health, activity) | 8h | ⬜ |
| 4.4 | Lifecycle controls (pause/resume/kill/switch) | 8h | ⬜ |
| 4.5 | Budget enforcement (tokens/time/cost limits) | 6h | ⬜ |

### Phase 4 Exit Criteria

- [ ] Agents spawn with configured model
- [ ] Progress tracked in real-time
- [ ] Agents can be paused/resumed/killed
- [ ] Budget exceeded → graceful termination

---

## Phase 5: Permissions & Security

**Duration:** 1 week  
**Status:** ⬜ BLOCKED

### Tasks

| Task | Description | Est. | Status |
|------|-------------|------|--------|
| 5.1 | Permission system (tools, files, capabilities) | 10h | ⬜ |
| 5.2 | Tool interception (validate before execute) | 8h | ⬜ |
| 5.3 | Protected test suite (prevent test modification) | 8h | ⬜ |

### Phase 5 Exit Criteria

- [ ] Tool calls checked against permissions
- [ ] File access limited to allowed paths
- [ ] Test modification detected and blocked

---

## Phase 6: Quality Gates

**Duration:** 1 week  
**Status:** ⬜ BLOCKED

### Tasks

| Task | Description | Est. | Status |
|------|-------------|------|--------|
| 6.1 | Gate framework (runner, result storage) | 8h | ⬜ |
| 6.2 | Test gate (pytest with protected tests) | 4h | ⬜ |
| 6.3 | Coverage gate (threshold enforcement) | 4h | ⬜ |
| 6.4 | Diff review gate (AI-based task vs work comparison) | 8h | ⬜ |
| 6.5 | Secret scan gate (hardcoded credential detection) | 4h | ⬜ |

### Phase 6 Exit Criteria

- [ ] Gates run in isolated environment
- [ ] Required gates block merge
- [ ] Test modification attempts flagged
- [ ] Coverage below threshold fails

---

## Phase 7: MCP Integration

**Duration:** 1 week  
**Status:** ⬜ BLOCKED

### Tasks

| Task | Description | Est. | Status |
|------|-------------|------|--------|
| 7.1 | MCP server core (protocol compliance) | 12h | ⬜ |
| 7.2 | MCP tool handlers (all tools from spec) | 12h | ⬜ |
| 7.3 | Claude Code integration test | 8h | ⬜ |

### Phase 7 Exit Criteria

- [ ] MCP server starts and responds
- [ ] All tools accessible from Claude Code
- [ ] End-to-end workflow works

---

## Phase 8: Metrics & Value Proof

**Duration:** 1 week  
**Status:** ⬜ BLOCKED

### Tasks

| Task | Description | Est. | Status |
|------|-------------|------|--------|
| 8.1 | Cost tracking (per task/session/project) | 6h | ⬜ |
| 8.2 | Naive comparison (estimated vs actual cost) | 8h | ⬜ |
| 8.3 | Quality metrics (pass rates, coverage trends) | 6h | ⬜ |
| 8.4 | Value report generator | 8h | ⬜ |

### Phase 8 Exit Criteria

- [ ] Cost tracked accurately per model
- [ ] "Saved X% vs naive approach" calculated
- [ ] Reports exportable as Markdown

---

## Phase 9: Task Decomposition

**Duration:** 1 week  
**Status:** ⬜ BLOCKED

### Tasks

| Task | Description | Est. | Status |
|------|-------------|------|--------|
| 9.1 | Decomposition engine (AI-powered splitting) | 12h | ⬜ |
| 9.2 | Decomposition strategies (sequential/parallel/hybrid) | 8h | ⬜ |
| 9.3 | Context splitting (minimal context per subtask) | 10h | ⬜ |

### Phase 9 Exit Criteria

- [ ] Complex tasks auto-decompose
- [ ] Dependencies tracked and respected
- [ ] Token savings achieved

---

## Phase 10: Tracker Agent

**Duration:** 1 week  
**Status:** ⬜ BLOCKED

### Tasks

| Task | Description | Est. | Status |
|------|-------------|------|--------|
| 10.1 | Tracker agent implementation | 10h | ⬜ |
| 10.2 | Progress calculation (aggregation, estimation) | 6h | ⬜ |
| 10.3 | Status reports (on-demand, scheduled) | 6h | ⬜ |

### Phase 10 Exit Criteria

- [ ] Progress tracked across sessions
- [ ] Stalled tasks detected
- [ ] Reports generated accurately

---

## Phase 11: Prompt Library

**Duration:** 1 week  
**Status:** ⬜ BLOCKED

### Tasks

| Task | Description | Est. | Status |
|------|-------------|------|--------|
| 11.1 | Prompt template system | 8h | ⬜ |
| 11.2 | Role templates (planner, coder, tester, reviewer) | 8h | ⬜ |
| 11.3 | Skill templates (python, testing, security, docs) | 6h | ⬜ |

### Phase 11 Exit Criteria

- [ ] Templates load and compose
- [ ] Roles produce appropriate behavior
- [ ] Skills enhance base capabilities

---

## Phase 12: Polish & Release

**Duration:** 1 week  
**Status:** ⬜ BLOCKED

### Tasks

| Task | Description | Est. | Status |
|------|-------------|------|--------|
| 12.1 | Error handling audit | 8h | ⬜ |
| 12.2 | Performance optimization | 8h | ⬜ |
| 12.3 | Documentation (README, guides, API ref) | 16h | ⬜ |
| 12.4 | Release preparation (PyPI, GitHub) | 4h | ⬜ |

### Phase 12 Exit Criteria

- [ ] No unhandled exceptions
- [ ] All operations fast (<100ms except API)
- [ ] Documentation complete
- [ ] `pip install subagent-control` works

---

## MVP Success Checklist

All of these must be true for MVP:

- [ ] Fresh `pip install` on new machine succeeds
- [ ] Integrates with Claude Code via MCP server
- [ ] Slash commands spawn and control subagents
- [ ] Live review of work in progress
- [ ] Automatic handoff on failure/token exhaustion
- [ ] Auto-fallback to alternative models (Claude → Gemini → Ollama)
- [ ] Cost comparison: "This saved X% vs naive approach"
- [ ] State survives unexpected failure, internet loss

---

## How to Use This Document

### For Human Developers

1. Start with Phase 0 (Critical Bug Fixes)
2. Complete all tasks before moving to next phase
3. Check exit criteria before considering phase complete
4. Update status as you progress

### For AI Developers

1. Read `SUBAGENT_CONTROL_SYSTEM_SPEC.md` for full context
2. Read `PHASE_0_CRITICAL_FIXES.md` for detailed bug fix instructions
3. Check this document for current status
4. Pick up tasks from the first incomplete phase
5. Update status and commit when tasks complete

### For Handoff

When switching between AI sessions or developers:

1. Generate handoff with current status
2. Include: completed tasks, in-progress work, blockers
3. Reference specific task IDs from this document
4. Include any decisions made during implementation

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-06 | Initial specification |
| 1.0.1 | 2025-12-06 | Added Phase 0 critical fixes from code review |

---

*This document is the implementation tracking checklist. Update task statuses as work progresses.*
