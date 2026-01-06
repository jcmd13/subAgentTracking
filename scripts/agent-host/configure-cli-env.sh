#!/usr/bin/env bash
set -euo pipefail

AGENT_USER="${AGENT_USER:-agent}"
REPO_DIR="${REPO_DIR:-/opt/agents/subAgentTracking}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_DIR="/etc/subagent"
ENV_FILE="${ENV_DIR}/agent.env"
EXAMPLE_FILE="${SCRIPT_DIR}/agent.env.example"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root to update ${ENV_FILE}."
  exit 1
fi

install -d "${ENV_DIR}"

if [ ! -f "${ENV_FILE}" ]; then
  sed -e "s|/opt/agents/subAgentTracking|${REPO_DIR}|g" \
    "${EXAMPLE_FILE}" > "${ENV_FILE}"
fi

detect_cmd() {
  local name
  for name in "$@"; do
    if command -v "${name}" >/dev/null 2>&1; then
      command -v "${name}"
      return 0
    fi
  done
  return 1
}

quote_value() {
  if [ -z "${1:-}" ]; then
    echo ""
  else
    printf '%q' "$1"
  fi
}

set_kv() {
  local key="$1"
  local value="$2"
  if grep -q "^${key}=" "${ENV_FILE}"; then
    sed -i.bak "s|^${key}=.*|${key}=${value}|" "${ENV_FILE}"
  else
    echo "${key}=${value}" >> "${ENV_FILE}"
  fi
}

codex_cmd="${CODEX_CLI_CMD:-}"
if [ -z "${codex_cmd}" ]; then
  codex_cmd="$(detect_cmd codex codex-cli || true)"
fi
if [ -n "${codex_cmd}" ]; then
  set_kv "CODEX_CLI_CMD" "$(quote_value "${codex_cmd}")"
fi
if [ -n "${CODEX_CLI_ARGS:-}" ]; then
  set_kv "CODEX_CLI_ARGS" "$(quote_value "${CODEX_CLI_ARGS}")"
fi

claude_cmd="${CLAUDE_CODE_CMD:-}"
if [ -z "${claude_cmd}" ]; then
  claude_cmd="$(detect_cmd claude claude-code claude-code-cli || true)"
fi
if [ -n "${claude_cmd}" ]; then
  set_kv "CLAUDE_CODE_CMD" "$(quote_value "${claude_cmd}")"
fi
if [ -n "${CLAUDE_CODE_ARGS:-}" ]; then
  set_kv "CLAUDE_CODE_ARGS" "$(quote_value "${CLAUDE_CODE_ARGS}")"
fi

chown "${AGENT_USER}:${AGENT_USER}" "${ENV_FILE}"
echo "Updated ${ENV_FILE}."
