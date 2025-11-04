# Storage Architecture & Backup Strategy

**Purpose**: Define storage, backup, and archival strategy for agent tracking system

**Last Updated**: 2025-10-29
**Decision Matrix**: Free > Lightweight > High Performance

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Storage Layers](#storage-layers)
3. [Backup Strategy](#backup-strategy)
4. [End-of-Phase Review](#end-of-phase-review)
5. [Technology Stack](#technology-stack)
6. [Capacity Planning](#capacity-planning)
7. [Setup Instructions](#setup-instructions)

---

## Architecture Overview

### Three-Tier Storage System

```
┌─────────────────────────────────────────────────────────┐
│               Tier 1: Local Storage (Fast)              │
│  • Activity logs (current + previous session)           │
│  • Snapshots (current + previous session)               │
│  • SQLite analytics DB (cumulative)                     │
│  • Retention: 2 sessions max (~20 MB)                   │
└─────────────────────────────────────────────────────────┘
                            ↓ (Backup at session end)
┌─────────────────────────────────────────────────────────┐
│            Tier 2: Google Drive Backup (Sync)           │
│  • All sessions for current phase                       │
│  • All sessions for previous phase                      │
│  • Phase insights & analytics                           │
│  • Retention: 2 phases max (~500 MB)                    │
└─────────────────────────────────────────────────────────┘
                            ↓ (Archive after phase review)
┌─────────────────────────────────────────────────────────┐
│          Tier 3: AWS S3 Archive (Long-Term)             │
│  • Completed phases (>2 phases old)                     │
│  • Glacier Deep Archive storage                         │
│  • Retention: Forever ($0.001/GB/month)                 │
│  • Status: Mature phase only (not MVP)                  │
└─────────────────────────────────────────────────────────┘
```

---

## Storage Layers

### Layer 1: Local Storage (Development Machine)

**Purpose**: High-performance local storage for active development

**Location**: `.claude/` directory in project root

**Structure**:
```
.claude/
├── logs/
│   ├── session_current.jsonl          # Active session (append-only)
│   └── session_previous.jsonl         # Previous session (backup)
├── state/
│   ├── session_current_snap001.json   # Current session snapshots
│   ├── session_current_snap002.json
│   └── session_previous_snap001.json  # Previous session snapshots
├── analytics/
│   └── agent_metrics.db               # SQLite (cumulative, all sessions)
├── handoffs/
│   └── session_YYYYMMDD_HHMMSS_handoff.md  # Session handoff summary
└── credentials/
    ├── google_drive_credentials.json  # OAuth credentials (git-ignored)
    └── google_drive_token.json        # Access token (git-ignored)
```

**Retention Policy**:
- ✅ Keep current session files
- ✅ Keep previous session files (1 session back)
- ✅ Delete older sessions after successful backup
- ✅ Keep SQLite DB indefinitely (cumulative analytics)

**Storage Size**: 10-20 MB max at any time

**Performance**:
- Activity log writes: <1ms (append-only)
- Snapshot writes: <50ms (compressed JSON)
- SQLite queries: <1ms (indexed)
- Recovery: <1s (load snapshot)

---

### Layer 2: Google Drive Backup (Cloud Sync)

**Purpose**: Reliable cloud backup with version history

**Location**: `Google Drive/SubAgentTracking/`

**Structure**:
```
Google Drive/SubAgentTracking/
├── Phase_0_MVP/
│   ├── sessions/
│   │   ├── session_20251029_153000/
│   │   │   ├── activity.jsonl.gz          # Compressed activity log
│   │   │   ├── snapshots.tar.gz           # All snapshots compressed
│   │   │   ├── handoff.md                 # Human-readable summary
│   │   │   └── analytics_snapshot.db      # SQLite snapshot for session
│   │   ├── session_20251029_180000/
│   │   │   └── ...
│   │   └── session_20251030_100000/
│   │       └── ...
│   ├── phase_insights.md                  # Generated after phase review
│   ├── phase_analytics.db                 # End-of-phase DB snapshot
│   └── phase_metadata.json                # Phase stats & completion date
│
├── Phase_1_Foundation/
│   ├── sessions/
│   │   └── ...
│   ├── phase_insights.md
│   └── phase_analytics.db
│
├── Phase_2_Plugins/
│   └── ...
│
└── current_phase.json                     # Tracks which phase is active
```

**Retention Policy**:
- ✅ Keep all sessions for current phase
- ✅ Keep all sessions for previous phase (reference)
- ✅ Archive older phases to AWS S3 (mature phase only)
- ✅ Keep phase insights forever

**Backup Triggers**:
- Automatic at end of each session (when handoff.md created)
- Manual: User says "Backup session now"

**Upload Process**:
1. Compress session files (gzip for JSONL, tar.gz for snapshots)
2. Upload to Google Drive via API (async, non-blocking)
3. Verify upload (check file hashes)
4. Delete local previous session files
5. Log backup status to analytics DB

**Storage Size**: ~100-200 MB per phase (well within 2TB limit)

**Performance**:
- Upload time: 1-2 minutes (async, doesn't block work)
- Download/restore: <30 seconds for full session
- Works offline: Queues uploads, syncs when online

---

### Layer 3: AWS S3 Archive (Long-Term Storage)

**Purpose**: Cost-effective long-term archive for completed phases

**Location**: `s3://subagent-tracking-archive/`

**Structure**:
```
s3://subagent-tracking-archive/
├── Phase_0_MVP.tar.gz                     # Entire phase compressed
├── Phase_1_Foundation.tar.gz
├── Phase_2_Plugins.tar.gz
└── metadata/
    ├── Phase_0_MVP_manifest.json          # File listing & checksums
    ├── Phase_1_Foundation_manifest.json
    └── ...
```

**Retention Policy**:
- ✅ Archive phases older than 2 phases back
- ✅ Use S3 Glacier Deep Archive storage class
- ✅ Keep forever (cost: $0.001/GB/month)

**Archive Triggers**:
- Manual: At end-of-phase review
- Condition: Only phases >2 back from current

**Archive Process**:
1. Download entire phase from Google Drive
2. Compress to single tar.gz file
3. Generate manifest (file listing, checksums, metadata)
4. Upload to S3 Glacier Deep Archive
5. Verify upload
6. Delete from Google Drive (keep insights only)

**Storage Size**: ~500 MB per phase compressed

**Cost**: $0.0005/month per phase (~$0.01/year for 20 phases)

**Status**: **Mature phase only** (not implemented in MVP)

---

## Backup Strategy

### Automatic Session Backup

**Trigger**: When `session_XXX_handoff.md` is created (session end)

**Process**:
```python
def backup_session(session_id):
    """
    Automatic backup to Google Drive at end of session
    """
    # 1. Compress session files
    compress_activity_log(f"session_{session_id}.jsonl")
    compress_snapshots(session_id)

    # 2. Prepare files for upload
    files_to_upload = [
        f"activity.jsonl.gz",
        f"snapshots.tar.gz",
        f"handoff.md",
        f"analytics_snapshot.db"
    ]

    # 3. Upload to Google Drive (async)
    phase = get_current_phase()  # From PROJECT_STATUS.md
    target_folder = f"SubAgentTracking/Phase_{phase}/sessions/session_{session_id}/"

    upload_to_google_drive(
        files=files_to_upload,
        target_folder=target_folder,
        async_mode=True  # Non-blocking
    )

    # 4. Verify upload
    if verify_backup_success(session_id):
        # 5. Clean up local storage
        delete_previous_session_files()

        # 6. Log backup status
        log_backup_event(
            session_id=session_id,
            status="success",
            uploaded_size=get_upload_size(files_to_upload),
            google_drive_path=target_folder
        )
    else:
        # Retry or alert user
        log_backup_event(session_id=session_id, status="failed")
```

**Compression Ratios**:
- JSONL (activity logs): ~90% compression (10MB → 1MB)
- JSON (snapshots): ~80% compression (5MB → 1MB)
- SQLite: ~50% compression (10MB → 5MB)

**Upload Time**: 1-2 minutes for typical session (~8MB compressed)

**Verification**: MD5 hash comparison (local vs uploaded)

---

### Manual Backup Commands

```bash
# Backup current session immediately
User: "Backup session now"
→ Triggers backup_session() even if session ongoing

# Backup specific session
User: "Backup session_20251029_153000"
→ Uploads specific session to Google Drive

# Verify backups
User: "Verify backups"
→ Lists all sessions in Google Drive, shows missing backups

# Restore session
User: "Restore session_20251029_153000"
→ Downloads from Google Drive, extracts to local storage
```

---

## End-of-Phase Review

### Automatic Analysis Workflow

**Trigger**: User says "End Phase N" or "Start phase review"

**Process**:
```python
def end_of_phase_review(phase_number):
    """
    Analyze all sessions from completed phase, generate insights
    """
    # 1. Download all phase sessions from Google Drive
    sessions = download_phase_sessions(phase_number)

    # 2. Load all activity logs into memory
    all_events = []
    for session in sessions:
        events = load_jsonl(f"{session}/activity.jsonl.gz")
        all_events.extend(events)

    # 3. Run analytics queries
    insights = {
        "performance": analyze_performance(all_events),
        "errors": analyze_errors(all_events),
        "bottlenecks": identify_bottlenecks(all_events),
        "tool_usage": analyze_tool_effectiveness(all_events),
        "agent_performance": analyze_agent_performance(all_events),
        "cost": analyze_token_costs(all_events),
        "refinements": generate_recommendations(all_events)
    }

    # 4. Generate phase_insights.md
    generate_insights_report(phase_number, insights)

    # 5. Snapshot SQLite DB for phase
    snapshot_analytics_db(phase_number)

    # 6. Upload to Google Drive
    upload_phase_artifacts(phase_number, [
        "phase_insights.md",
        "phase_analytics.db",
        "phase_metadata.json"
    ])

    # 7. Optional: Archive to S3 (mature phase only)
    if should_archive_to_s3(phase_number):
        archive_phase_to_s3(phase_number)
        cleanup_google_drive(phase_number)

    # 8. Return insights for user review
    return insights
```

---

### Phase Insights Report Format

**File**: `phase_insights.md`

**Structure**:
```markdown
# Phase N Review - [Phase Name]

**Phase Duration**: YYYY-MM-DD to YYYY-MM-DD (X days)
**Total Sessions**: 25
**Total Development Time**: 40 hours
**Overall Success**: ✅ Phase completed on schedule

---

## Executive Summary

[3-5 sentence summary of what was accomplished]

---

## Performance Metrics

### Latency Analysis
- **Average task latency**: 3.2s (target: <4s) ✅
- **P95 latency**: 3.8s ✅
- **P99 latency**: 5.2s ⚠️ (above target)

### Token Efficiency
- **Total tokens consumed**: 1.2M
- **Average tokens/task**: 2400
- **Token budget adherence**: 95% of tasks under budget ✅

### Agent Performance
| Agent | Tasks | Avg Duration | Success Rate | Token Efficiency |
|-------|-------|--------------|--------------|------------------|
| config-architect | 15 | 4.2 min | 93% | 3200 tokens/task |
| refactor-agent | 12 | 6.5 min | 89% | 4500 tokens/task |
| test-engineer | 8 | 3.1 min | 95% | 2100 tokens/task |

---

## Error Analysis

### Top 10 Errors
1. **PerformanceBudgetExceeded** (12 occurrences)
   - Files: src/core/logger.py (5), src/llm/analyzer.py (7)
   - Fix success rate: 92%
   - Common fix: Switch to faster libraries (orjson, msgpack)
   - Recommendation: Update agent prompts to prefer fast libraries

2. **TestCoverageBelowThreshold** (8 occurrences)
   - Fix success rate: 100%
   - Common fix: Add unit tests
   - Recommendation: Remind agents of 80% coverage requirement

[... more errors ...]

---

## Bottleneck Analysis

### Slowest 20% of Operations
1. **LLM answer generation** (avg: 3.5s, p95: 6.2s)
   - Opportunity: Try faster Ollama model (gemma2 vs llama3.1)
   - Potential savings: 1-2s per answer

2. **Whisper transcription** (avg: 450ms, p95: 850ms)
   - Opportunity: GPU acceleration (currently CPU-only)
   - Potential savings: 300ms per transcription

[... more bottlenecks ...]

---

## Tool Usage Effectiveness

| Tool | Usage Count | Avg Duration | Success Rate | Notes |
|------|-------------|--------------|--------------|-------|
| Edit | 120 | 150ms | 98% | Very reliable |
| Read | 200 | 80ms | 99% | Fast and accurate |
| Bash | 45 | 1200ms | 91% | Some blocked by validation |
| Grep | 80 | 900ms | 95% | Consider Glob first for speed |

**Recommendation**: Use Glob before Grep for 40% speed improvement

---

## Cost Analysis

### Token Costs
- **Total tokens**: 1.2M
- **Cost (if using Claude API)**: $9.60 (at $8/M tokens)
- **Cost (using Ollama local)**: $0.00 ✅

### Compute Costs
- **Local development**: $0.00
- **Google Drive storage**: $0.00 (within 2TB limit)
- **Total cost**: $0.00 ✅

---

## Refinement Opportunities

### Agent Prompt Improvements
1. **config-architect**: Add reminder to use fast libraries (orjson, msgpack)
2. **refactor-agent**: Emphasize backward compatibility via feature flags
3. **test-engineer**: Default to 85% coverage (5% buffer above 80% min)

### Workflow Optimizations
1. **Component extraction**: Use parallel file reads (40% faster)
2. **Validation**: Cache validation results (avoid re-checking)
3. **Context management**: Use snapshots more aggressively (every 5 agents)

### Tool Selection Changes
1. **File search**: Prefer Glob → Grep workflow (faster)
2. **Performance measurement**: Add timing to all critical paths
3. **Error handling**: Add retry logic for transient failures

---

## Recommendations for Next Phase

### Performance Targets
- [ ] Reduce p99 latency to <4s (currently 5.2s)
- [ ] Improve token efficiency by 10% (2400 → 2160 tokens/task)
- [ ] Increase agent success rate to 95%+ (currently 92%)

### Process Improvements
- [ ] Add pre-flight checks before major refactors
- [ ] Implement parallel agent execution (where safe)
- [ ] Add more granular validation checkpoints

### Technical Debt
- [ ] Refactor src/llm/analyzer.py (5 performance issues)
- [ ] Add GPU acceleration for Whisper (300ms savings)
- [ ] Implement caching for term definitions

---

## Success Metrics

✅ **Completed**: 28/28 tasks (100%)
✅ **On Schedule**: Yes (4 weeks planned, 4 weeks actual)
✅ **Performance**: 95% of tasks met latency budget
✅ **Quality**: 92% validation pass rate
✅ **Cost**: $0 (all free tier services)

**Overall Assessment**: Successful phase, ready to proceed to Phase N+1

---

**Next Phase**: Phase N+1 - [Next Phase Name]
**Start Date**: YYYY-MM-DD
**Expected Duration**: X weeks
```

---

## Technology Stack

### MVP Phase (Now - 6 Months)

#### Local Storage
```python
# Activity Logs
Format: JSONL (JSON Lines)
Compression: gzip (90% reduction)
Library: built-in (json + gzip)

# Snapshots
Format: JSON
Compression: tar.gz (80% reduction)
Library: built-in (json + tarfile)

# Analytics Database
Database: SQLite
File: agent_metrics.db
Library: sqlite3 (built-in)
Size: ~5-10 MB per month
Performance: 100k+ inserts/sec, <1ms queries
```

#### Cloud Backup
```python
# Google Drive API
Library: google-api-python-client
Authentication: OAuth 2.0
Storage: 2TB free (Google Workspace)
Upload: Async, non-blocking
Versioning: Automatic (Google Drive native)

# Installation
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

#### Analytics
```python
# SQL Queries on SQLite
Libraries: sqlite3, pandas (for data analysis)
Visualization: matplotlib (for charts in insights)

# Installation
pip install pandas matplotlib
```

---

### Mature Phase (Post-MVP, 6+ Months)

#### Cloud Analytics Database
```python
# MongoDB Atlas Free Tier
Storage: 512 MB free
Use case: Real-time analytics, cross-session queries
Library: pymongo
Performance: Excellent for time-series data

# Installation
pip install pymongo
```

#### Long-Term Archive
```python
# AWS S3 Glacier Deep Archive
Storage class: GLACIER_DEEP_ARCHIVE
Cost: $0.00099/GB/month
Use case: Phases older than 2 back
Library: boto3

# Installation
pip install boto3
```

#### Migration Path
```python
# SQLite → MongoDB Migration
1. Export SQLite to CSV/JSON:
   sqlite3 agent_metrics.db ".mode csv" ".output data.csv" "SELECT * FROM agent_performance"

2. Import to MongoDB:
   mongoimport --uri "mongodb+srv://..." --collection agent_performance --file data.csv --type csv --headerline

3. Update queries to use pymongo
   Total time: ~2 hours
```

---

## Capacity Planning

### Storage Projections

#### MVP Phase (4 Phases, 6 Months)

| Component | Per Session | Sessions/Phase | Phase Total | 4 Phases |
|-----------|-------------|----------------|-------------|----------|
| Activity Log (raw) | 20 MB | 20 | 400 MB | 1.6 GB |
| Activity Log (compressed) | 2 MB | 20 | 40 MB | 160 MB |
| Snapshots (raw) | 10 MB | 20 | 200 MB | 800 MB |
| Snapshots (compressed) | 2 MB | 20 | 40 MB | 160 MB |
| Handoff Summary | 50 KB | 20 | 1 MB | 4 MB |
| SQLite Snapshot | 5 MB | 20 | 100 MB | 400 MB |
| **Total (compressed)** | ~9 MB | | **181 MB** | **724 MB** |

**Local Storage**: ~20 MB at any time (2 sessions max)
**Google Drive**: ~724 MB for entire MVP (0.036% of 2TB)

---

#### Mature Phase (10 Developers, 1 Year)

| Component | Size | Location | Cost |
|-----------|------|----------|------|
| Active sessions (2 phases) | 500 MB | Google Drive | $0/mo |
| MongoDB Atlas (analytics) | 512 MB | Cloud | $0/mo |
| S3 Archive (10 phases) | 5 GB | AWS Glacier | $0.005/mo |
| **Total** | ~6 GB | | **<$0.01/mo** |

---

### Bandwidth Requirements

#### Per Session Backup
- Upload size: ~8 MB compressed
- Upload time: 1-2 minutes (typical home internet)
- Frequency: 1 per session (typically 1-2 sessions per day)
- Daily bandwidth: ~16 MB upload (negligible)

#### End-of-Phase Review
- Download size: ~180 MB per phase (all sessions)
- Download time: <1 minute (typical home internet)
- Frequency: Once every 4-6 weeks
- Impact: Minimal

---

## Setup Instructions

### Google Drive API Setup (One-Time, ~10 Minutes)

#### Step 1: Enable Google Drive API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create new project: "SubAgentTracking"
3. Enable Google Drive API:
   - Navigate to "APIs & Services" → "Library"
   - Search "Google Drive API"
   - Click "Enable"

#### Step 2: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth 2.0 Client ID"
3. Application type: "Desktop app"
4. Name: "SubAgentTracking Local"
5. Download credentials JSON

#### Step 3: Save Credentials

```bash
# Create credentials directory
mkdir -p .claude/credentials

# Save downloaded file as:
mv ~/Downloads/credentials.json .claude/credentials/google_drive_credentials.json

# Add to .gitignore (if not already)
echo ".claude/credentials/" >> .gitignore
echo ".claude/credentials/*.json" >> .gitignore
```

#### Step 4: First-Time Authorization

```bash
# Run authorization script
python src/core/backup_manager.py --auth

# This will:
# 1. Open browser for Google account authorization
# 2. User approves access to Google Drive
# 3. Saves token to .claude/credentials/google_drive_token.json
# 4. Future backups use this token (no browser needed)
```

#### Step 5: Verify Setup

```bash
# Test backup
python src/core/backup_manager.py --test

# Expected output:
# ✅ Google Drive API connected
# ✅ Created test folder: SubAgentTracking/
# ✅ Uploaded test file
# ✅ Verified upload
# ✅ Cleanup successful
#
# Setup complete! Automatic backups enabled.
```

---

### SQLite Setup (Zero Configuration)

SQLite is included with Python, no setup needed!

```python
# First run automatically creates database
import sqlite3
conn = sqlite3.connect('.claude/analytics/agent_metrics.db')

# Schema created on first use (see src/core/analytics_db.py)
```

---

### MongoDB Atlas Setup (Mature Phase Only)

#### Step 1: Create Free Cluster

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas/register)
2. Sign up with Google account (free tier)
3. Create cluster: "SubAgentTracking" (M0 Free Tier, 512MB)

#### Step 2: Configure Access

1. Database Access:
   - Username: `subagent_admin`
   - Password: (generate strong password)
   - Role: "Atlas Admin"

2. Network Access:
   - Add IP: "0.0.0.0/0" (allow from anywhere)
   - Or: Add current IP only (more secure)

#### Step 3: Get Connection String

```python
# Connection string format:
mongodb+srv://subagent_admin:<password>@subagenttracking.xxxxx.mongodb.net/

# Save to .env file (git-ignored)
MONGODB_URI=mongodb+srv://subagent_admin:PASSWORD@subagenttracking.xxxxx.mongodb.net/
```

#### Step 4: Migrate from SQLite

```bash
# Run migration script
python src/core/migrate_to_mongodb.py

# This will:
# 1. Export all tables from SQLite to JSON
# 2. Upload to MongoDB Atlas
# 3. Verify data integrity
# 4. Keep SQLite as backup
```

---

### AWS S3 Setup (Mature Phase Only)

#### Step 1: Create S3 Bucket

1. Go to [AWS Console](https://console.aws.amazon.com/s3/)
2. Create bucket: "subagent-tracking-archive"
3. Region: us-east-1 (cheapest)
4. Block public access: Enabled
5. Versioning: Disabled (not needed)

#### Step 2: Configure Lifecycle Policy

```json
{
  "Rules": [{
    "Id": "ArchiveToGlacierDeepArchive",
    "Status": "Enabled",
    "Transitions": [{
      "Days": 0,
      "StorageClass": "DEEP_ARCHIVE"
    }]
  }]
}
```

#### Step 3: Create IAM User

1. IAM Console → Users → Add User
2. Username: "subagent-uploader"
3. Access type: Programmatic access
4. Permissions: S3 PutObject, GetObject
5. Save credentials (Access Key ID + Secret)

#### Step 4: Configure AWS CLI

```bash
# Install AWS CLI
pip install boto3

# Save credentials to .env
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AWS_REGION=us-east-1
S3_ARCHIVE_BUCKET=subagent-tracking-archive
```

---

## Migration Path

### SQLite → MongoDB (When to Migrate)

**Trigger Points**:
- ✅ SQLite DB exceeds 500 MB (~6-12 months of data)
- ✅ Need cross-session analytics from multiple developers
- ✅ Want cloud-accessible analytics dashboard
- ✅ Planning to build web UI for insights

**Migration Process**: ~2 hours (one-time)

**Benefits After Migration**:
- ✅ Cloud-accessible (query from anywhere)
- ✅ Better time-series queries
- ✅ JSON-native (matches log format)
- ✅ Still free (512 MB limit)

**SQLite Advantages (Why Start Here)**:
- ✅ Zero setup
- ✅ Single file (easy to backup)
- ✅ Excellent performance (local)
- ✅ No network dependency

---

## Best Practices

### Backup Hygiene

1. **Never delete local session** until backup verified
2. **Check backup status** after each session (automatic log entry)
3. **Verify monthly** that all sessions backed up
4. **Test restore** quarterly to ensure backups work

### Storage Optimization

1. **Compress before upload** (90% smaller)
2. **Delete previous session** only after new session backed up
3. **Archive old phases** to S3 (mature phase)
4. **Keep SQLite DB** indefinitely (small, cumulative)

### Security

1. **Never commit credentials** to git (.gitignore)
2. **Use OAuth tokens** for Google Drive (auto-refresh)
3. **Encrypt sensitive data** in logs (API keys, passwords)
4. **Limit network access** to MongoDB (IP whitelist)

---

## Summary

### MVP Phase (Now)

| Component | Technology | Cost | Setup Time |
|-----------|-----------|------|------------|
| Local logs | JSONL (gzip) | $0 | 0 min |
| Local snapshots | JSON (tar.gz) | $0 | 0 min |
| Analytics DB | SQLite | $0 | 0 min |
| Backup | Google Drive API | $0 | 10 min |
| **Total** | | **$0/mo** | **10 min** |

**Storage**: <1 GB for entire MVP
**Performance**: Excellent (all local)
**Reliability**: High (Google Drive versioning)

---

### Mature Phase (6+ Months)

| Component | Technology | Cost | Migration Time |
|-----------|-----------|------|----------------|
| Analytics DB | MongoDB Atlas | $0 | 2 hours |
| Archive | AWS S3 Glacier | <$0.01/mo | 1 hour |
| **Total** | | **<$0.01/mo** | **3 hours** |

**Storage**: Unlimited (practical)
**Performance**: Excellent
**Reliability**: Enterprise-grade

---

## Next Steps

1. ✅ Review this architecture
2. ⏳ Set up Google Drive API (10 minutes)
3. ⏳ Implement backup_manager.py
4. ⏳ Test automatic backup
5. ⏳ Integrate with agent system

**Ready to implement?** See [AGENT_TRACKING_SYSTEM.md](AGENT_TRACKING_SYSTEM.md) for implementation guide.
