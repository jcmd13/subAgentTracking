#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SESSION="${SESSION:-claude}"
CMD="${CLAUDE_CODE_CMD:-claude}"

if [ -n "${CLAUDE_CODE_ARGS:-}" ]; then
  CMD="${CMD} ${CLAUDE_CODE_ARGS}"
fi

exec "${SCRIPT_DIR}/tmux-session.sh" "${SESSION}" "${SCRIPT_DIR}/runner.sh ${CMD}"
