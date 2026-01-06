#!/usr/bin/env bash
set -euo pipefail

AGENT_USER="${AGENT_USER:-agent}"
REPO_DIR="${REPO_DIR:-/opt/agents/subAgentTracking}"
ENABLE_CODEX="${ENABLE_CODEX:-1}"
ENABLE_CLAUDE="${ENABLE_CLAUDE:-1}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root to manage systemd services."
  exit 1
fi

is_truthy() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
  esac
  return 1
}

AGENT_USER="${AGENT_USER}" REPO_DIR="${REPO_DIR}" \
  bash "${SCRIPT_DIR}/install-systemd.sh"

AGENT_USER="${AGENT_USER}" REPO_DIR="${REPO_DIR}" \
  bash "${SCRIPT_DIR}/configure-cli-env.sh"

systemctl daemon-reload
systemctl enable --now subagent-dashboard
systemctl enable --now subagent-monitor

if is_truthy "${ENABLE_CODEX}"; then
  systemctl enable --now subagent-codex
fi

if is_truthy "${ENABLE_CLAUDE}"; then
  systemctl enable --now subagent-claude-code
fi

echo "Services enabled."
