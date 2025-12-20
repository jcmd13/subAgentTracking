# SubAgent Tracking System - Agents Guide

## Repository Overview

### Project Description
SubAgent Tracking System is a **universal tracking, observability, and recovery system** for Claude Code agentic workflows. Think of it as "git for AI agents" - providing complete history, perfect recovery, and data-driven optimization.

**Main Purpose and Goals:**
- **Complete Activity Logging**: Track every agent invocation, tool usage, file operation, decision, and error
- **Session State Snapshots**: Create periodic checkpoints for instant recovery (90% faster than rebuilding context)
- **Historical Analytics**: Monitor agent performance, tool effectiveness, and error patterns
- **Cloud Backup & Archive**: Automatic Google Drive backup with optional AWS S3 archival
- **Token Savings**: 85-90% reduction in token usage for recovery operations

**Key Technologies Used:**
- **Language**: Python 3.10+
- **Storage**: JSONL (activity logs), JSON (snapshots), SQLite (analytics)
- **Cloud**: Google Drive API (OAuth2), AWS S3 Glacier (future)
- **Dependencies**: google-api-python-client, pandas, pydantic, pytest

## Architecture Overview

### High-Level Architecture
Three-tier storage system:
1. **Local Storage**: Fast (current + previous session only, ~20MB max)
2. **Google Drive**: Sync (all sessions for current phase, ~500MB per phase)
3. **AWS S3**: Archive (completed phases >2 back, $0.001/GB/month)

### Main Components
- **Activity Logger**: Event logging system (<1ms overhead per event)
- **Snapshot Manager**: State checkpoints every 10 agents or 20k tokens
- **Backup Manager**: Google Drive integration with automatic sync
- **Analytics DB**: SQLite database for aggregated metrics
- **Phase Review**: End-of-phase analysis and insights generation

### Data Flow
```
Agent Actions → Activity Logger → Analytics DB → Snapshot Manager → Backup Manager
```

## Directory Structure

### Important Directories
- **`.claude/`**: Tracking system configuration and storage
  - `logs/`: Activity logs (JSONL format)
  - `state/`: State snapshots (JSON format)
  - `analytics/`: SQLite database (agent metrics)
  - `handoffs/`: Session handoff summaries
  - `credentials/`: OAuth tokens (git-ignored)

- **`src/core/`**: Core tracking modules
  - `activity_logger.py`: Event logging system
  - `snapshot_manager.py`: State checkpoint system
  - `backup_manager.py`: Google Drive integration
  - `analytics_db.py`: SQLite analytics queries
  - `schemas.py`: Event type definitions

### Key Files and Configuration
- **`requirements.txt`**: Python dependencies
- **`setup_google_drive.py`**: One-time OAuth setup script
- **`.gitignore`**: Excludes credentials and local storage
- **`CLAUDE.md`**: Claude Code project guidance
- **`PROJECT_MANIFEST.md`**: Detailed project overview

### Entry Points and Main Modules
- **Automatic Integration**: Import `src.core.activity_logger` and usage begins automatically
- **Manual Operations**: Use snapshot, backup, and analytics functions directly
- **Test Entry**: `tests/` directory contains unit and integration tests

## Development Workflow

### How to Build/Run the Project
```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Optional Google Drive setup
python setup_google_drive.py

# Test the system
python -c "from src.core.activity_logger import log_agent_invocation; log_agent_invocation(agent='test', reason='Test')"
```

### Testing Approach
```bash
# Run all tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=src --cov-report=html

# Specific test file
pytest tests/test_activity_logger.py -v
```

### Development Environment Setup
- **Python 3.10+ required**
- **Virtual environment recommended**
- **Google account needed for backup features** (optional)
- **Zero-config by default** - works immediately without setup

### Lint and Format Commands
```bash
# Format code with Black
black src/ tests/

# Lint with flake8
flake8 src/ tests/

# Type checking with mypy
mypy src/
```

## Common Operations for AI Agents

### Agent Task Logging
```python
from src.core.activity_logger import log_agent_invocation

log_agent_invocation(
    agent="your-agent-name",
    invoked_by="orchestrator",
    reason="Specific task description"
)
```

### Snapshot Before Risky Operations
```python
from src.core.snapshot_manager import take_snapshot

snapshot_id = take_snapshot(
    trigger="before_risky_operation",
    context={"operation": "describe task"}
)
```

### Session Handoff
```python
from src.core.snapshot_manager import create_handoff_summary

handoff = create_handoff_summary(
    session_id="current_session",
    reason="Token limit or end of work"
)
```

### Error Recovery Options
```python
# To resume from last session:
# Say "Resume from session_[timestamp]" in Claude Code

# To view session history:
# Say "Show session history" in Claude Code
```

## Performance Characteristics

### Overhead
- **Event logging**: <1ms per event
- **Snapshot creation**: ~50ms every 10 agents or 20k tokens
- **Total overhead**: 5-8% of session time

### Recovery Savings
- **Status check**: 90% (50k → 5k tokens)
- **Error recovery**: 90% (100k → 10k tokens)
- **Session resume**: 95% (150k → 8k tokens)

## Integration Patterns

### Copy to Existing Project
```bash
cp -r .claude /path/to/your/project/
cp -r src/core /path/to/your/project/src/
```

### Minimal Integration
```python
from src.core.activity_logger import log_agent_invocation

# Add to orchestrator before invoking any subagent
log_agent_invocation(
    agent="task-specific-agent",
    invoked_by="orchestrator", 
    reason="Task description"
)
```

## Troubleshooting

### Common Issues
- **"Module not found"**: Activate virtual environment `source venv/bin/activate`
- **Google Drive backup issues**: Re-run `python setup_google_drive.py`
- **SQLite locked**: Close any DB browsers and wait a few seconds
- **Snapshot space**: Run cleanup (keeps current + previous session only)

### Verification Commands
```bash
# Test logging
python -c "from src.core.activity_logger import log_agent_invocation; log_agent_invocation(agent='test', invoked_by='user', reason='Test'); print('✅ Logging works')"

# Test snapshot
python -c "from src.core.snapshot_manager import take_snapshot; snap_id = take_snapshot(trigger='test'); print(f'✅ Snapshot: {snap_id}')"

# Test backup (if configured)
python -c "from src.core.backup_manager import test_connection; print('✅ Backup works' if test_connection() else '⚠️ Not configured')"
```

## Agent-Specific Considerations

### For Claude Code Agents
- This system is designed to integrate seamlessly with Claude Code workflows
- Tracking happens automatically once imported
- Snapshots automatically prevent token limit issues
- Recovery from crashes is instant

### For Human Developers
- All data is human-readable (JSON/Markdown)
- Analytics can be queried via SQL or Python
- Backups are stored in accessible Google Drive structure
- Phase reviews generate actionable insights

### For Codex CLI Sessions
- If `.subagent/config.yaml` is missing, prefer `/prompts:subagent-init` or allow the auto-init prompt.
- Do not ask the user to run setup commands manually; defaults should be used unless explicitly requested.
- Advanced settings live in `.subagent/config.yaml` and should stay out of the main workflow.
