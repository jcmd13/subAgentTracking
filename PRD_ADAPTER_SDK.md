# Product Requirements Document

## Original Request
<!-- VERBATIM_START -->
Provide an adapter SDK so the observability layer can ingest events from
popular AI coding tools (Aider, Continue, OpenHands, Claude Code) without
replacing those tools.
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

### F001: Adapter SDK and Event Mapping
- **Status**: [ ] Not Started
- **Priority**: High
- **Description**: Provide a small SDK that maps tool specific events to the
  common event schema and streams them to the event bus.

#### User Stories

##### US001: Integrate a new tool quickly
- **Status**: [ ] Not Started
- **As a**: developer
- **I want**: a small adapter template with clear mapping rules
- **So that**: I can integrate any AI coding tool in under a day

###### Acceptance Criteria
- AC001: [ ] Adapter interface defined with map_event and emit
- AC002: [ ] Adapter supports sync and async emitters
- AC003: [ ] Documentation includes a minimal example

#### Tasks
- T001: [ ] Define adapter interface and registration
- T002: [ ] Provide mapping helpers and validation
- T003: [ ] Add adapter documentation and examples

### F002: Built-in Adapters for Top Tools
- **Status**: [ ] Not Started
- **Priority**: Medium
- **Description**: Provide built-in adapters for common tools to reduce
  integration friction.

#### User Stories

##### US002: Use existing tools without extra setup
- **Status**: [ ] Not Started
- **As a**: developer
- **I want**: built-in adapters for popular tools
- **So that**: I can start capturing events immediately

###### Acceptance Criteria
- AC004: [ ] Adapter for Aider
- AC005: [ ] Adapter for Continue
- AC006: [ ] Adapter for OpenHands or Claude Code

#### Tasks
- T004: [ ] Implement Aider adapter
- T005: [ ] Implement Continue adapter
- T006: [ ] Implement OpenHands or Claude Code adapter

### F003: Privacy and Redaction Controls
- **Status**: [ ] Not Started
- **Priority**: Medium
- **Description**: Allow redaction and field allowlists to prevent sensitive
  data from being logged.

#### User Stories

##### US003: Control what data is captured
- **Status**: [ ] Not Started
- **As a**: team lead
- **I want**: to redact or allowlist event fields
- **So that**: sensitive data is protected

###### Acceptance Criteria
- AC007: [ ] Redaction rules support paths and regex
- AC008: [ ] Allowlist option available per adapter

#### Tasks
- T007: [ ] Add redaction configuration
- T008: [ ] Apply redaction in adapter pipeline

---

## Progress Summary
- **Features**: 0/3 (0%)
- **User Stories**: 0/3 (0%)
- **Acceptance Criteria**: 0/8 (0%)
- **Tasks**: 0/8 (0%)
