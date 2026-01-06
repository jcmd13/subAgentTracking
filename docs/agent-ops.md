# Agent Ops Workflow

This playbook defines consistent, cross-platform workflows for human and agent
collaboration, with strong GitHub hygiene and safety guardrails.

## Principles
- README.md is the single source of truth for requirements and status.
- Runtime data stays in `.subagent/`; secrets stay out of git.
- Prefer reproducible workflows with explicit sessions, tasks, and tests.

## Cross-platform layouts
Local dev (Mac/Linux/WSL):
- Use `./venv/bin/` for CLI and tests.
- Keep `.subagent/` in the repo root.

Remote host (Proxmox + Linux):
- Use `/opt/agents/subAgentTracking` as the repo root.
- Expose dashboard/monitor over Tailscale only.
- Keep secrets in `/etc/subagent/agent.env`.

Mixed workflow (edit local, run remote):
- Edit via git push or a sync tool.
- Run tests on the remote host to keep environment parity.

## Standard workflow (human + agent)
1) Start a session:
   `subagent session-start --metadata owner=alice --metadata intent=refactor`
2) Add a task:
   `subagent task add "Implement approval hooks" -a "Blocks risky edits"`
3) Work the task and log agent invocations where applicable.
4) Run quality checks:
   `subagent quality run --test-suite default`
5) Export metrics for the record:
   `subagent metrics --scope session --export report.md`
6) End the session:
   `subagent session-end --status completed --note "PR #123"`

## Agent lifecycle (CLI)
- Spawn: `subagent agent spawn refactor-agent --reason "Handle migration"`
- List: `subagent agent list`
- Show: `subagent agent show <agent_id>`

## Permissions and approvals
- Check tool permission: `subagent tool check --tool read --path src/app.py`
- Simulate a request: `subagent tool simulate --tool write --path src/app.py`
- Review approvals: `subagent approval list`

## GitHub hygiene
- Branch per task: `task/<id>-short-description`
- Keep PRs small and test-backed.
- Fill out `.github/PULL_REQUEST_TEMPLATE.md`.
- Require CI before merge.

## Health checks
- `subagent status` for current session and file stats.
- `subagent logs --count 20` for recent events.
