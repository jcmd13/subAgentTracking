#!/usr/bin/env bash
set -euo pipefail

AGENT_USER="${AGENT_USER:-agent}"
REPO_DIR="${REPO_DIR:-/opt/agents/subAgentTracking}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMD_DIR="/etc/systemd/system"
ENV_DIR="/etc/subagent"
ENV_FILE="${ENV_DIR}/agent.env"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root to write systemd units and /etc/subagent/agent.env."
  exit 1
fi

if [ ! -d "${REPO_DIR}" ]; then
  echo "Repo dir not found: ${REPO_DIR}"
  exit 1
fi

install -d "${ENV_DIR}"

if [ ! -f "${ENV_FILE}" ]; then
  sed -e "s|/opt/agents/subAgentTracking|${REPO_DIR}|g" \
    "${SCRIPT_DIR}/agent.env.example" > "${ENV_FILE}"
  echo "Created ${ENV_FILE} (add API keys as needed)."
fi

render_unit() {
  sed -e "s|__REPO_DIR__|${REPO_DIR}|g" \
      -e "s|__AGENT_USER__|${AGENT_USER}|g" "$1" > "$2"
}

render_unit "${SCRIPT_DIR}/systemd/subagent-dashboard.service" \
  "${SYSTEMD_DIR}/subagent-dashboard.service"
render_unit "${SCRIPT_DIR}/systemd/subagent-monitor.service" \
  "${SYSTEMD_DIR}/subagent-monitor.service"
render_unit "${SCRIPT_DIR}/systemd/subagent-codex.service" \
  "${SYSTEMD_DIR}/subagent-codex.service"
render_unit "${SCRIPT_DIR}/systemd/subagent-claude-code.service" \
  "${SYSTEMD_DIR}/subagent-claude-code.service"

echo "Wrote unit files to ${SYSTEMD_DIR}."
echo "Next: systemctl daemon-reload"
echo "Enable dashboard/monitor: systemctl enable --now subagent-dashboard subagent-monitor"
echo "Enable Codex CLI: systemctl enable --now subagent-codex"
echo "Enable Claude Code CLI: systemctl enable --now subagent-claude-code"
