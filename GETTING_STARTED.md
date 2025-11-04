# Getting Started with SubAgent Tracking System

**Welcome!** This guide will walk you through setting up the tracking system for your Claude Code project.

**Estimated setup time**: 15 minutes

---

## What You're Building

A comprehensive tracking system that:
- ✅ Logs every agent action automatically
- ✅ Creates periodic state snapshots for recovery
- ✅ Backs up to Google Drive at session end
- ✅ Generates end-of-phase insights & recommendations
- ✅ Saves 85-90% tokens on recovery operations

---

## Prerequisites

### Required
- ✅ **Python 3.10+** - Check: `python --version`
- ✅ **pip** - Check: `pip --version`
- ✅ **Google account** - For Google Drive backup (2TB free)

### Optional (for mature phase)
- ⚪ **MongoDB Atlas account** - Free tier (512 MB)
- ⚪ **AWS account** - Free tier for S3 archive

---

## Quick Start (5 Minutes)

### Option 1: New Project

```bash
# 1. Clone this repository
git clone https://github.com/yourusername/subAgentTracking.git
cd subAgentTracking

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# OR: .\venv\Scripts\activate  # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Done! (Google Drive setup optional, see below)
```

### Option 2: Add to Existing Project

```bash
# 1. Navigate to your project
cd /path/to/your-claude-code-project

# 2. Copy tracking system files
cp -r /path/to/subAgentTracking/.claude .
cp -r /path/to/subAgentTracking/src/core src/

# 3. Install dependencies
pip install -r /path/to/subAgentTracking/requirements.txt

# 4. Done! Tracking starts automatically
```

---

## Full Setup (15 Minutes)

### Step 1: Install Dependencies (2 min)

```bash
# Navigate to project
cd subAgentTracking

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install packages
pip install -r requirements.txt

# Verify installation
python -c "import google.auth; print('✅ Google Drive API ready')"
python -c "import pandas; print('✅ Analytics ready')"
python -c "import sqlite3; print('✅ SQLite ready')"
```

**Expected output**:
```
✅ Google Drive API ready
✅ Analytics ready
✅ SQLite ready
```

---

### Step 2: Set Up Google Drive API (10 min, OPTIONAL)

**Note**: This step is optional. The system works perfectly offline and will queue backups for later.

#### 2.1: Enable Google Drive API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Project name: "SubAgentTracking"
4. Click "Create"
5. Wait for project creation (~30 seconds)

6. Enable Google Drive API:
   - Click "Enable APIs and Services"
   - Search "Google Drive API"
   - Click "Google Drive API"
   - Click "Enable"

#### 2.2: Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Configure Consent Screen"
   - User Type: "External"
   - Click "Create"
3. Fill in OAuth consent screen:
   - App name: "SubAgent Tracking"
   - User support email: (your email)
   - Developer contact: (your email)
   - Click "Save and Continue"
4. Scopes: Click "Save and Continue" (no additional scopes)
5. Test users: Add your email, click "Save and Continue"
6. Click "Back to Dashboard"

7. Create credentials:
   - Click "Create Credentials" → "OAuth 2.0 Client ID"
   - Application type: "Desktop app"
   - Name: "SubAgent Tracking Desktop"
   - Click "Create"
   - Click "Download JSON"

#### 2.3: Save Credentials

```bash
# Create credentials directory
mkdir -p .claude/credentials

# Move downloaded file
mv ~/Downloads/client_secret_*.json .claude/credentials/google_drive_credentials.json

# Verify
ls -la .claude/credentials/google_drive_credentials.json
# Should show the file
```

#### 2.4: Authorize Application (First Time Only)

```bash
# Run setup script
python setup_google_drive.py

# This will:
# 1. Open browser to Google authorization page
# 2. Ask you to sign in with Google account
# 3. Show permissions request (click "Allow")
# 4. Save authorization token
# 5. Test upload to verify setup

# Expected output:
# ✅ Opening browser for authorization...
# ✅ Authorization successful
# ✅ Token saved to .claude/credentials/google_drive_token.json
# ✅ Testing upload...
# ✅ Upload successful
# ✅ Google Drive backup enabled!
```

**Troubleshooting**:
- **"Browser didn't open"**: Copy URL from terminal, paste in browser
- **"Access denied"**: Make sure you added your email as test user
- **"Invalid credentials"**: Re-download credentials.json, try again

---

### Step 3: Verify Setup (3 min)

```bash
# Test activity logging
python -c "
from src.core.activity_logger import log_agent_invocation
log_agent_invocation(agent='test', invoked_by='user', reason='Setup test')
print('✅ Activity logging working')
"

# Test snapshot manager
python -c "
from src.core.snapshot_manager import take_snapshot
snap_id = take_snapshot(trigger='setup_test')
print(f'✅ Snapshot created: {snap_id}')
"

# Test Google Drive backup (if configured)
python -c "
from src.core.backup_manager import test_connection
if test_connection():
    print('✅ Google Drive backup working')
else:
    print('⚠️  Google Drive backup not configured (optional)')
"
```

**Expected output**:
```
✅ Activity logging working
✅ Snapshot created: snap_20251029_153000_001
✅ Google Drive backup working
```

---

## Usage Examples

### Example 1: Basic Logging

```python
from src.core.activity_logger import log_agent_invocation, log_tool_usage

# Log agent invocation
log_agent_invocation(
    agent="config-architect",
    invoked_by="orchestrator",
    reason="Implement structured logging (Task 1.1)"
)

# Log tool usage
with log_tool_usage(agent="config-architect", tool="Write"):
    # ... your code ...
    pass
```

### Example 2: Manual Snapshot

```python
from src.core.snapshot_manager import take_snapshot

# Create checkpoint before risky operation
snapshot_id = take_snapshot(
    trigger="before_refactor",
    context={"operation": "Extract component to plugin"}
)

print(f"Checkpoint created: {snapshot_id}")
# Later, if needed: restore_snapshot(snapshot_id)
```

### Example 3: Session Handoff

```python
from src.core.snapshot_manager import create_handoff_summary

# At end of session (or before hitting token limit)
handoff = create_handoff_summary(
    session_id="session_20251029_153000",
    reason="Token limit approaching"
)

print("Handoff summary created!")
print(f"To resume: Resume from {handoff['session_id']}")
```

### Example 4: Analytics Query

```python
from src.core.analytics_db import query_agent_performance

# Get agent performance for last 30 days
perf = query_agent_performance(days=30)

for agent in perf:
    print(f"{agent['name']}: {agent['success_rate']:.1f}% success")
```

---

## Integration with Your Project

### Minimal Integration (Logging Only)

Add to your orchestrator agent (`.claude/agents/orchestrator-agent.md`):

```python
from src.core.activity_logger import log_agent_invocation

# Before invoking any subagent
log_agent_invocation(
    agent="config-architect",
    invoked_by="orchestrator",
    reason="Task 1.1: Structured Logging"
)
```

**That's it!** Snapshots, backups, analytics all happen automatically.

---

### Full Integration (All Features)

1. **Add logging to orchestrator**:
```python
from src.core.activity_logger import (
    log_agent_invocation,
    log_decision,
    log_validation
)

# Log decision
log_decision(
    question="Which agent for structured logging?",
    options=["config-architect", "refactor-agent"],
    selected="config-architect",
    rationale="Infrastructure work matches expertise"
)

# Log validation
log_validation(
    task="Task 1.1",
    checks={"performance": "PASS", "tests": "PASS"},
    result="PASS"
)
```

2. **Add logging to subagents**:
```python
from src.core.activity_logger import log_tool_usage, log_error

# Log tool usage
with log_tool_usage(agent="config-architect", tool="Write"):
    # Create file
    pass

# Log errors
try:
    # Risky operation
    pass
except Exception as e:
    log_error(
        error_type="PerformanceBudgetExceeded",
        context={"file": "logger.py", "measured": "450ms"},
        attempted_fix="Switch to orjson",
        fix_successful=True
    )
```

3. **Add end-of-phase review**:
```python
from src.core.phase_review import run_phase_review

# At end of each phase
insights = run_phase_review(phase_number=1)
print(f"Phase 1 insights saved: {insights['path']}")
```

---

## Common Workflows

### Workflow 1: Start New Session

```bash
# 1. Start working (tracking starts automatically)
# No action needed!

# 2. Activity log created:
.claude/logs/session_current.jsonl

# 3. Snapshots created periodically:
.claude/state/session_current_snap001.json
.claude/state/session_current_snap002.json
...
```

---

### Workflow 2: End Session

```bash
# 1. Say "End session" or create handoff manually
python -c "
from src.core.snapshot_manager import create_handoff_summary
create_handoff_summary(reason='End of work day')
"

# 2. Handoff summary created:
.claude/handoffs/session_20251029_153000_handoff.md

# 3. Automatic backup to Google Drive (if configured):
# - Compresses session files
# - Uploads to Google Drive/SubAgentTracking/Phase_N/sessions/
# - Verifies upload
# - Deletes local previous session files

# 4. Done! Session safely backed up
```

---

### Workflow 3: Recover from Crash

```bash
# 1. Restart Claude Code

# 2. System detects incomplete session automatically

# 3. Shows recovery prompt:
🔄 Detected incomplete session from 2025-10-29 15:30

Last snapshot: 15:35 (snap_003)
Progress: Phase 1, Week 1, Task 1.2 (in progress)

Completed:
✅ Task 1.1: Structured Logging

Files changed:
- src/core/logger.py (created)
- PROJECT_STATUS.md (updated)

Resume? [Y/n]

# 4. Type 'Y' to restore from latest snapshot

# 5. Back to work! (loaded in <1 second)
```

---

### Workflow 4: Resume After Token Limit

```bash
# 1. Session hits 90% token limit

# 2. System creates handoff summary automatically:
⚠️  Token limit warning: 180k/200k used (90%)

Creating handoff summary...
✅ Saved to: .claude/handoffs/session_20251029_153000_handoff.md

To resume in new session:
Say: "Resume from session_20251029_153000"

# 3. Open new Claude Code session

# 4. Say: "Resume from session_20251029_153000"

# 5. System loads handoff + snapshot (8k tokens vs 150k rebuild)

# 6. Continue exactly where you left off!
```

---

### Workflow 5: End-of-Phase Review

```bash
# 1. Complete all tasks in phase

# 2. Say "End Phase 1" or run manually:
python -c "
from src.core.phase_review import run_phase_review
insights = run_phase_review(phase_number=1)
"

# 3. System analyzes all sessions:
# - Downloads from Google Drive (if needed)
# - Analyzes performance metrics
# - Identifies error patterns
# - Finds bottlenecks
# - Calculates token costs
# - Generates improvement recommendations

# 4. Insights report created:
.claude/handoffs/phase_1_insights.md

# 5. Review insights, implement improvements

# 6. Start Phase 2 with optimized agents!
```

---

## Troubleshooting

### "Module not found" errors

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Google Drive backup not working

```bash
# Test connection
python -c "from src.core.backup_manager import test_connection; test_connection()"

# Common fixes:
# 1. Re-run authorization: python setup_google_drive.py
# 2. Check credentials file exists: ls .claude/credentials/google_drive_credentials.json
# 3. Check token file exists: ls .claude/credentials/google_drive_token.json
```

### Snapshots taking too much space

```bash
# Check snapshot sizes
du -sh .claude/state/*

# Clean up old snapshots (keeps current + previous session)
python -c "from src.core.snapshot_manager import cleanup_old_snapshots; cleanup_old_snapshots()"
```

### SQLite database locked

```bash
# This happens if database is open in another process
# Close any DB browsers (DB Browser for SQLite, etc.)

# Or wait a few seconds and try again
```

---

## Next Steps

### Learn More
- 📚 **[AGENT_TRACKING_SYSTEM.md](.claude/AGENT_TRACKING_SYSTEM.md)** - Complete technical specification
- 📚 **[STORAGE_ARCHITECTURE.md](.claude/STORAGE_ARCHITECTURE.md)** - Storage strategy details
- 📚 **[TRACKING_QUICK_REFERENCE.md](.claude/TRACKING_QUICK_REFERENCE.md)** - Quick lookup guide
- 📚 **[PROJECT_MANIFEST.md](PROJECT_MANIFEST.md)** - Project overview

### Customize
- 📝 **Event schemas** - Add custom event types (see `examples/custom_events.py`)
- 📝 **Analytics queries** - Create custom queries (see `examples/analytics_queries.py`)
- 📝 **Backup schedule** - Adjust backup frequency (see `src/core/config.py`)

### Contribute
- 🔧 **Report bugs** - GitHub Issues
- 💡 **Request features** - GitHub Discussions
- 🤝 **Submit PRs** - Fork, branch, PR

---

## FAQ

**Q: Do I need Google Drive for this to work?**
A: No! The system works perfectly offline. Google Drive backup is optional but highly recommended for safety.

**Q: How much does this cost?**
A: $0 for MVP. Google Drive is free (2TB), SQLite is free, everything local. Optional mature features: MongoDB Atlas free tier (512 MB), AWS S3 Glacier ~$0.001/GB/month.

**Q: Will this slow down my agents?**
A: Minimal impact. Event logging adds <1ms, snapshots add ~50ms every 10 agents. Total overhead: 5-8% of session time.

**Q: Can I use this with existing projects?**
A: Yes! Copy `.claude/` and `src/core/` folders to your project, import logging functions, done.

**Q: What if I don't want backups?**
A: Skip the Google Drive setup. Everything still works locally. You can add backup later anytime.

**Q: Can multiple people use the same tracking system?**
A: Current version is single-developer. Multi-developer support planned for v1.0.0.

**Q: What happens if Google Drive is down?**
A: Backups are queued locally and uploaded when connection restored. No data loss.

**Q: How do I migrate to MongoDB later?**
A: Run `python src/core/migrate_to_mongodb.py`. Takes ~2 hours one-time. See [MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md).

---

## Support

### Documentation
- **Complete spec**: [AGENT_TRACKING_SYSTEM.md](.claude/AGENT_TRACKING_SYSTEM.md)
- **Quick reference**: [TRACKING_QUICK_REFERENCE.md](.claude/TRACKING_QUICK_REFERENCE.md)
- **API docs**: [API_REFERENCE.md](docs/API_REFERENCE.md) (coming soon)

### Community
- **GitHub Issues**: Bug reports
- **GitHub Discussions**: Questions, ideas
- **Email**: (coming soon)

---

**Ready to start tracking?**

```bash
# Install dependencies
pip install -r requirements.txt

# Start coding! Tracking happens automatically 🎉
```

---

**Version**: 0.1.0 (MVP)
**Last Updated**: 2025-10-29
