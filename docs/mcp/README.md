# MCP Config Templates

This folder contains templates for clients that support MCP servers using a
`mcpServers` JSON configuration. Adjust paths and environment values as needed.

Templates:
- `claude-code.json`: Claude Code CLI-style configuration.
- `local-dev.json`: Local dev template that uses a repo-relative runner.

Notes:
- The MCP server is a stdio JSON-RPC process; clients typically spawn it.
- Use `scripts/agent-host/runner.sh` when you want the repo venv on PATH.
