# Project Pivot Document - Observability and Governance Layer

Date: 2025-12-20
Status: Proposed and Approved
Owner: SubAgent Tracking Team

## Executive Summary

The project will pivot from a Claude Code specific tracking system to a neutral
observability and governance layer for AI coding workflows. This pivot is
supported by market signals from leading open-source AI coding tools and by
recurring user pain points observed in developer communities.

The new direction focuses on:
- Task lifecycle visibility and real time status.
- Human-in-the-loop approvals for risky changes.
- Test and quality telemetry surfaced at the right time.
- Adapter based integration with popular AI coding tools instead of building a
  competing agent runtime.

## Market Signals and User Problems

Observed open-source leaders include OpenHands, OpenInterpreter, AutoGen,
CrewAI, Aider, Continue, LangGraph, Semantic Kernel, SWE-agent, and
smol-ai/developer. These projects emphasize agent autonomy, repo context, and
IDE or CLI integration. They provide speed and capability but often lack
enterprise grade governance, repeatability, and reliable human checkpoints.

Common themes from developer discussions include:
- Cost anxiety and unpredictable spend.
- Context limits and the "85 percent problem" where progress stalls.
- Fear of destructive edits and regressions.
- Need for better test visibility and reliable change summaries.
- Demand for intuitive UX that is not invasive or cluttered.

## Why the Pivot Makes Sense

Our strongest assets are deep observability, recovery, and analytics. The
market has many agent runtimes but fewer tools that provide reliable,
non-invasive governance and visibility across different assistants. A neutral
layer is more defensible and easier for teams to adopt because it does not
replace their preferred AI tool.

## New Product Direction

We will build a neutral layer that:
- Emits standardized task lifecycle events across tools.
- Tracks approvals, risk scores, and quality checks.
- Streams real time updates with clear UX cues.
- Provides session summaries and progress checkpoints.
- Integrates via adapters with Aider, Continue, OpenHands, and Claude Code.

## Scope Changes

In scope now:
- Event lifecycle schema for tasks, tests, approvals, and risk alerts.
- Adapter SDK and built in adapters for top tools.
- Dashboard UX focused on task status, summary, and risk alerts.
- Human-in-loop gating and rollback prompts.

De-emphasized for now:
- Building a full agent runtime or model orchestration system.
- Deep provider API integration beyond adapter needs.

## Success Metrics

- Time to understand current task state: under 10 seconds.
- Risky changes always require explicit approval.
- Test results visible within 60 seconds of completion.
- Session summary delivered at session start and end.
- Adapter coverage for at least 3 popular tools.

## Risks and Mitigations

- Risk: UX overload from too many signals.
  Mitigation: Focus mode and progressive disclosure.

- Risk: Adapter complexity across tools.
  Mitigation: Common schema with minimal tool-specific translation.

- Risk: Slower delivery due to new PRDs.
  Mitigation: Implement quick wins early and dogfood during development.

