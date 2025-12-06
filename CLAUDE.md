# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**SubAgent Tracking System** - Universal tracking, observability, and recovery system for Claude Code agentic workflows. Think "git for AI agents" - complete history, perfect recovery, and data-driven optimization.

**Status**: MVP Phase (v0.1.0, Active Development)
**Language**: Python 3.10+

## Core Purpose

Solves the "lost context on crashes/token limits" problem for multi-agent Claude Code projects by providing:
- Complete activity logging (every agent invocation, tool usage, file operation, decision, error)
- Session state snapshots (periodic checkpoints for instant recovery)
- Historical analytics (agent performance, tool effectiveness, error patterns)
- Cloud backup & archive (Google Drive, optional AWS S3)

**Token Savings**: 85-90% on recovery operations (status check: 50k→5k, session resume: 150k→8k)

## Development Commands

### Setup
```bash
# Create virtual environment and install dependencies
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt

# Optional: Google Drive backup setup (one-time, 10 min)
python setup_google_drive.py
```

### Testing
```bash
# Run all tests (when implemented)
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test file
pytest tests/test_activity_logger.py -v
```

### Code Quality
```bash
# Format code with Black
black src/ tests/

# Lint with flake8
flake8 src/ tests/

# Type checking with mypy
mypy src/
```

### Verification
```bash
# Test activity logging
python -c "from src.core.activity_logger import log_agent_invocation; log_agent_invocation(agent='test', invoked_by='user', reason='Test'); print('✅ Logging works')"

# Test snapshot manager
python -c "from src.core.snapshot_manager import take_snapshot; snap_id = take_snapshot(trigger='test'); print(f'✅ Snapshot: {snap_id}')"

# Test Google Drive backup (if configured)
python -c "from src.core.backup_manager import test_connection; print('✅ Backup works' if test_connection() else '⚠️ Not configured')"
```

## Architecture

### Three-Tier Storage Strategy

**Tier 1: Local Storage (Fast)**
- Location: `.claude/logs/`, `.claude/state/`, `.claude/analytics/`
- Contents: Activity logs (JSONL), snapshots (JSON), analytics (SQLite)
- Retention: Current + previous session
- Size: ~20 MB max

**Tier 2: Google Drive (Sync)**
- Contents: All sessions for current phase, phase insights
- Retention: 2 phases
- Size: ~500 MB per phase
- Cost: Free (2TB Google Drive)

**Tier 3: AWS S3 Glacier (Archive)** - Planned
- Contents: Completed phases (>2 phases old)
- Retention: Forever
- Cost: $0.001/GB/month

### Three-Layer Tracking System

1. **Activity Log** (`.claude/logs/session_current.jsonl`)
   - Append-only JSONL format (gzip compressed)
   - Every event: agent invocations, tool usage, file operations, decisions, errors
   - Async writes to avoid blocking
   - Complete audit trail for debugging

2. **State Snapshots** (`.claude/state/session_current_snapNNN.json`)
   - Triggered every 10 agent invocations or 20k tokens
   - JSON format for human readability
   - Contains: transcript summary, modified files, agent context, token usage
   - Enables instant recovery without reading full history

3. **Analytics DB** (`.claude/analytics/tracking.db`)
   - SQLite database for aggregated metrics
   - Agent performance tracking, tool effectiveness, error patterns
   - Query interface for insights and optimization

### Event-Driven Flow

```
Agent Action → Activity Logger → Analytics DB → Snapshot Manager → Backup Manager
```

### Core Components

**`src/core/activity_logger.py`** - Event logging system
- Functions: `log_agent_invocation()`, `log_tool_usage()`, `log_decision()`, `log_validation()`, `log_error()`
- Format: JSONL (one JSON object per line)
- Compression: gzip for storage efficiency
- Performance: <1ms overhead per event

**`src/core/snapshot_manager.py`** - State checkpoint system
- Functions: `take_snapshot()`, `restore_snapshot()`, `create_handoff_summary()`
- Triggers: Manual, every 10 agents, every 20k tokens, before token limit
- Format: JSON with metadata (timestamp, trigger, files changed, git hashes)
- Recovery: ~50ms to load snapshot vs minutes to rebuild context

**`src/core/backup_manager.py`** - Google Drive integration
- Functions: `backup_session()`, `restore_session()`, `test_connection()`
- Timing: Automatic at session end, manual on demand
- Format: tar.gz archives with version history
- Authentication: OAuth 2.0 (credentials in `.claude/credentials/`, git-ignored)

**`src/core/analytics_db.py`** - SQLite metrics database
- Functions: `query_agent_performance()`, `query_tool_effectiveness()`, `query_error_patterns()`
- Schema: agents, tools, errors, sessions tables
- Queries: Performance metrics, cost optimization insights

**`src/core/phase_review.py`** - End-of-phase analysis
- Function: `run_phase_review(phase_number)`
- Analyzes all phase sessions, generates insights report
- Output: `.claude/handoffs/phase_N_insights.md`

## Project Structure

```
subAgentTracking/
├── .claude/                              # Tracking system configuration
│   ├── AGENT_TRACKING_SYSTEM.md         # Complete technical spec (28k tokens)
│   ├── STORAGE_ARCHITECTURE.md          # Storage strategy docs (26k tokens)
│   ├── TRACKING_QUICK_REFERENCE.md      # Quick lookup guide
│   ├── logs/                            # Activity logs (JSONL, git-ignored)
│   ├── state/                           # Snapshot storage (JSON, git-ignored)
│   ├── analytics/                       # SQLite database (git-ignored)
│   ├── credentials/                     # OAuth tokens (git-ignored)
│   └── handoffs/                        # Session handoff summaries
│
├── src/core/                            # Core tracking modules
│   ├── activity_logger.py               # Event logging system
│   ├── snapshot_manager.py              # State snapshots
│   ├── backup_manager.py                # Google Drive integration
│   ├── analytics_db.py                  # SQLite analytics
│   └── phase_review.py                  # End-of-phase analysis
│
├── docs/                                # Documentation (planned)
│   ├── SETUP_GUIDE.md
│   ├── INTEGRATION_GUIDE.md
│   ├── API_REFERENCE.md
│   └── BEST_PRACTICES.md
│
├── examples/                            # Usage examples (planned)
│   ├── basic_usage.py
│   ├── custom_events.py
│   └── analytics_queries.py
│
├── tests/                               # Test files (minimal coverage currently)
│   ├── test_activity_logger.py
│   ├── test_snapshot_manager.py
│   └── test_backup_manager.py
│
├── requirements.txt                     # Python dependencies
├── setup_google_drive.py                # One-time OAuth setup script
├── GETTING_STARTED.md                   # Setup instructions
├── README.md                            # Project overview
├── PROJECT_MANIFEST.md                  # Detailed manifest
├── LLM_SETUP_GUIDE.md                   # LLM configuration
├── MULTI_LLM_ARCHITECTURE.md            # Multi-LLM strategy
└── .gitignore
```

## Key Dependencies

**Core (MVP Phase)**:
- `google-api-python-client >= 2.100.0` - Google Drive API
- `google-auth-oauthlib >= 1.1.0` - OAuth authentication
- `pandas >= 2.0.0` - Data processing
- `matplotlib >= 3.7.0` - Analytics visualization
- `sqlite3` - Built-in (no package needed)

**Development**:
- `pytest >= 7.4.0`, `pytest-asyncio >= 0.21.0`, `pytest-cov >= 4.1.0` - Testing
- `black >= 23.9.0`, `flake8 >= 6.1.0`, `mypy >= 1.5.0` - Linting/formatting

**Future (Commented out in requirements.txt)**:
- `pymongo >= 4.5.0` - MongoDB Atlas (mature phase)
- `boto3 >= 1.28.0` - AWS S3 (archive phase)

## Common Workflows

### Integration into Claude Code Projects

**Minimal Integration** (recommended for new adopters):
```python
from src.core.activity_logger import log_agent_invocation

# Before invoking any subagent
log_agent_invocation(
    agent="config-architect",
    invoked_by="orchestrator",
    reason="Task 1.1: Implement structured logging"
)
```
That's it! Snapshots, backups, and analytics happen automatically.

**Full Integration**:
```python
from src.core.activity_logger import (
    log_agent_invocation,
    log_decision,
    log_validation,
    log_tool_usage,
    log_error
)

# Log decisions
log_decision(
    question="Which agent for structured logging?",
    options=["config-architect", "refactor-agent"],
    selected="config-architect",
    rationale="Infrastructure work matches expertise"
)

# Log tool usage
with log_tool_usage(agent="config-architect", tool="Write"):
    # Create file
    pass

# Log validation
log_validation(
    task="Task 1.1",
    checks={"performance": "PASS", "tests": "PASS"},
    result="PASS"
)

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

### Manual Snapshots Before Risky Operations

```python
from src.core.snapshot_manager import take_snapshot

# Create checkpoint before major refactor
snapshot_id = take_snapshot(
    trigger="before_refactor",
    context={"operation": "Extract component to plugin"}
)

# Later, if needed: restore_snapshot(snapshot_id)
```

### Session Handoff (Token Limit or End of Day)

```python
from src.core.snapshot_manager import create_handoff_summary

# Create handoff summary
handoff = create_handoff_summary(
    session_id="session_20251029_153000",
    reason="Token limit approaching"
)

# To resume in new session: "Resume from session_20251029_153000"
```

### End-of-Phase Review

```python
from src.core.phase_review import run_phase_review

# At end of each phase
insights = run_phase_review(phase_number=1)
# Generates: .claude/handoffs/phase_1_insights.md
```

## Configuration

**Zero-config by default** - Works out-of-box with local storage only.

**Optional: Google Drive Backup**
1. Run `python setup_google_drive.py` (one-time, 10 min)
2. Credentials saved to `.claude/credentials/google_drive_credentials.json`
3. Token saved to `.claude/credentials/google_drive_token.json`
4. Both files are git-ignored for security

**Storage Limits**:
- Local: ~20 MB (current + previous session)
- Google Drive: ~500 MB per phase (automatic cleanup)
- Snapshots triggered: Every 10 agents OR 20k tokens

## Performance Characteristics

**Overhead**:
- Event logging: <1ms per event
- Snapshot creation: ~50ms every 10 agents
- Total overhead: 5-8% of session time

**Savings**:
- Status check: 90% (50k → 5k tokens)
- Error recovery: 90% (100k → 10k tokens)
- Session resume: 95% (150k → 8k tokens)
- Debug capability: Infinite improvement (was impossible)

## Current Development Status

**Phase 0: Core System** ✅ Complete
- [x] Activity logging (JSONL)
- [x] State snapshots (JSON)
- [x] SQLite analytics
- [x] Documentation

**Phase 1: Backup & Recovery** 🟡 In Progress
- [x] Google Drive backup design
- [ ] Backup manager implementation
- [ ] Automatic session handoff
- [ ] Recovery UI

**Phase 2: Analytics & Insights** 🔵 Planned
- [ ] End-of-phase review automation
- [ ] Performance metrics dashboard
- [ ] Error pattern analysis
- [ ] Agent optimization recommendations

**Phase 3: Advanced Features** 🔵 Future
- [ ] MongoDB Atlas integration
- [ ] AWS S3 archival
- [ ] Web dashboard for analytics
- [ ] Multi-developer collaboration

## Important Design Principles

1. **Local-First**: Everything works offline, cloud backup is optional
2. **Zero-Config**: Works immediately without setup
3. **Append-Only Logs**: Activity logs never modified (safety + auditability)
4. **Async Operations**: Logging/snapshots don't block agents
5. **Compression**: gzip for logs, tar.gz for backups
6. **Git-Aware**: Tracks file changes with git hashes when available
7. **Privacy**: All credentials git-ignored, local processing by default

## Testing Notes

**Current Status**: Minimal test coverage (MVP phase focus on design)

**When Writing Tests**:
- Use `pytest` with async support (`pytest-asyncio`)
- Mock Google Drive API calls (don't require real credentials)
- Test activity logger independently (verify JSONL format)
- Test snapshot creation/restoration (use temp directories)
- Test analytics queries (use in-memory SQLite)

**Coverage Goals**:
- Phase 1: 70% coverage on core modules
- Phase 2: 85% coverage with integration tests
- Phase 3: 90% coverage with end-to-end tests

## Common Integration Patterns

**Pattern 1: Copy to existing project**
```bash
cp -r .claude /path/to/your/project/
cp -r src/core /path/to/your/project/src/
```

**Pattern 2: Import as submodule** (future)
```bash
git submodule add https://github.com/yourusername/subAgentTracking.git
```

**Pattern 3: Use as library** (future, when published to PyPI)
```bash
pip install subagent-tracking
```

## Troubleshooting

**"Module not found" errors**: Activate virtual environment (`source venv/bin/activate`)

**Google Drive backup not working**: Re-run `python setup_google_drive.py` or check credentials in `.claude/credentials/`

**Snapshots taking too much space**: Run cleanup (keeps current + previous session only)

**SQLite database locked**: Close any DB browsers or wait a few seconds

## Zen MCP Integration

**Status**: Configured and Active (v1.1 - Ollama Integrated)

This project uses [Zen MCP Server](https://github.com/BeehiveInnovations/zen-mcp-server) with a three-tier model strategy to offload high-token analysis tasks while maintaining Claude Code quality for implementation.

### Core Strategy: Three-Tier Model Selection

**TIER 1: Ollama (Try First)** ⭐
- `gpt-oss:120b-cloud` - 120B params, cloud-hosted, FREE, PRIMARY model
- `deepseek-v3.1:671b-cloud` - 671B params, complex reasoning, FREE
- Local models (mistral, phi3.5, etc.) - Quick drafts, offline work
- **Quality Gate**: Score ≥ 18/25 to use, fallback to Tier 2 if lower

**TIER 2: Gemini (Refinement & High-Stakes)** ✅
- `gemini-2.5-pro` - 1M context, proven reliable, FREE
- `gemini-2.5-flash` - Ultra-fast for quick checks, FREE

**TIER 3: Paid Models (Avoid)** ❌
- `gpt-5-pro`, `o3-pro`, etc. - COST $$$
- **Only use if**: Both Tier 1 and 2 demonstrably fail quality checks

**Token Distribution** (when Ollama quality is good):
- **60-70% Ollama** (free): Experimental validation, analysis
- **20-30% Gemini** (free): Refinement, high-stakes validation
- **10% Claude** (focused): Final code generation, implementation

**Cost Optimization**:
- Try Ollama first for non-critical tasks
- Validate quality rigorously (5-point checklist)
- Fallback to Gemini if needed
- **Avoid**: Paid models entirely

### Zen MCP Documentation

**Quick Start**:
- **`.claude/ZEN_MCP_QUICK_REFERENCE.md`** - 2-minute lookup guide (updated for Ollama)
- **`.claude/ZEN_MCP_DECISION_TREE.md`** - Visual decision trees (three-tier strategy)
- **`.claude/ZEN_MCP_RULES.md`** - Comprehensive usage rules (Ollama-first workflows)
- **`.claude/OLLAMA_INTEGRATION_RULES.md`** - Detailed Ollama quality validation guide

### Common Zen Workflows (Ollama-First)

**Code Analysis** (saves ~95% tokens):
```
1. mcp__zen__analyze with gpt-oss:120b-cloud
2. Claude validates quality (score: 21/25 ✅)
3. Claude implements based on Ollama findings

Alternative (if quality score < 18/25):
1. mcp__zen__analyze with gpt-oss:120b-cloud
2. Claude validates quality (score: 16/25 ⚠️)
3. mcp__zen__analyze with gemini-2.5-pro (refine)
4. Claude implements based on refined findings
```

**Debugging** (saves ~90% tokens):
```
1. mcp__zen__debug with gpt-oss:120b-cloud
2. Claude validates quality
3. If score ≥ 18/25: Claude implements fix
   If score < 18/25: Refine with gemini-2.5-pro, then fix
```

**Feature Implementation** (saves ~85% tokens + quality validation):
```
1. mcp__zen__planner with gpt-oss:120b-cloud
2. Claude validates quality (if ≥ 18/25, proceed; else refine with Gemini)
3. mcp__zen__chat with gpt-oss:120b-cloud (discuss approach)
4. Claude implements code
5. mcp__zen__codereview with gpt-oss:120b-cloud (validate quality)
6. Claude fixes issues
7. mcp__zen__precommit with gemini-2.5-pro (high-stakes final check)
8. Claude commits
```

**High-Stakes Tasks** (skip Ollama):
```
Security audit, production deployment, critical bug fix:
→ Skip Ollama (unproven for critical tasks)
→ Use gemini-2.5-pro directly
→ Claude implements with proven-quality findings
```

### Integration with Activity Logger

Log Ollama usage with quality tracking:
```python
from src.core.activity_logger import log_tool_usage, log_decision

# Log decision to use Ollama
log_decision(
    question="Which model for code analysis?",
    options=["Ollama (gpt-oss:120b-cloud)", "Gemini", "Claude direct"],
    selected="Ollama (gpt-oss:120b-cloud)",
    rationale="150k+ tokens, Ollama is free + quality validation"
)

# Log Ollama usage with quality score
log_tool_usage(
    agent="ollama",
    tool="gpt-oss:120b-cloud",
    details={
        "task_type": "code_analysis",
        "quality_score": "21/25",
        "breakdown": {
            "correctness": 5,
            "completeness": 4,
            "specificity": 4,
            "context_awareness": 4,
            "actionability": 4
        },
        "outcome": "used_as_is",
        "token_estimate": "~150k tokens"
    }
)
```

### Available Models (Three-Tier Strategy)

**TIER 1 - FREE (Try First)** ⭐:
- `gpt-oss:120b-cloud` - 120B params, cloud-hosted, PRIMARY Ollama model
- `deepseek-v3.1:671b-cloud` - 671B params, complex reasoning
- `mistral:latest`, `phi3.5:3.8b` - Local models for quick drafts

**TIER 2 - FREE (Refinement)** ✅:
- `gemini-2.5-pro` - 1M context, proven reliable
- `gemini-2.5-flash` - Ultra-fast for quick checks

**TIER 3 - PAID (Avoid)** ❌:
- All OpenAI models (`gpt-5-pro`, `gpt-5`, `o3-pro`, etc.)
- OpenRouter models
- **Exception**: Only if both Ollama AND Gemini fail quality checks

### Quality Validation (5-Point Checklist)

**For Ollama Output** - Score 1-5 on each:
1. **Correctness**: Factually accurate?
2. **Completeness**: All aspects addressed?
3. **Specificity**: Concrete vs vague?
4. **Context Awareness**: Understands project context?
5. **Actionability**: Can Claude implement directly?

**Scoring**:
- **20-25/25**: ✅ Use as-is
- **18-19/25**: ✅ Use with minor validation
- **15-17/25**: ⚠️ Refine with Gemini
- **< 15/25**: ❌ Discard, use Gemini

**For Gemini Output** - Proven reliable:
- Quick validation for critical issues only
- Trust output unless obviously flawed

### Token Savings Examples

| Task | Claude Only | With Ollama (validated) | With Gemini (fallback) | Savings |
|------|-------------|-------------------------|------------------------|---------|
| Analyze architecture | ~150k tokens | ~5k tokens | ~8k tokens | 95-97% |
| Debug complex bug | ~100k tokens | ~6k tokens | ~10k tokens | 90-94% |
| Pre-commit review | ~50k tokens | ~3k tokens | ~5k tokens | 90-94% |
| Plan feature | ~80k tokens | ~4k tokens | ~6k tokens | 93-95% |

**Expected Savings**:
- **With Ollama** (when quality ≥ 18/25): 95-97% of analysis tokens moved to validation workflow
- **With Gemini** (fallback): 85-95% of analysis/review tokens
- **Bonus**: Quality validation data and multi-model checking at zero added cost

## Related Documentation

For comprehensive details, see:

**Training Materials** (Separate Repository):
- **[SubAgent Training Repository](https://github.com/jcmd13/subAgentTracking-training)** - Complete training program with tutorials, exercises, and hands-on projects

**Core Tracking System**:
- **`.claude/AGENT_TRACKING_SYSTEM.md`** (28k) - Complete technical specification
- **`.claude/STORAGE_ARCHITECTURE.md`** (26k) - Storage strategy & capacity planning
- **`.claude/TRACKING_QUICK_REFERENCE.md`** - Quick lookup guide for common operations

**Zen MCP & Model Strategy**:
- **`.claude/ZEN_MCP_RULES.md`** - Comprehensive Zen MCP usage rules (three-tier strategy)
- **`.claude/ZEN_MCP_QUICK_REFERENCE.md`** - Quick Zen MCP reference (Ollama-first)
- **`.claude/ZEN_MCP_DECISION_TREE.md`** - Visual decision trees (updated for Ollama)
- **`.claude/OLLAMA_INTEGRATION_RULES.md`** - Detailed Ollama quality validation guide

**Project Documentation**:
- **`GETTING_STARTED.md`** - Detailed setup instructions with examples
- **`README.md`** - High-level project overview
- **`PROJECT_MANIFEST.md`** - Comprehensive project manifest
- **`MULTI_LLM_ARCHITECTURE.md`** - Multi-LLM cost optimization strategy
