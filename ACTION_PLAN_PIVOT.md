# Action Plan - Observability and Governance Layer Pivot

Date: 2025-12-20

## Purpose

Deliver a neutral observability and governance layer for AI coding workflows
with task visibility, approvals, and test telemetry, while keeping UX
non-invasive and easy to adopt.

## PRD Map

- PRD_OBSERVABILITY_GOVERNANCE_LAYER.md
  - F001 Task Lifecycle and State Model
  - F002 Human-In-Loop Approvals and Risk Scoring
  - F003 Test Telemetry and Quality Signals

- PRD_ADAPTER_SDK.md
  - F001 Adapter SDK and Event Mapping
  - F002 Built-in Adapters for Top Tools
  - F003 Privacy and Redaction Controls

- PRD_DASHBOARD_UX.md
  - F001 Task Strip and Session Summaries
  - F002 Alerts and Risk Signals
  - F003 Focus Mode and Filters

## Phase Plan

### Phase 0: Quick Wins and Dogfood Setup (1 to 2 weeks)
Goals:
- Start using the system during development.
- Deliver immediate visibility improvements.

Scope:
- Add task lifecycle event types and minimal payloads (PRD_OBSERVABILITY_GOVERNANCE_LAYER F001).
- Add basic session summary generation (PRD_DASHBOARD_UX F001).
- Add a minimal task strip UI and show current task and stage.
- Add test telemetry events without gating logic (PRD_OBSERVABILITY_GOVERNANCE_LAYER F003).

Deliverables:
- Task lifecycle events emitted by manual hooks.
- Dashboard shows task strip and last test status.
- Session summary generated at start and end of dev session.

### Phase 1: Core Task State and Metrics (2 weeks)
Goals:
- Persist task state and progress in analytics DB.
- Provide reliable progress metrics.

Scope:
- Task state model and DB persistence (F001).
- Update metrics aggregation for tasks and tests.
- Add API endpoints or event payloads for dashboard updates.

### Phase 2: Adapter SDK MVP (2 to 3 weeks)
Goals:
- Enable external tools to emit events with minimal friction.

Scope:
- Adapter interface, validation, and documentation (PRD_ADAPTER_SDK F001).
- Redaction and allowlist controls (F003).
- One pilot adapter (Aider or Continue) with a working demo (F002).

### Phase 3: Human-In-Loop Approvals (2 weeks)
Goals:
- Add approvals and risk scoring to prevent destructive actions.

Scope:
- Risk heuristics and approval required events (PRD_OBSERVABILITY_GOVERNANCE_LAYER F002).
- Hook integration to block risky actions until approved.
- Alert UX and guidance prompts (PRD_DASHBOARD_UX F002).

### Phase 4: UX Polish and Focus Mode (2 weeks)
Goals:
- Make the dashboard feel intuitive and not noisy.

Scope:
- Focus mode and advanced filters (PRD_DASHBOARD_UX F003).
- Summary export and session timeline improvements.
- UX tuning based on dogfood feedback.

### Phase 5: Release and Adoption (ongoing)
Goals:
- Ship a stable, well-documented release with example integrations.

Scope:
- Add a second adapter.
- Publish guided setup and quickstart.
- Collect feedback and iterate on UX.

## Immediate Features to Implement Now

These can be implemented early and used to accelerate development:
- Task lifecycle events and a manual CLI or hook to emit them.
- Basic session summary generator that outputs markdown.
- Task strip in dashboard with stage and status.
- Test telemetry events captured from local test runs.

## Dogfooding Plan

- Use the task lifecycle events for all new work.
- Require a summary at session start and end.
- Track costs and test outcomes during development.
- Log approval events for any file deletions or large diffs.

## Testing Strategy

- Unit tests for event schemas and adapter mappings.
- Integration tests for WebSocket stream and dashboard updates.
- Snapshot tests for session summary outputs.

## Decision Points

- After Phase 1: confirm if progress metrics are useful or too noisy.
- After Phase 2: decide whether to expand adapters or deepen one tool.
- After Phase 3: validate approvals UX with real users.

