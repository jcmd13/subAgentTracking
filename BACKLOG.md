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

### Fixed bundled examples (2026-06-22, follow-up session)
All six `examples/*.py` were drifted/broken against the current API; all now run clean and are guarded by `tests/test_examples_smoke.py` (in the CI gate):
- `dashboard_example.py`, `full_observability_example.py`: `await event_bus.publish(...)` → `publish_async` (publish is sync now). `full_observability_example.py` also now creates `.subagent/` before writing its report (was `FileNotFoundError`).
- `custom_events.py`: `with log_tool_usage(...)` → direct call (no longer a context manager); invalid `FileOperationType` values (`write`/`edit` → `create`/`modify`); added required `rationale` to `log_decision`; `status="in_progress"` → valid `AgentStatus` (`started`); corrected `tool_type=`/`status=`/`lines_affected=` kwargs.
- `analytics_queries.py`: initialize the analytics schema first so a fresh DB returns empty results instead of `no such table`.
- `basic_usage.py`, `mcp_smoke_test.py`: already current.

### CI stabilization (merged, PR #2)
- [x] Separated hardware-sensitive benchmarks from the CI correctness gate via a `performance` marker (`tests/conftest.py`); gate runs `-m "not performance"`, benchmarks run non-blocking.

### Still open
- [ ] **Confirm license choice** — `LICENSE` is **MIT** (copyright "John Davis", 2026). Change to Apache-2.0 / other if preferred. (Decision only; no code action.)
- [ ] **(Optional) Pin `websockets`** — not strictly needed now: `realtime_monitor._handle_client` was made signature-robust, so 14/15.x work. A defensive upper bound (`websockets<16`) could still guard against a future major; left unpinned to avoid install conflicts.
