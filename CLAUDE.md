# Claude Code CLI Notes

This project exposes an MCP server for Claude Code integration and uses
`.subagent/` for runtime state. Requirements and roadmap remain in `README.md`.

## MCP server
Start the MCP server from the repo root:
```bash
scripts/agent-host/runner.sh python -m subagent.mcp.server
```

Configure Claude Code CLI with an MCP server that runs:
- Command: `python`
- Args: `-m subagent.mcp.server`
- Working directory: repo root
Template configs live in `docs/mcp/`.

## Environment
Recommended env vars:
- `SUBAGENT_PROJECT_DIR` (repo root)
- `SUBAGENT_DATA_DIR` (default: `.subagent/`)
- `SUBAGENT_PROVIDER_LIVE=1` to allow live model calls

## Permissions and guardrails
Tool and path permissions live in `.subagent/config/permissions.yaml`.
Keep config files out of git and store secrets in `/etc/subagent/agent.env`.
