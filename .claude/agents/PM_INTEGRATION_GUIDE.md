# Project Manager Integration Guide

## Overview

The **Project Manager (PM) Agent** maintains long-term project memory via [`PROJECT_STATUS.md`](../ PROJECT_STATUS.md), eliminating the need for expensive codebase scans to determine project state.

## The Problem It Solves

**Without PM Agent:**
- ❌ "What's our current status?" → Full codebase scan (50k+ tokens)
- ❌ "What should we work on next?" → Read entire roadmap + scan files
- ❌ Ad-hoc changes get lost → No memory of unplanned work
- ❌ Performance regressions unnoticed → No baseline tracking

**With PM Agent:**
- ✅ "What's our current status?" → Read PROJECT_STATUS.md (5k tokens, **90% savings**)
- ✅ "What should we work on next?" → PM recommends from roadmap position
- ✅ Ad-hoc changes logged → Full project memory maintained
- ✅ Performance tracked → Baseline comparisons automatic

## The Single Source of Truth

### PROJECT_STATUS.md Structure

```
PROJECT_STATUS.md
├── Quick Status Overview (Phase completion table)
├── Current Sprint Focus (Active tasks, blockers)
├── Phase Details (All tasks with status)
│   ├── Phase 1: Foundation (Weeks 1-4)
│   ├── Phase 2: Plugin Architecture (Weeks 5-8)
│   ├── Phase 3: UI & Audio (Weeks 9-13)
│   └── Phase 4: Production (Weeks 14-17)
├── Ad-Hoc Changes (Unplanned work log)
├── Performance Baselines (Metrics over time)
├── Known Issues (Technical debt tracker)
├── Dependencies (External requirements)
└── Next Actions (Immediate priorities)
```

### What Gets Tracked

**Task Status:**
- ⚪ Not Started → 🟢 In Progress → ✅ Complete
- ⚠️ Blocked → 🔄 In Review

**For Each Task:**
- Status, dates (start/completion), assigned agent
- Actual outcomes (what was delivered)
- Files created/modified (with line numbers)
- Performance impact (latency, coverage)
- Integration status

**Additional Tracking:**
- Ad-hoc work outside roadmap
- Performance baselines over time
- Technical debt and blockers
- Dependencies and prerequisites

## How Agents Interact with PM

### Orchestrator ↔ PM Protocol

**1. Before Planning Work**
```
Orchestrator: "Get current status"
  ↓
PM: Reads PROJECT_STATUS.md
  ↓
PM: Returns current phase, completed tasks, blockers, next recommendations
  ↓
Orchestrator: Uses status to plan work
```

**2. When Starting Task**
```
Orchestrator: "Starting Task 1.1 (Structured Logging) with config-architect"
  ↓
PM: Updates PROJECT_STATUS.md
  - Mark task 🟢 In Progress
  - Add start date
  - Add assigned agent
  ↓
PM: Confirms to orchestrator
```

**3. When Task Completes**
```
Orchestrator: "Task 1.1 complete. Files: [list]. Coverage: 85%. No regression."
  ↓
PM: Updates PROJECT_STATUS.md
  - Mark task ✅ Complete
  - Add completion date and outcomes
  - Add files created/modified
  - Add performance impact
  - Recalculate phase %
  - Check for unblocked tasks
  ↓
PM: Suggests next task based on dependencies
```

**4. When Requesting Next Steps**
```
Orchestrator: "What should we work on next?"
  ↓
PM: Reads PROJECT_STATUS.md
  ↓
PM: Analyzes completed tasks and dependencies
  ↓
PM: Recommends next logical task with justification
```

### User ↔ PM Interactions

**Status Checks:**
```
User: "What's our current status?"
  ↓
PM: Generates report from PROJECT_STATUS.md
  ↓
PM: Returns formatted status with metrics
```

**Ad-Hoc Work Logging:**
```
User: "I just optimized the audio buffer"
  ↓
PM: Asks for details (files, changes, why, impact)
  ↓
User: Provides details
  ↓
PM: Logs in "Ad-Hoc Changes" section
  ↓
PM: Assesses integration needs
```

**Progress Reports:**
```
User: "Give me a weekly report"
  ↓
PM: Analyzes PROJECT_STATUS.md for date range
  ↓
PM: Generates report (tasks completed, velocity, metrics, blockers)
```

## Integration Examples

### Example 1: Starting Phase 1

**User Request:**
```
"I'm ready to start Phase 1"
```

**Workflow:**

1. **Orchestrator** → **PM**: "Get current status"
   - PM reads PROJECT_STATUS.md
   - PM returns: "Phase 0 complete (MVP), Phase 1 not started"

2. **Orchestrator** plans Phase 1, Week 1, Task 1.1

3. **Orchestrator** → **PM**: "Starting Task 1.1 with config-architect"
   - PM updates PROJECT_STATUS.md (mark 🟢 In Progress)
   - PM confirms

4. **Orchestrator** → **config-architect**: "Create structured logging system"
   - config-architect completes work

5. **Orchestrator** → **PM**: "Task 1.1 complete. [outcomes]"
   - PM updates PROJECT_STATUS.md (mark ✅ Complete)
   - PM recalculates: Phase 1 now 5% complete
   - PM suggests Task 1.2 (Configuration Management)

6. **Orchestrator** → **User**: "Task 1.1 complete. Next: Task 1.2?"

---

### Example 2: User Makes Ad-Hoc Change

**User:**
```
"I just added a helper function to src/audio/buffer.py for debugging"
```

**Workflow:**

1. **PM** asks for details:
   ```
   - What lines in src/audio/buffer.py?
   - What does the helper do?
   - Why was it needed?
   - Performance impact?
   ```

2. **User** provides:
   ```
   - Lines 45-67
   - Added get_buffer_stats() for real-time stats
   - Needed for debugging audio quality
   - <1ms overhead
   ```

3. **PM** logs in PROJECT_STATUS.md:
   ```markdown
   #### 2025-10-29: Audio Buffer Helper Functions
   **Changed By**: User
   **Files Modified**:
   - src/audio/buffer.py (lines 45-67) - Added get_buffer_stats()

   **Motivation**: Needed for debugging audio quality issues
   **Impact**: Enables real-time buffer stats, <1ms overhead
   **Integration Status**: ⚪ Consider adding to Phase 3 audio quality monitoring
   ```

4. **PM** confirms: "Logged in PROJECT_STATUS.md under Ad-Hoc Changes"

---

### Example 3: Performance Baseline Update

**performance-agent** reports:
```
"New baseline after LLM optimization: end-to-end 3.2s (was 3.8s)"
```

**Workflow:**

1. **Orchestrator** → **PM**: "Update baseline: 3.2s end-to-end, -600ms improvement"

2. **PM** updates PROJECT_STATUS.md:
   ```markdown
   ### Phase 1 Baseline (After LLM Optimization)
   **Measured**: 2025-10-30

   **Latency Metrics:**
   - End-to-end (p95): 3.2s ✅ (improved from 3.8s)

   **Changes Since Last:**
   - LLM prompt optimization (saves 400ms)
   - Batch question detection (saves 100ms)
   - Optimized audio buffer (saves 100ms)
   - **Total improvement**: 600ms (16% faster)
   ```

3. **PM** confirms: "Baseline updated in PROJECT_STATUS.md"

---

## PM Agent Invocation Patterns

### Pattern 1: Status Check
```
User: "What's our current status?"
  ↓
[PM Agent reads PROJECT_STATUS.md]
  ↓
PM: "Phase 1, Week 2 | 40% complete | Next: Error handling"
```

### Pattern 2: Next Steps Recommendation
```
Orchestrator: "What should we work on next?"
  ↓
[PM Agent analyzes dependencies in PROJECT_STATUS.md]
  ↓
PM: "Task 2.3 (Input Validation) - dependencies met, security-critical"
```

### Pattern 3: Task Lifecycle Tracking
```
Start: Orchestrator → PM: "Starting Task X"
  ↓
[PM marks 🟢 In Progress]
  ↓
Complete: Orchestrator → PM: "Task X complete [details]"
  ↓
[PM marks ✅ Complete, updates %, suggests next]
```

### Pattern 4: Ad-Hoc Work Logging
```
User: "I changed [something]"
  ↓
[PM asks for details]
  ↓
[PM logs in Ad-Hoc Changes section]
  ↓
[PM assesses integration needs]
```

### Pattern 5: Progress Reporting
```
User: "Weekly report"
  ↓
[PM analyzes last 7 days in PROJECT_STATUS.md]
  ↓
[PM generates report: tasks, velocity, metrics, blockers]
```

---

## Benefits

### For Users

✅ **Instant Status** - No waiting for codebase scans
```
"What's our status?" → 5 seconds (not 2 minutes)
```

✅ **Clear Next Steps** - Always know what to work on
```
"What's next?" → Intelligent recommendation with justification
```

✅ **No Lost Work** - All changes tracked
```
Ad-hoc fixes logged → Integrated into roadmap when appropriate
```

✅ **Performance Visibility** - Track improvements over time
```
Baseline comparisons → See cumulative optimizations
```

### For Orchestrator

✅ **Context Savings** - 90% reduction for status checks
```
Before: 50k tokens (full scan)
After: 5k tokens (read PROJECT_STATUS.md)
```

✅ **Smart Planning** - Knows dependencies and blockers
```
Can plan multi-step workflows without guessing current state
```

✅ **Quality Assurance** - Verify against tracked baselines
```
Performance regression detection automatic
```

### For Specialized Agents

✅ **Clear Assignments** - PM routes work appropriately
```
PM: "Task 1.1 assigned to you (config-architect)"
```

✅ **Success Tracking** - Outcomes recorded for future reference
```
PM logs: What worked, what didn't, lessons learned
```

---

## Best Practices

### 1. Always Start with PM

**Before any planning:**
```
Orchestrator → PM: "Get current status"
```

**Reason:** Ensures planning based on accurate state, not assumptions.

---

### 2. Log Everything

**Task completions:**
```
Orchestrator → PM: "Task complete [full details]"
```

**Ad-hoc changes:**
```
User → PM: "I changed [something]"
```

**Performance updates:**
```
performance-agent → PM: "New baseline [metrics]"
```

**Reason:** Maintains comprehensive project memory.

---

### 3. Update Immediately

**Don't batch updates:**
- ❌ "I'll update PM after finishing 5 tasks"
- ✅ Update PM after each task completes

**Reason:** Keeps PROJECT_STATUS.md current for other agents.

---

### 4. Be Specific

**Always include:**
- Exact file paths
- Line numbers for changes
- Metrics (latency, coverage, etc.)
- Dates

**Reason:** Enables future analysis and debugging.

---

### 5. Check Dependencies

**Before starting task:**
```
PM: "Task X depends on Task Y. Y is ⚪ Not Started. Start Y first."
```

**Reason:** Prevents wasted effort on blocked tasks.

---

## Common Scenarios

### Scenario: Blocked Task

**Situation:** Task 3.1 requires Task 2.4, but 2.4 isn't done

**PM Response:**
```
⚠️ Task 3.1 is blocked

**Depends On**: Task 2.4 (Dependency Injection)
**Status**: Task 2.4 is 🟢 In Progress (60% complete)
**ETA**: Tomorrow

**Recommendation**: Work on Task 3.2 instead (no dependencies)
```

---

### Scenario: Performance Regression

**Situation:** New code causes latency increase

**PM Response:**
```
⚠️ Performance regression detected

**Baseline**: 3.2s end-to-end
**Current**: 3.9s end-to-end
**Regression**: +700ms (+22%)

**Violates**: <4s budget (but still within threshold)
**Action Needed**: Investigate and optimize before proceeding
```

---

### Scenario: Phase Completion

**Situation:** All Phase 1 tasks complete

**PM Response:**
```
✅ Phase 1 Complete!

**Duration**: 4 weeks (on schedule)
**Tasks**: 25/25 (100%)
**Performance**: 3.1s end-to-end ✅
**Coverage**: 84% ✅

**Phase 1 Deliverables:**
- ✅ Structured logging
- ✅ Configuration management
- ✅ Modular architecture
- ✅ All components extracted
- ✅ Feature flags implemented
- ✅ Database schema designed

**Ready for Phase 2**: Plugin Architecture

**Recommendation**: Start Phase 2, Week 5, Task 5.1 (Design Plugin Architecture)

Shall I coordinate with orchestrator to begin Phase 2?
```

---

## Troubleshooting

### PM Says "Can't Find Task"

**Problem:** Task number doesn't exist in PROJECT_STATUS.md

**Solution:**
- Check ROADMAP.md for correct task number
- Ensure PROJECT_STATUS.md is up to date

---

### PM Says "Dependency Not Met"

**Problem:** Trying to start task with incomplete dependencies

**Solution:**
- Complete dependency first, OR
- Ask PM for alternative task without dependencies

---

### Ad-Hoc Work Not Integrated

**Problem:** Logged change not incorporated into roadmap

**Solution:**
- PM marks "Integration Status: ⚪ Needs integration"
- When relevant task starts, review ad-hoc changes
- Incorporate if still relevant

---

## Quick Reference

**PM Agent File:** `.claude/agents/project-manager-agent.md`

**Status File:** `.claude/PROJECT_STATUS.md`

**Status Emojis:**
- ✅ Complete
- 🟢 In Progress
- ⚪ Not Started
- ⚠️ Blocked
- 🔄 In Review

**Key Operations:**
```
PM: Get status          → Current phase, completed tasks, blockers
PM: Log start           → Mark task 🟢 In Progress
PM: Log completion      → Mark task ✅ Complete, update %
PM: Get next steps      → Recommend next task
PM: Log ad-hoc work     → Record unplanned changes
PM: Update baseline     → Record performance metrics
PM: Generate report     → Weekly/phase completion report
```

**Integration Points:**
- Orchestrator checks PM before planning
- Orchestrator notifies PM when starting tasks
- Orchestrator notifies PM when completing tasks
- Users log ad-hoc changes with PM
- performance-agent reports baselines to PM

---

## Summary

The PM Agent + PROJECT_STATUS.md system provides:

1. **Long-Term Memory** - No lost progress or changes
2. **Context Savings** - 90% reduction for status checks
3. **Smart Planning** - Dependency-aware recommendations
4. **Performance Tracking** - Baseline comparisons automatic
5. **Clear Next Steps** - Always know what to work on

**The Result:** Efficient, organized development with full project history.

**Start Using:**
```
"What's our current status?"
```

PM will read PROJECT_STATUS.md and report back instantly.
