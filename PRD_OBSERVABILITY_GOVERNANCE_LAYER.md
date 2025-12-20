# Product Requirements Document

## Original Request
<!-- VERBATIM_START -->
Build a neutral observability and governance layer for AI coding workflows that
provides task lifecycle state, human approvals for risky changes, and test
telemetry, with minimal disruption to the developer's flow.
<!-- VERBATIM_END -->

## Metadata
- **Created**: 2025-12-20T06:29:37Z
- **Last Updated**: 2025-12-20T06:29:37Z
- **Session**: session_20251220_062937
- **Status**: In Progress
- **Project**: SubAgent Tracking System
- **Author**: SubAgent Team

---

## Features

### F001: Task Lifecycle and State Model
- **Status**: [ ] Not Started
- **Priority**: High
- **Description**: Emit and persist task lifecycle events so users can see the
  current task, stage, and progress with clear transitions.

#### User Stories

##### US001: See current task stage
- **Status**: [ ] Not Started
- **As a**: developer
- **I want**: to see the current task and its stage at a glance
- **So that**: I can tell what the AI is doing without reading logs

###### Acceptance Criteria
- AC001: [ ] Task events exist for started, stage_changed, and completed
- AC002: [ ] Event payloads include task_id, stage, and summary
- AC003: [ ] Task state is persisted in analytics DB

##### US002: Track project progress
- **Status**: [ ] Not Started
- **As a**: project owner
- **I want**: a percent complete estimate per task and project
- **So that**: I can plan and adjust scope

###### Acceptance Criteria
- AC004: [ ] Task progress stored and updated on stage changes
- AC005: [ ] Dashboard shows percent complete for active tasks

#### Tasks
- T001: [ ] Add task lifecycle event types and schemas
- T002: [ ] Update metrics aggregator and analytics DB ingestion
- T003: [ ] Add task state model and persistence

### F002: Human-In-Loop Approvals and Risk Scoring
- **Status**: [ ] Not Started
- **Priority**: High
- **Description**: Gate risky actions behind explicit approvals with clear
  alerts and rollback guidance.

#### User Stories

##### US003: Require approval for risky changes
- **Status**: [ ] Not Started
- **As a**: developer
- **I want**: to approve risky actions before they happen
- **So that**: I can prevent destructive or unsafe changes

###### Acceptance Criteria
- AC006: [ ] Risk scoring is computed for file deletions or large diffs
- AC007: [ ] Approval required event is emitted when threshold exceeded
- AC008: [ ] Hooks can block action until approval is granted

#### Tasks
- T004: [ ] Define risk score heuristics
- T005: [ ] Add approval events and hooks integration
- T006: [ ] Add rollback prompt and guidance event

### F003: Test Telemetry and Quality Signals
- **Status**: [ ] Not Started
- **Priority**: Medium
- **Description**: Capture test runs and quality signals and surface results
  at the right time.

#### User Stories

##### US004: See test status in real time
- **Status**: [ ] Not Started
- **As a**: developer
- **I want**: to see test start, progress, and results in the dashboard
- **So that**: I can trust the changes

###### Acceptance Criteria
- AC009: [ ] Test run started and completed events exist
- AC010: [ ] Test results include pass/fail and duration
- AC011: [ ] Dashboard shows last test status for current task

#### Tasks
- T007: [ ] Add test event types and schema
- T008: [ ] Add test telemetry to dashboard and metrics

---

## Progress Summary
- **Features**: 0/3 (0%)
- **User Stories**: 0/4 (0%)
- **Acceptance Criteria**: 0/11 (0%)
- **Tasks**: 0/8 (0%)
