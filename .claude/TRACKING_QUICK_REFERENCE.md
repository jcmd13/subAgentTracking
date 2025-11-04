# Agent Tracking System - Quick Reference

**Purpose**: Fast lookup for common tracking patterns and recovery scenarios

---

## 🚀 Quick Start

### When Starting Any Session

```bash
# Automatically creates:
# - .claude/logs/session_YYYYMMDD_HHMMSS.jsonl
# - Session ID assigned
# - Initial snapshot taken
```

### When Resuming After Error/Token Limit

```bash
# User says: "Resume from last session"
# System automatically:
# 1. Finds latest snapshot
# 2. Loads handoff summary (if exists)
# 3. Restores context
# 4. Shows: "Resume from Task X.Y?"
```

---

## 📊 What Gets Tracked

| Event Type | Logged Automatically | Token Cost |
|------------|---------------------|------------|
| Agent invocation | ✅ Yes | ~100 tokens |
| Tool usage | ✅ Yes | ~150 tokens |
| File operations | ✅ Yes | ~200 tokens |
| Decisions made | ✅ Yes | ~250 tokens |
| Errors | ✅ Yes | ~300 tokens |
| Context snapshots | ✅ Every 10 agents | ~500 tokens |
| Validation results | ✅ Yes | ~200 tokens |

**Total overhead**: ~5-8% of session tokens (well worth the recovery benefits)

---

## 💾 Snapshot Triggers

Automatic snapshots happen:
- ✅ Every 10 agent invocations
- ✅ Every 20k tokens consumed
- ✅ Before high-risk operations (major refactors, deletions)
- ✅ After completing roadmap tasks
- ✅ When user requests: "Checkpoint progress"

**Token cost per snapshot**: ~500 tokens
**Recovery savings**: 90% (5k vs 50k tokens to restore context)

---

## 🔄 Recovery Scenarios

### Scenario 1: Session Crashed

```
🔄 Detected incomplete session

Last activity: 2025-10-29 15:35 (5 min ago)
Progress: Phase 1, Week 1, Task 1.2 (in progress)

Completed:
✅ Task 1.1: Structured Logging

Files changed:
- src/core/logger.py (created)
- PROJECT_STATUS.md (updated)

Resume? [Y/n]
```

**Action**: Type `Y` → Continue exactly where left off

---

### Scenario 2: Token Limit Approaching

```
⚠️  Token limit warning: 180k/200k used (90%)

Creating handoff summary...
✅ Saved to: .claude/handoffs/session_20251029_153000_handoff.md

To resume in new session:
Say: "Resume from session_20251029_153000"
```

**Action**: Open new session, say "Resume from session_20251029_153000"

**Token cost to resume**: ~8k (handoff summary + snapshot) vs 150k (rebuild context)

---

### Scenario 3: Want to Try Different Approach

```
User: "Actually, let's try a different logging library"

🌿 Creating branch: logging_alternate_approach
   Branch from: snap_003 (Task 1.1 complete)

You can return to original anytime:
Say: "Restore snap_003"
```

**Action**: Continue on branch, return to original if needed

---

## 📈 Analytics Queries

### Check Agent Performance

```
📊 config-architect (Last 30 days)

Tasks: 15 completed
Speed: 4.2 min average
Tokens: 3200/task average
Success: 93%
Validation: 87% pass rate

Top tools:
1. Edit (45%)
2. Read (30%)
3. Bash (15%)

Common issues:
→ Performance budget exceeded (3x)
→ Fix: Switch to faster libs (100% success)
```

### Check Session History

```
Recent Sessions:
1. session_20251029_153000 - Phase 1 Week 1 [80% done] (45m ago)
2. session_20251029_100000 - Planning Phase 1 [100% done] (6h ago)
3. session_20251028_150000 - Agent system [100% done] (1d ago)
```

---

## 🎯 Common Patterns

### Pattern 1: Start New Phase

```python
# Orchestrator automatically:
1. log_agent_invocation(agent="orchestrator", reason="Start Phase 1")
2. log_tool_usage(tool="Task", subagent="project-manager")
3. log_decision(question="Which agent?", selected="config-architect")
4. take_snapshot(trigger="phase_start")
```

**You don't do anything** - it's automatic!

---

### Pattern 2: Complete Task

```python
# Orchestrator automatically:
1. log_validation(task="1.1", checks={...}, result="PASS")
2. log_tool_usage(tool="Task", subagent="project-manager", message="Mark complete")
3. take_snapshot(trigger="task_complete")
```

**You don't do anything** - it's automatic!

---

### Pattern 3: Error Recovery

```python
# When error occurs:
1. log_error(
     type="PerformanceBudgetExceeded",
     context={...},
     attempted_fix="Switch to orjson",
     fix_successful=True
   )
2. Analytics DB records pattern
3. Future similar errors → suggest known fix automatically
```

**You don't do anything** - it learns from errors!

---

## 📁 File Locations

```
.claude/
├── logs/                          # Activity logs (JSONL)
│   └── session_YYYYMMDD_HHMMSS.jsonl
├── state/                         # Snapshots (JSON)
│   └── session_YYYYMMDD_HHMMSS_snapNNN.json
├── handoffs/                      # Handoff summaries (Markdown)
│   └── session_YYYYMMDD_HHMMSS_handoff.md
├── analytics/                     # Analytics DB
│   └── agent_metrics.db
└── AGENT_TRACKING_SYSTEM.md       # Full documentation
```

---

## 🔍 Debugging

### "Why did it choose that agent?"

```bash
# Check decision log:
grep "decision" .claude/logs/session_YYYYMMDD_HHMMSS.jsonl
```

**Output**:
```json
{
  "event_type": "decision",
  "decision": {
    "question": "Which agent for structured logging?",
    "selected": "config-architect",
    "rationale": "Infrastructure work matches expertise"
  }
}
```

---

### "What files did it modify?"

```bash
# Check file operations:
grep "file_operation" .claude/logs/session_YYYYMMDD_HHMMSS.jsonl
```

**Output**:
```json
{
  "event_type": "file_operation",
  "operation": {
    "type": "write",
    "file_path": "src/core/logger.py",
    "diff_summary": "Created structured logging system"
  }
}
```

---

### "How long did that take?"

```bash
# Check tool usage:
grep "tool_usage" .claude/logs/session_YYYYMMDD_HHMMSS.jsonl
```

**Output**:
```json
{
  "event_type": "tool_usage",
  "tool": {"name": "Task", "subagent_type": "config-architect"},
  "execution": {"duration_ms": 4200}
}
```

---

## 💡 Pro Tips

### Tip 1: Checkpoint Before Risky Changes

```
User: "Checkpoint progress before refactoring"
System: ✅ Snapshot snap_005 created
        → You can restore anytime: "Restore snap_005"
```

### Tip 2: Review Session Before Resuming

```
User: "Show me what happened last session"
System: [Loads handoff summary]
        - Completed: Tasks 1.1, 1.2, 1.3
        - In progress: Task 1.4 (50% done)
        - Next: Complete error handling in src/core/error_handler.py
```

### Tip 3: Learn From Past Sessions

```
User: "How long does Task 1.1 usually take?"
System: [Queries analytics DB]
        → Task 1.1 (Structured Logging)
          Average: 15 minutes
          Last 5 times: 12, 14, 16, 15, 13 minutes
          Agent: config-architect (100%)
```

---

## 🎯 Key Benefits

| Benefit | Traditional | With Tracking | Savings |
|---------|------------|---------------|---------|
| Status check | 50k tokens | 5k tokens | **90%** |
| Error recovery | 100k tokens | 10k tokens | **90%** |
| Session resume | 150k tokens | 8k tokens | **95%** |
| Debug "why?" | Impossible | Instant | **∞** |
| Learn from errors | Manual | Automatic | **100%** |

---

## 🚦 Implementation Status

| Component | Status | Priority |
|-----------|--------|----------|
| Activity Logger | 🟡 Designed | Must-Have |
| Snapshot Manager | 🟡 Designed | Must-Have |
| Handoff Summaries | 🟡 Designed | Must-Have |
| Analytics DB | 🟡 Designed | Should-Have |
| Recovery UI | 🟡 Designed | Should-Have |
| Session Browser | 🟡 Designed | Nice-to-Have |

**Next Step**: Implement Activity Logger + Snapshot Manager (Week 1 of Phase 1)

---

## 📚 Full Documentation

For complete details, see: [.claude/AGENT_TRACKING_SYSTEM.md](.claude/AGENT_TRACKING_SYSTEM.md)

---

## ❓ FAQ

**Q: Does tracking slow down agents?**
A: No! Async logging adds <50ms overhead per event. Snapshots are 500ms but only every 10 agents.

**Q: How much space do logs take?**
A: ~1-2 MB per hour-long session. Compressed snapshots ~500KB each.

**Q: Can I disable tracking?**
A: Yes, but not recommended. Tracking is your safety net for token limits and crashes.

**Q: What if I lose internet during session?**
A: All tracking is local. Works perfectly offline.

**Q: Can I export session data?**
A: Yes! Logs are JSON, snapshots are JSON, handoffs are Markdown. Easy to parse/export.

---

**Ready to implement?** This system will be built in Phase 1, Week 1 alongside structured logging.
