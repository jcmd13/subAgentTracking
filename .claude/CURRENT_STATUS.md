# SubAgent Tracking — Current Status

**Last updated**: 2026-06-22
**Branch**: master
**Latest commit**: `b1977fc` (Proxmox deploy tooling + docs)
**Version**: 0.1.0 — active development (dogfooded, not a 1.0 release)

> Single source of truth for requirements + roadmap is **`README.md`**. This file is a short, current status snapshot. Verified metrics below were measured on 2026-06-22, not inherited from older docs.

---

## Verified metrics (measured)

| Metric | Value | How measured |
|---|---|---|
| Tests | **790 passed, 3 skipped, 0 failed** | `pytest tests/` (12.9s) |
| Coverage | **67%** | `pytest tests/ --cov=src` |
| Source | ~70 modules, ~28k LOC prod / ~17k LOC tests | `find src -name '*.py'` |
| CI | green on push/PR (GitHub Actions, Python 3.10) | `.github/workflows/ci.yml` |

> ⚠️ Older docs (and a prior README) claimed ~85–90% coverage and "242+/387+ tests". Those were inflated or counted differently — the measured numbers above supersede them.

---

## What's built & verified

**Foundational layers (complete):**
- **Event-driven core** — event bus, activity logging (JSONL), snapshots, SQLite analytics, session handoff, cost tracking.
- **Orchestration** — agent lifecycle, complexity-scored model router + fallback, per-agent budgets, tool proxy.
- **Observability platform** — real-time WebSocket monitor, metrics aggregator, analytics + insight engines, fleet monitor, browser dashboard.
- **Governance** — tool/path/network permissions, risk-scored approvals store, quality gates (secret scan, diff review, command gate, test protection).
- **Integrations** — CLI (`subagent`), MCP server (7 tools), Adapter SDK + Aider adapter, multi-provider abstraction (Anthropic/Gemini/Ollama), Proxmox + systemd deployment.

## Roadmap (current pivot)

The project pivoted from a "control system" to a **neutral observability / governance / orchestration layer**. Active product phases:

| Phase | Focus | Status |
|---|---|---|
| 0 | Quick wins & dogfood (task lifecycle, session summaries, test telemetry) | ✅ Done |
| 1 | Task state + progress metrics | 🟢 Mostly done |
| 2 | Adapter SDK MVP (interface, redaction, pilot adapter) | 🟡 In progress |
| 3 | Approvals + risk-scoring UX (queue, blocking hooks, alert UX) | 🟡 In progress |
| 4 | Dashboard UX polish + focus mode/filters | 🔵 Planned |
| 5 | Release + adoption (guided setup, second adapter) | 🔵 Planned |

## Known open items
- Approval UX calibration (avoid false blocks / noise).
- End-to-end MCP smoke test with a live client.
- Live provider validation (credentials + opt-in).
- A few non-blocking TODOs in `hooks_manager.py`, `activity_logger_compat.py`, `analytics_db_subscriber.py`, `snapshot_manager_subscriber.py`.

See `BACKLOG.md` for housekeeping items.
