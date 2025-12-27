# SubAgent Tracking System

Single source of truth for requirements and project tracking.
Last updated: 2025-12-20

## What this is
A neutral observability and governance layer for AI coding workflows. It tracks
agent activity, task lifecycle, approvals, tests, and recovery checkpoints with
minimal disruption to developer flow. Think of it as "git for AI agents" plus
governance signals.

## Quick summary
- Core tracking, snapshots, analytics, and session handoffs are implemented.
- CLI, dashboard server, and WebSocket monitor are implemented.
- Adapter SDK, providers, and MCP server exist; E2E validation is pending.
- Approvals and risk scoring exist; alert UX and blocking hooks are pending.
- Requirements and roadmap live in this document only.

## Quick start
1) Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
2) Install in editable mode to use the CLI:
```bash
pip install -e .
```
3) Initialize the data directory:
```bash
subagent init
```

Optional Google Drive backup setup:
```bash
python setup_google_drive.py
```

Minimal integration example:
```python
from src.core.activity_logger import log_agent_invocation

log_agent_invocation(agent="your-agent", invoked_by="orchestrator", reason="Task X")
```

## Requirements (single source)

### Observability and Governance Layer
F001 Task Lifecycle and State Model (Done).
User stories: US001 see current task stage, US002 track project progress.
Acceptance criteria: AC001 task events exist; AC002 payload includes task_id, stage, summary;
AC003 task state persisted in analytics DB; AC004 task progress stored and updated; AC005 dashboard
shows percent complete for active tasks.
Tasks: T001 add task lifecycle event types, T002 update metrics/ingestion, T003 add task state model.

F002 Human-In-Loop Approvals and Risk Scoring (In progress).
User story: US003 require approval for risky changes.
Acceptance criteria: AC006 risk scoring computed for risky file ops; AC007 approval required event emitted
when threshold exceeded; AC008 hooks can block action until approval is granted.
Tasks: T004 risk heuristics, T005 approval events and hooks, T006 rollback guidance (pending).

F003 Test Telemetry and Quality Signals (Done).
User story: US004 see test status in real time.
Acceptance criteria: AC009 test start and completion events exist; AC010 results include pass/fail and duration;
AC011 dashboard shows last test status for current task.
Tasks: T007 add test event types, T008 wire telemetry to dashboard and metrics.

### Adapter SDK
F001 Adapter SDK and Event Mapping (Done).
User story: integrate a new tool quickly with map_event and emit.
Acceptance criteria: adapter interface defined; supports sync/async emitters; minimal example documented.
Tasks: T001 interface/registration, T002 mapping helpers/validation, T003 docs/examples.

F002 Built-in Adapters for Top Tools (In progress).
User story: use existing tools without extra setup.
Acceptance criteria: Aider adapter done; Continue adapter pending; OpenHands or Claude Code adapter pending.
Tasks: T004 Aider adapter, T005 Continue adapter, T006 OpenHands/Claude adapter.

F003 Privacy and Redaction Controls (Done).
User story: control what data is captured.
Acceptance criteria: redaction rules support paths and regex; allowlist per adapter.
Tasks: T007 redaction configuration, T008 apply redaction in adapter pipeline.

### Dashboard UX
F001 Task Strip and Session Summaries (In progress).
User stories: US001 task strip with stage/status, US002 concise session summaries.
Acceptance criteria: AC001 task strip shows task/stage/ETA; AC002 task strip collapses; AC003 summary includes
changes/tests/cost/risks; AC004 summary available in dashboard and exportable.
Tasks: T001 task strip UI done, T002 session summary card/export done.

F002 Alerts and Risk Signals (Not started).
User story: US003 alerts only when needed.
Acceptance criteria: AC005 alerts drawer shows severity and recommended action; AC006 alerts collapse after ack.
Tasks: T003 alerts drawer, T004 wire alerts to risk/test events.

F003 Focus Mode and Filters (Not started).
User story: US004 hide non-essential data.
Acceptance criteria: AC007 focus mode persists; AC008 event stream supports severity/task filters.
Tasks: T005 focus mode toggle, T006 event stream filters.

### Status Ribbon Observability Overlay (optional)
Goal: a single-line status ribbon for Claude Code, Codex CLI, and generic terminals.
Modes: Minimal, Balanced, Power. Degrade order: alerts, task, progress, context, spend, files, tools.

Core requirements:
- FR1 StatusSnapshot data model (serializable JSON state for rendering).
- FR2 CLI render command: `subagent ui ribbon --mode balanced --width 117 --format plain|ansi|tmux`.
- FR3 Inspector command: `subagent ui inspect --width 117`.
- FR4 UI daemon that subscribes to events and writes snapshots on a cadence.

StatusSnapshot fields (condensed):
```
timestamp_ms
workspace: project_dir, cwd
agent_session: active_agent_name, active_model_id, provider
task: current_task_id, current_task_title, current_task_phase, next_task_id, task_started_ms, last_activity_ms,
      stuck_score/idle_seconds
progress: mode, phase_index/phase_total, complete_pct, bar_text
files: changed_count, created_count, last_touched_path
usage: context_pct, tokens_used/window, cost_run_usd, cost_daily_usd/budget, cost_weekly_usd/budget
tools: calls_shell, calls_fs, calls_web, calls_other
alerts: list of {severity, code, message}
```

### Advanced features already implemented (not fully surfaced)
- PRD management system (parser, schemas, state, progress stats).
- Event bus (pub/sub with async handlers).
- Agent coordinator (scout/plan/build workflow).
- Context optimizer.
- Analytics engine and fleet monitor.
- Dashboard server (observability layer).

## Tracking and roadmap (single source)

### Pivot phases (current)
Phase 0 Quick wins and dogfood: task lifecycle events, session summaries, task strip, test telemetry (Done).
Phase 1 Task state + metrics: persist task state and show progress metrics (In progress).
Phase 2 Adapter SDK MVP: adapter interface, redaction/allowlist, pilot adapter (In progress).
Phase 3 Approvals + risk scoring UX: approvals queue, blocking hooks, alert UX (In progress).
Phase 4 UX polish + focus mode: filters, summaries, export (Planned).
Phase 5 Release + adoption: guided setup, second adapter (Planned).

### Blockers requiring troubleshooting or human validation
- Live provider validation (credentials + opt-in)
- MCP end-to-end smoke test with Claude Code
- Approval UX calibration to avoid false blocks/noise

### Phase 0 critical fixes (complete)
- BackupManager high-level methods added and integrated.
- Deprecated datetime.utcnow replaced with timezone-aware timestamps.
- Thread safety fixes for parent event tracking.
- Atomic file operations and retry on snapshot failure.
- Log rotation and event ID format updates.

### Known TODOs (non-blocking metrics)
- Publish AGENT_BLOCKED event in `src/core/hooks_manager.py`.
- Track session duration and tokens in `src/core/activity_logger_compat.py`.
- Determine session success from exit status in `src/core/analytics_db_subscriber.py`.
- Capture snapshot size bytes in `src/core/snapshot_manager_subscriber.py`.

### Quality audit summary (condensed)
- Code quality grade: A-; test coverage ~85%.
- Documentation sprawl resolved by consolidating into this file.
- Recommended next actions: resolve the 4 TODOs, finish approvals UX, finish dashboard focus/alerts.

## Architecture overview
Data flow:
Agent actions -> Activity Logger -> Analytics DB -> Snapshot Manager -> Backup Manager

Storage tiers:
- Local (fast): JSONL logs, JSON snapshots, SQLite analytics, session handoffs
- Google Drive (sync): optional, backs up current phase sessions
- AWS S3 (archive): planned for mature phase

Key components:
- Core tracking: `src/core/`
- CLI: `src/subagent_cli/`
- Observability: `src/observability/`
- Adapters: `src/adapters/`
- MCP server: `src/subagent/mcp/`
- Tests: `tests/`

## Data directories and retention
Default data root is `.subagent/` with legacy `.claude/` support.

Runtime data locations:
- `.subagent/logs/` activity logs (JSONL, gzip)
- `.subagent/state/` snapshots (JSON)
- `.subagent/analytics/` SQLite analytics
- `.subagent/handoffs/` session summaries
- `.subagent/quality/` quality gate reports
- `.subagent/approvals/` approval queue state
- `.subagent/observability/` dashboard/monitor runtime state

Retention policy (local-first): current + previous session only; analytics DB retained; backups optional.

## Configuration
Important files:
- `.subagent/config.yaml` core settings
- `.subagent/config/permissions.yaml` tool/path/network permissions
- `.subagent/config/providers.yaml` provider adapter config

Selected environment variables:
- `SUBAGENT_DATA_DIR` override data root
- `SUBAGENT_PROJECT_DIR` MCP server project root
- `SUBAGENT_PROVIDER_LIVE` or `SUBAGENT_LIVE_PROVIDERS` enable live providers
- `SUBAGENT_APPROVAL_THRESHOLD` risk threshold for approvals
- `SUBAGENT_APPROVALS_BYPASS=1` bypass approvals (dev only)
- `SUBAGENT_MIGRATE_LEGACY=1` create `.subagent` symlink to legacy `.claude`

## CLI (high level)
- `subagent init` create `.subagent/` structure
- `subagent status [--json] [--watch] [--interval]` show system status
- `subagent session-start|session-end|session-list`
- `subagent task add|update|complete|list|show`
- `subagent logs [--follow] [--count N] [--task-id ID]`
- `subagent emit-task-start|emit-task-stage|emit-task-complete`
- `subagent emit-test-start|emit-test-complete`
- `subagent tool check|simulate|read|write|edit`
- `subagent agent spawn|pause|resume|terminate|list|show`
- `subagent quality run [--test-suite LABEL] [--task-id ID]`
- `subagent metrics --scope session|task|project [--export report.md]`
- `subagent approval list|approve|deny`
- `subagent dashboard start|stop [--host HOST --port PORT]`
- `subagent monitor start|stop [--host HOST --port PORT]`

## MCP integration
Start the MCP JSON-RPC server:
```bash
python -m subagent.mcp.server
```
Point it at a repo:
```bash
export SUBAGENT_PROJECT_DIR=/path/to/project
```
Claude Code config example:
```json
{
  "mcpServers": {
    "subagent": {
      "command": "python",
      "args": ["-m", "subagent.mcp.server"],
      "env": {"SUBAGENT_PROJECT_DIR": "/path/to/project"}
    }
  }
}
```

## Adapter SDK (summary)
Adapters map tool-specific events into the standard event schema.

Minimal usage:
```python
from src.adapters import AiderAdapter, AdapterRegistry

adapter = AiderAdapter()
AdapterRegistry.register(adapter)
adapter.handle_event({"type": "task_started", "task_id": "task_001"})
```

Redaction and allowlist example:
```python
from src.adapters import AiderAdapter, RedactionRule

rules = [RedactionRule(path="prompt", pattern=r"sk-[A-Za-z0-9]+")]
adapter = AiderAdapter(allowlist=["type", "task_id", "task_name", "stage", "prompt"], redaction_rules=rules)
```

## Provider adapters (summary)
Providers are opt-in for live calls. Example `.subagent/config/providers.yaml`:
```yaml
providers:
  live: true
  order: [claude, ollama, gemini]
  claude:
    model: claude-sonnet-3.5
    api_key: "..."
  ollama:
    model: llama3
    endpoint: "http://localhost:11434"
  gemini:
    model: gemini-2.0-pro
    api_key: "..."
```

Suggested usage (cost-optimized):
- Claude Sonnet 3.5 for complex refactors and architecture.
- Gemini Flash for general tasks and test generation.
- Ollama for local or fast review tasks.
- Perplexity for web research (if enabled).

## Permissions and approvals
Permissions live in `.subagent/config/permissions.yaml` and gate tools, paths,
and network access. Example:
```yaml
permissions:
  default_profile: default_worker
  profiles:
    default_worker:
      tools: ["read", "write", "edit", "provider"]
      paths_allowed: ["src/**", "tests/**"]
      paths_forbidden: [".env*", "*.secret", ".subagent/config.yaml"]
      can_run_bash: false
      can_access_network: false
    elevated:
      can_run_bash: true
      can_access_network: true
```

CLI helpers:
- `subagent tool check --tool read --path src/app.py`
- `subagent tool simulate --tool read --path src/app.py`
- `subagent tool read src/app.py`
- `subagent tool write src/app.py --content "print('hi')"`
- `subagent tool edit src/app.py --find "hi" --replace "hello"`

Approvals queue:
- `subagent approval list`
- `subagent approval approve APPROVAL_ID --actor name --reason "..."`
- `subagent approval deny APPROVAL_ID --actor name --reason "..."`

## Quality gates
`subagent quality run` can execute:
- pytest gate
- coverage gate
- diff review gate
- secret scan gate

## Dashboard and realtime monitor
- Dashboard server: `subagent dashboard start`
- WebSocket monitor: `subagent monitor start`

## Testing and linting
```bash
pytest tests/ -v
pytest tests/ --cov=src --cov-report=html
black src/ tests/
flake8 src/ tests/
mypy src/
```

## Performance highlights (from tests/test_performance.py)
- Logging: ~0.007 ms per event
- Snapshot creation: ~4 ms
- Snapshot restore: ~0.05 ms
- Analytics queries: <1 ms average
- Throughput: ~95,000 events/sec

## Changelog (condensed)
Unreleased additions:
- Test telemetry emitted from `subagent quality run`.
- Approval-required events with risk scoring in tool proxy path.
- Approval queue persistence and CLI commands.
- Task state persistence in analytics DB and progress metrics.
- Adapter SDK with redaction/allowlist and Aider adapter.
- Dashboard server and realtime monitor commands.

0.1.0 (2025-11-12): core logging, snapshots, analytics, backup integration, and tests.

## Legacy and compatibility
- The project pivoted from a full agent control system to a neutral observability/governance layer.
- Legacy `.claude/` data roots are supported; `.subagent/` is the default.
- Previous control system phases are archived; current focus is the pivot roadmap above.
