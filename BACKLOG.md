# Backlog

Tracking file for requests/ideas not fully implemented in the session they arrived.

## 2026-06-22 — Repo refresh / portfolio polish session

Context: local checkout was 62 commits behind `origin/master`; fast-forwarded to `b1977fc`. README fully rewritten as a portfolio-grade doc (balanced: recruiter-skimmable top, engineering depth below).

### Done this session
- [x] **README** rewritten as a portfolio piece; every metric measured (790 tests pass, 67% coverage).
- [x] **Added `LICENSE`** (MIT).
- [x] **Reconciled `.claude/CURRENT_STATUS.md`** — was "Ready to begin Phase 3" (Phase 3 is done); now accurate.
- [x] **Replaced `.claude/PROJECT_STATUS.md`** — was a 2,464-line self-contradictory template; now a concise accurate tracker.
- [x] **Removed stray artifacts** — `proxmox-jobs.sqlite3*` (unrelated Proxmox MCP files).
- [x] **Gitignored legacy `.claude/` runtime dirs** (`approvals/`, `observability/`, `requirements/`, `quality/`, `tasks/`, `hooks/`).
- [x] **Pinned `python_requires=">=3.10"`** in `setup.py` to match CI.
- [x] **Captured a live dashboard screenshot** (`docs/img/dashboard.png`) and embedded it in the README.
- [x] **Fixed 3 dashboard-path bugs** found while capturing the screenshot (see below).

### Dashboard bugs fixed (in `src/observability/realtime_monitor.py`)
The observability dashboard was broken against current dependencies; all three are now fixed and the suite still passes (790):
1. `_handle_client(self, websocket, path)` → `path` made optional. `websockets>=14` (resolved 15.0.1) calls the handler with only the connection, so every WS connection was failing with `TypeError: missing 'path'`.
2. `_send_event_to_client` referenced `event.metadata`, which the current `Event` dataclass doesn't have → events never broadcast. Now uses `getattr(..., {})` and also forwards `trace_id`/`session_id`.
3. `_snapshot_to_dict` called `asdict()` on a snapshot whose `events_by_type` is a `defaultdict` → `asdict` raised and all metrics broadcasts were silently swallowed. Now coerces to a plain dict first.

### Still open
- [ ] **Confirm license choice** — `LICENSE` is **MIT** (copyright "John Davis", 2026). Change to Apache-2.0 / other if preferred.
- [ ] **Fix bundled examples** — `examples/dashboard_example.py` (and likely siblings) use the stale event-bus API (`await event_bus.publish(...)`); `publish` is now sync (`publish_async` is the awaitable). The example crashes as written. Update examples to the current API, or add a regression test that imports/runs them.
- [ ] **(Optional) Pin `websockets`** — consider `websockets>=12,<16` or test against the installed major to avoid future handler-signature breaks.
