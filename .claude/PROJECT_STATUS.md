# SubAgent Tracking System — Project Status

**Version**: 0.1.0 (active development)
**Last updated**: 2026-06-22
**Single source of truth for requirements & roadmap**: `README.md`
**Human-facing status snapshot**: `.claude/CURRENT_STATUS.md`

> This file is the structured status tracker (used by the project-manager agent). It was rewritten on 2026-06-22 to replace an obsolete, internally-contradictory task template. Metrics are measured, not inherited.

---

## At a glance

| Metric | Value |
|---|---|
| Tests | 790 passed / 3 skipped / 0 failed (`pytest tests/`) |
| Coverage | 67% (`--cov=src`) |
| Source | ~70 modules · ~28k LOC prod · ~17k LOC tests |
| CI | GitHub Actions, Python 3.10, on push/PR |

## Foundational build phases (complete)

These shipped and are covered by the test suite. They are the substrate the product roadmap builds on.

| Layer | Modules | Status |
|---|---|---|
| Event-driven core | `src/core/` — event bus, activity logger, snapshots, analytics DB, cost tracker, session manager, backup | ✅ Complete |
| Orchestration | `src/orchestration/` — agent lifecycle, model router + fallback, budgets, permissions, tool proxy, test protection | ✅ Complete |
| Observability | `src/observability/` — realtime monitor, metrics aggregator, analytics + insight engines, fleet monitor, dashboard | ✅ Complete |
| Interfaces | `src/subagent_cli/` (CLI), `src/subagent/mcp/` (MCP server, 7 tools), `src/adapters/` (Adapter SDK + Aider) | ✅ Complete |

## Product roadmap (current pivot)

Reframed from a "control system" to a neutral observability / governance / orchestration layer.

| Phase | Focus | Status | Notes |
|---|---|---|---|
| 0 | Quick wins & dogfood | ✅ Done | Task lifecycle events, session summaries, task strip, test telemetry |
| 1 | Task state + metrics | 🟢 Mostly done | Task state persisted in analytics DB; progress metrics shown |
| 2 | Adapter SDK MVP | 🟡 In progress | Interface + redaction/allowlist + Aider adapter done; 2nd adapter pending |
| 3 | Approvals + risk-scoring UX | 🟡 In progress | Store + events done; alert UX + blocking hooks pending |
| 4 | Dashboard UX polish + focus mode | 🔵 Planned | Alerts drawer, severity/task filters, export |
| 5 | Release + adoption | 🔵 Planned | Guided setup, second adapter |

## Open / blocked items

- Approval UX calibration (threshold tuning to avoid false blocks/noise).
- End-to-end MCP smoke test against a live client.
- Live provider validation (requires credentials + `SUBAGENT_PROVIDER_LIVE=1`).
- Non-blocking TODOs: `AGENT_BLOCKED` emit in `hooks_manager.py`; session duration/tokens in `activity_logger_compat.py`; success-from-exit in `analytics_db_subscriber.py`; snapshot size bytes in `snapshot_manager_subscriber.py`.

## Housekeeping
Tracked in `BACKLOG.md` (license confirmation, stray-artifact cleanup, runtime-dir gitignore, optional dashboard screenshot, `python_requires` pin).
