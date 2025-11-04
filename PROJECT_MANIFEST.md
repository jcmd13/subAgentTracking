# SubAgent Tracking System - Project Manifest

**Version**: 0.1.0 (MVP)
**Created**: 2025-10-29
**Status**: Active Development
**Purpose**: Universal tracking, observability, and recovery system for Claude Code agentic workflows

---

## Project Overview

### What This Is

SubAgent Tracking System is a comprehensive observability and recovery framework for any Claude Code project that uses multi-agent workflows. It provides:

1. **Complete Activity Logging** - Every agent action, tool usage, decision, and error
2. **State Snapshots** - Periodic checkpoints for instant recovery
3. **Historical Analytics** - Performance metrics, error patterns, optimization insights
4. **Cloud Backup** - Automatic Google Drive backup at session end
5. **Phase Review** - End-of-phase analysis with improvement recommendations

### What This Isn't

- ❌ Not a Claude Code replacement (it enhances Claude Code)
- ❌ Not project-specific (works with any Claude Code project)
- ❌ Not cloud-dependent (works offline, syncs when online)
- ❌ Not expensive (100% free for MVP, <$0.01/month mature)

---

## Design Principles

### Decision Matrix: Free > Lightweight > High Performance

All architectural decisions prioritize in this order:
1. **Free** - Use free tier services, no paid dependencies
2. **Lightweight** - Minimal setup, no heavy infrastructure
3. **High Performance** - Fast recovery, low overhead

### Core Values

1. **Local-First** - All data stored locally first, cloud is backup
2. **Append-Only** - Logs never modified, only appended (safety)
3. **Human-Readable** - JSON/JSONL for machine + Markdown for humans
4. **Zero-Config** - Works out of box, setup optional
5. **Graceful Degradation** - Works even if backup fails

---

## Architecture

### Three-Tier Storage

```
Local (Fast)
  ↓ Automatic backup at session end
Google Drive (Sync)
  ↓ Archive after phase review (mature phase)
AWS S3 Glacier (Archive)
```

### Three-Layer Tracking

```
Layer 1: Activity Log (every event)
Layer 2: State Snapshots (periodic checkpoints)
Layer 3: Analytics DB (aggregated metrics)
```

### Event-Driven Design

```
Agent Action
  ↓
Activity Logger (async write to JSONL)
  ↓
Analytics DB (async insert)
  ↓
Snapshot Manager (check if trigger met)
  ↓
Backup Manager (at session end)
```

---

## Technology Stack

### Core Technologies (MVP)

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Activity Logs** | JSONL (gzip) | Append-only, streamable, 90% compression |
| **Snapshots** | JSON (tar.gz) | Human-readable, easy restore, 80% compression |
| **Analytics** | SQLite | Zero-config, 100k+ ops/sec, single file |
| **Backup** | Google Drive API | 2TB free, reliable, version history |
| **Language** | Python 3.10+ | Native Claude Code integration |

### Advanced Technologies (Mature Phase)

| Component | Technology | When to Use |
|-----------|-----------|-------------|
| **Cloud Analytics** | MongoDB Atlas Free | SQLite >500MB or need cloud access |
| **Archive** | AWS S3 Glacier | Phases >2 back, long-term storage |

---

## File Structure

```
subAgentTracking/
├── .claude/                              # Tracking system core
│   ├── AGENT_TRACKING_SYSTEM.md         # Complete technical spec (7200 words)
│   ├── STORAGE_ARCHITECTURE.md          # Storage strategy (5000 words)
│   ├── TRACKING_QUICK_REFERENCE.md      # Quick lookup (1500 words)
│   ├── logs/                            # Activity logs (local only)
│   │   ├── session_current.jsonl
│   │   └── session_previous.jsonl
│   ├── state/                           # Snapshots (local only)
│   │   ├── session_current_snap001.json
│   │   └── ...
│   ├── analytics/                       # SQLite DB (cumulative)
│   │   └── agent_metrics.db
│   ├── handoffs/                        # Session summaries
│   │   └── session_YYYYMMDD_HHMMSS_handoff.md
│   └── credentials/                     # OAuth credentials (git-ignored)
│       ├── google_drive_credentials.json
│       └── google_drive_token.json
│
├── src/                                 # Python implementation
│   └── core/
│       ├── __init__.py
│       ├── activity_logger.py          # Event logging
│       ├── snapshot_manager.py         # State snapshots
│       ├── backup_manager.py           # Google Drive backup
│       ├── analytics_db.py             # SQLite analytics
│       ├── phase_review.py             # End-of-phase analysis
│       └── config.py                   # Configuration
│
├── docs/                                # Documentation
│   ├── SETUP_GUIDE.md                  # Step-by-step installation
│   ├── INTEGRATION_GUIDE.md            # Integrate with existing projects
│   ├── GOOGLE_DRIVE_SETUP.md           # OAuth setup walkthrough
│   ├── API_REFERENCE.md                # Python API docs
│   ├── BEST_PRACTICES.md               # Tips and patterns
│   └── MIGRATION_GUIDE.md              # SQLite → MongoDB migration
│
├── examples/                            # Usage examples
│   ├── basic_usage.py                  # Simple tracking
│   ├── custom_events.py                # Custom event types
│   ├── analytics_queries.py            # Example queries
│   └── phase_review_example.py         # End-of-phase review
│
├── tests/                               # Unit tests
│   ├── test_activity_logger.py
│   ├── test_snapshot_manager.py
│   ├── test_backup_manager.py
│   └── test_analytics_db.py
│
├── .gitignore                           # Ignore credentials, local logs
├── requirements.txt                     # Python dependencies
├── setup_google_drive.py               # One-time OAuth setup
├── PROJECT_MANIFEST.md                 # This file
└── README.md                           # Project overview
```

---

## Implementation Roadmap

### Phase 0: Foundation (Complete)
- [x] Architecture design
- [x] Documentation (AGENT_TRACKING_SYSTEM.md)
- [x] Storage strategy (STORAGE_ARCHITECTURE.md)
- [x] Quick reference (TRACKING_QUICK_REFERENCE.md)
- [x] Project structure

### Phase 1: Core Implementation (Current)
**Duration**: 1 week
**Status**: In Progress

#### Week 1: MVP Implementation
**Day 1-2: Activity Logger**
- [ ] Event schema validation
- [ ] Async JSONL writer
- [ ] Compression (gzip)
- [ ] Log rotation (current + previous)
- [ ] Unit tests

**Day 3-4: Snapshot Manager**
- [ ] Snapshot triggers (10 agents, 20k tokens, manual)
- [ ] State serialization (JSON)
- [ ] Snapshot diffing (only save changes)
- [ ] Compression (tar.gz)
- [ ] Recovery interface
- [ ] Unit tests

**Day 5: Analytics DB**
- [ ] SQLite schema (agent_performance, tool_usage, error_patterns)
- [ ] Event ingestion from activity logs
- [ ] Query interface
- [ ] Unit tests

**Day 6-7: Integration & Testing**
- [ ] End-to-end testing
- [ ] Documentation updates
- [ ] Example scripts
- [ ] Performance benchmarks

### Phase 2: Backup & Recovery (Next)
**Duration**: 1 week

**Day 1-2: Google Drive Backup**
- [ ] OAuth 2.0 setup script
- [ ] Async upload manager
- [ ] Compression before upload
- [ ] Verification (hash comparison)
- [ ] Retry logic
- [ ] Unit tests

**Day 3-4: Recovery System**
- [ ] Session resume from snapshot
- [ ] Handoff summary generation
- [ ] Session history browser
- [ ] Restore from Google Drive
- [ ] Unit tests

**Day 5: End-of-Phase Review**
- [ ] Download all phase sessions
- [ ] Analytics queries (performance, errors, bottlenecks)
- [ ] Insights report generation (Markdown)
- [ ] Improvement recommendations
- [ ] Unit tests

**Day 6-7: Documentation & Examples**
- [ ] SETUP_GUIDE.md
- [ ] INTEGRATION_GUIDE.md
- [ ] GOOGLE_DRIVE_SETUP.md
- [ ] Example scripts
- [ ] Video walkthrough

### Phase 3: Advanced Features (Future)
**Duration**: 2 weeks

**Week 1: Analytics Dashboard**
- [ ] MongoDB Atlas migration script
- [ ] Cloud analytics queries
- [ ] Performance metrics dashboard
- [ ] Error pattern visualization
- [ ] Agent comparison charts

**Week 2: Archive & Collaboration**
- [ ] AWS S3 archival script
- [ ] Multi-developer support
- [ ] Session sharing
- [ ] Web dashboard (optional)

---

## Storage Strategy

### Local Storage (Current + Previous Session Only)

**Retention Policy**:
- Keep current session files
- Keep previous session files (1 session back)
- Delete older sessions after Google Drive backup
- Keep SQLite DB indefinitely (cumulative)

**Max Size**: 20 MB at any time

**Files**:
```
.claude/logs/
  ├── session_current.jsonl         (~10 MB uncompressed)
  └── session_previous.jsonl        (~10 MB uncompressed)
.claude/state/
  ├── session_current_snap001.json  (~2 MB uncompressed)
  ├── session_current_snap002.json
  └── session_previous_snap001.json
.claude/analytics/
  └── agent_metrics.db              (~5-10 MB cumulative)
```

---

### Google Drive Backup (Current + Previous Phase)

**Structure**:
```
Google Drive/SubAgentTracking/
├── Phase_0_MVP/
│   ├── sessions/
│   │   ├── session_20251029_153000/
│   │   │   ├── activity.jsonl.gz       (compressed, ~1 MB)
│   │   │   ├── snapshots.tar.gz        (compressed, ~1 MB)
│   │   │   ├── handoff.md              (human-readable)
│   │   │   └── analytics_snapshot.db   (compressed, ~5 MB)
│   │   └── ...
│   ├── phase_insights.md              (generated after phase review)
│   └── phase_analytics.db             (end-of-phase snapshot)
└── Phase_1_Foundation/
    └── ...
```

**Backup Trigger**: Automatic when `handoff.md` created (session end)

**Retention**: Keep current + previous phase (delete older after archive to S3)

**Size per Phase**: ~200 MB compressed

---

### AWS S3 Archive (Completed Phases >2 Back)

**Storage Class**: Glacier Deep Archive

**Cost**: $0.001/GB/month

**Retention**: Forever

**Archive Trigger**: Manual at end-of-phase review

**Size per Phase**: ~200 MB compressed

**Status**: Mature phase only (not MVP)

---

## Event Schema

### 7 Event Types

1. **agent_invocation** - Agent started/completed
2. **tool_usage** - Tool used (Read, Edit, Bash, etc.)
3. **file_operation** - File created/modified/deleted
4. **decision** - Agent decision with rationale
5. **error** - Error encountered with fix attempts
6. **context_snapshot** - Token usage, state checkpoint
7. **validation** - Validation check result

### Example Event (agent_invocation)

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

See [AGENT_TRACKING_SYSTEM.md](.claude/AGENT_TRACKING_SYSTEM.md) for all 7 schemas.

---

## Analytics Queries

### Agent Performance

```sql
SELECT
  agent_name,
  COUNT(*) as tasks,
  AVG(duration_ms) as avg_duration_ms,
  AVG(tokens_consumed) as avg_tokens,
  SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate
FROM agent_performance
WHERE session_date >= DATE('now', '-30 days')
GROUP BY agent_name
ORDER BY success_rate DESC;
```

### Tool Effectiveness

```sql
SELECT
  tool_name,
  COUNT(*) as usage_count,
  AVG(duration_ms) as avg_duration_ms,
  SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as success_rate,
  COUNT(CASE WHEN error_type IS NOT NULL THEN 1 END) as error_count
FROM tool_usage
WHERE session_date >= DATE('now', '-30 days')
GROUP BY tool_name
ORDER BY usage_count DESC;
```

### Error Patterns

```sql
SELECT
  error_type,
  COUNT(*) as frequency,
  AVG(resolution_time_ms) as avg_resolution_ms,
  SUM(CASE WHEN fix_successful = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as fix_success_rate,
  GROUP_CONCAT(DISTINCT file_path) as affected_files
FROM error_patterns
WHERE session_date >= DATE('now', '-30 days')
GROUP BY error_type
ORDER BY frequency DESC
LIMIT 10;
```

---

## Capacity Planning

### MVP (4 Phases, 6 Months, 1 Developer)

| Storage Tier | Size | Cost |
|--------------|------|------|
| Local (max 2 sessions) | 20 MB | $0 |
| Google Drive (2 phases) | 400 MB | $0 |
| **Total** | **420 MB** | **$0/month** |

### Mature (10 Phases, 1 Year, 10 Developers)

| Storage Tier | Size | Cost |
|--------------|------|------|
| Local (max 2 sessions) | 20 MB | $0 |
| Google Drive (2 phases) | 500 MB | $0 |
| MongoDB Atlas | 512 MB | $0 |
| AWS S3 Glacier (8 phases) | 1.6 GB | $0.0016/month |
| **Total** | **~2.5 GB** | **<$0.01/month** |

---

## Integration Guide

### Adding to Existing Project

```bash
# 1. Copy tracking system to your project
cp -r subAgentTracking/.claude your-project/
cp -r subAgentTracking/src/core your-project/src/

# 2. Install dependencies
pip install -r subAgentTracking/requirements.txt

# 3. Set up Google Drive API (one-time, 10 min)
python subAgentTracking/setup_google_drive.py

# 4. Import in your agents
from src.core.activity_logger import log_agent_invocation, log_tool_usage
from src.core.snapshot_manager import take_snapshot

# 5. Log events
log_agent_invocation(agent="my_agent", invoked_by="orchestrator", reason="Task 1.1")

# 6. Done! Tracking starts automatically
```

### Minimal Integration (Just Logging)

```python
# In your orchestrator agent:
from src.core.activity_logger import log_agent_invocation

# Before invoking subagent
log_agent_invocation(
    agent="config-architect",
    invoked_by="orchestrator",
    reason="Implement structured logging (Task 1.1)"
)

# That's it! Logs, snapshots, backups all automatic
```

---

## Security & Privacy

### Credentials (Never Committed)

All credential files in `.gitignore`:
- `.claude/credentials/google_drive_credentials.json`
- `.claude/credentials/google_drive_token.json`
- `.env` files

### Sensitive Data in Logs

**Automatic filtering** for sensitive patterns:
- API keys (e.g., `sk-...`)
- Passwords (e.g., `password=...`)
- Tokens (e.g., `Bearer ...`)
- Email addresses (optional)

**Manual filtering**:
```python
log_event(
    event_type="tool_usage",
    tool="API_call",
    parameters={"api_key": "[REDACTED]"}  # Manual redaction
)
```

### Google Drive Access

**OAuth 2.0 scopes** (requested):
- `https://www.googleapis.com/auth/drive.file` (only files created by app)
- NOT `drive` (no access to other files)

**User control**:
- Revoke access anytime: [Google Account Permissions](https://myaccount.google.com/permissions)
- Delete all data: Delete `SubAgentTracking/` folder in Google Drive

---

## Performance

### Overhead

| Operation | Latency Added | Frequency |
|-----------|--------------|-----------|
| Log event | <1ms | Every agent action |
| Snapshot | 50ms | Every 10 agents or 20k tokens |
| Backup | 1-2 min (async) | End of session (non-blocking) |

**Total overhead**: ~5-8% of session time (well worth recovery benefits)

### Recovery Speed

| Operation | Time | Token Cost |
|-----------|------|------------|
| Load snapshot | <1s | 5k tokens |
| Restore from Google Drive | 30s | 8k tokens (handoff + snapshot) |
| Full session replay | Variable | (avoided by snapshots) |

**Savings vs rebuilding context**: 85-90% token reduction

---

## Testing Strategy

### Unit Tests (pytest)

- `test_activity_logger.py` - Event logging
- `test_snapshot_manager.py` - State snapshots
- `test_backup_manager.py` - Google Drive upload
- `test_analytics_db.py` - SQLite queries

### Integration Tests

- End-to-end session logging
- Snapshot → recovery workflow
- Backup → restore workflow
- Phase review analysis

### Performance Tests

- Event logging throughput (target: 1000/sec)
- Snapshot speed (target: <100ms)
- SQLite query speed (target: <10ms)
- Backup upload speed (target: <5 min for typical session)

---

## Release Plan

### v0.1.0 (MVP) - Current
- Core activity logging
- State snapshots
- SQLite analytics
- Documentation

**Release Date**: Week 1 of Phase 1

### v0.2.0 - Backup & Recovery
- Google Drive backup
- Session resume
- End-of-phase review

**Release Date**: Week 2 of Phase 1

### v0.3.0 - Advanced Analytics
- MongoDB Atlas integration
- Performance dashboard
- Error pattern analysis

**Release Date**: Week 3 of Phase 1

### v1.0.0 - Production Ready
- AWS S3 archival
- Multi-developer support
- Web dashboard
- Full documentation

**Release Date**: End of Phase 1

---

## Success Metrics

### Technical Metrics

- ✅ Event logging overhead: <1ms average
- ✅ Snapshot creation: <100ms average
- ✅ Recovery speed: <1s from snapshot
- ✅ Token savings: >85% on recovery operations
- ✅ Backup reliability: >99.9% success rate

### User Metrics

- ✅ Setup time: <15 minutes (including Google Drive OAuth)
- ✅ Recovery success: 100% (never lose work)
- ✅ User satisfaction: >4.5/5 stars
- ✅ Adoption: Used in >50% of Claude Code projects

---

## Known Limitations (MVP)

1. **No MongoDB support** - SQLite only (mature phase feature)
2. **No AWS S3 archive** - Google Drive only (mature phase feature)
3. **No web dashboard** - Command-line only (mature phase feature)
4. **Manual phase review** - No automated triggers (v0.2.0)
5. **Single developer** - No collaboration features (v1.0.0)

---

## Future Enhancements

### Post-v1.0.0

1. **Real-time collaboration** - Multiple developers, shared sessions
2. **Web dashboard** - Browser-based analytics and session browser
3. **AI-powered insights** - LLM analysis of error patterns
4. **Integration with CI/CD** - Automatic tracking in pipelines
5. **Slack/Discord notifications** - Phase completion alerts
6. **Cost optimization** - Automatic detection of expensive operations
7. **Compliance features** - Audit trails for SOC2/HIPAA

---

## Contact & Support

### Documentation
- **Complete spec**: [AGENT_TRACKING_SYSTEM.md](.claude/AGENT_TRACKING_SYSTEM.md)
- **Storage strategy**: [STORAGE_ARCHITECTURE.md](.claude/STORAGE_ARCHITECTURE.md)
- **Quick reference**: [TRACKING_QUICK_REFERENCE.md](.claude/TRACKING_QUICK_REFERENCE.md)

### Community
- **GitHub Issues**: Report bugs, request features
- **GitHub Discussions**: Ask questions, share ideas
- **Email**: (to be added)

---

## License

MIT License - Use anywhere, modify freely, no restrictions.

See [LICENSE](LICENSE) for full text.

---

## Acknowledgments

**Inspired by**:
- Git (version control for code)
- Time Machine (macOS backup system)
- DataDog/New Relic (observability platforms)
- Sentry (error tracking)

**Built with**:
- Claude Code (Anthropic)
- Google Drive API
- SQLite
- MongoDB Atlas (future)
- AWS S3 (future)

---

**Project Lead**: John ([@yourusername](https://github.com/yourusername))
**Status**: Active Development
**Version**: 0.1.0 (MVP)
**Last Updated**: 2025-10-29
