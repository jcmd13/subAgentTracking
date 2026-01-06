#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SESSION="${SESSION:-codex}"
CMD="${CODEX_CLI_CMD:-codex}"

if [ -n "${CODEX_CLI_ARGS:-}" ]; then
  CMD="${CMD} ${CODEX_CLI_ARGS}"
fi

exec "${SCRIPT_DIR}/tmux-session.sh" "${SESSION}" "${SCRIPT_DIR}/runner.sh ${CMD}"
