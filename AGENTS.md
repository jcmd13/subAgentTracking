# SubAgent Tracking System - Agent Guide

This repo uses `README.md` as the single source of truth for requirements and
project status. Operational hosting details live in `docs/agent-hosting.md`.

## Core expectations
- Keep requirements, roadmap, and status updates in `README.md` only.
- Use `.subagent/` for runtime data; do not commit credentials or local state.
- Prefer defaults; only change `.subagent/config.yaml` when explicitly required.
- Avoid asking humans to run setup commands unless they request it.

## Task and session hygiene
- Start/stop sessions with `subagent session-start` / `subagent session-end`.
- Track work with `subagent task add` and `subagent task complete`.
- Record risky operations with `subagent approval` flows when enabled.

## Testing
- Run `./venv/bin/python -m pytest tests/ -v` when behavior changes.
- Note any skipped tests or env constraints in the PR description.

## Long-running hosts
- Use `scripts/agent-host/` for bootstrap and systemd templates.
- Keep secrets in `/etc/subagent/agent.env` or environment variables.
- Use Tailscale instead of exposing public ports.
