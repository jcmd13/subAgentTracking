# Product Requirements Document

## Original Request
<!-- VERBATIM_START -->
Evolve the dashboard UX to surface task status, session summaries, and
non-invasive alerts so developers can understand progress without noise.
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

### F001: Task Strip and Session Summaries
- **Status**: [ ] Not Started
- **Priority**: High
- **Description**: Add a top level task strip and start/end session summaries
  with the most important changes and risks.

#### User Stories

##### US001: See current task without scrolling
- **Status**: [ ] Not Started
- **As a**: developer
- **I want**: a task strip with stage and status
- **So that**: I can stay oriented during long runs

###### Acceptance Criteria
- AC001: [ ] Task strip shows task, stage, and ETA if available
- AC002: [ ] Task strip collapses to a minimal mode

##### US002: Receive concise session summaries
- **Status**: [ ] Not Started
- **As a**: developer
- **I want**: a summary at session start and end
- **So that**: I understand changes, tests, and risks quickly

###### Acceptance Criteria
- AC003: [ ] Summary includes changes, tests, cost, and open risks
- AC004: [ ] Summary available in dashboard and exportable as markdown

#### Tasks
- T001: [ ] Add task strip UI component
- T002: [ ] Add session summary card and export

### F002: Alerts and Risk Signals
- **Status**: [ ] Not Started
- **Priority**: High
- **Description**: Provide non-invasive alerts for destructive changes,
  quality degradation, and cost spikes.

#### User Stories

##### US003: See alerts only when needed
- **Status**: [ ] Not Started
- **As a**: developer
- **I want**: alerts that surface only on threshold events
- **So that**: I avoid dashboard noise

###### Acceptance Criteria
- AC005: [ ] Alerts drawer shows severity and recommended action
- AC006: [ ] Alerts collapse after acknowledgment

#### Tasks
- T003: [ ] Add alerts drawer and severity UI
- T004: [ ] Wire alerts to risk and test events

### F003: Focus Mode and Filters
- **Status**: [ ] Not Started
- **Priority**: Medium
- **Description**: Reduce clutter with a focus mode and stronger filtering.

#### User Stories

##### US004: Hide non-essential data
- **Status**: [ ] Not Started
- **As a**: developer
- **I want**: a focus mode with only task, tests, and cost
- **So that**: I can work without distraction

###### Acceptance Criteria
- AC007: [ ] Focus mode toggle persists between sessions
- AC008: [ ] Event stream supports severity and task filters

#### Tasks
- T005: [ ] Add focus mode toggle and persistence
- T006: [ ] Extend event stream filters

---

## Progress Summary
- **Features**: 0/3 (0%)
- **User Stories**: 0/4 (0%)
- **Acceptance Criteria**: 0/8 (0%)
- **Tasks**: 0/6 (0%)
