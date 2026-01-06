#!/usr/bin/env bash
set -euo pipefail

SESSION="${1:-subagent}"
shift || true

if [ "$#" -eq 0 ]; then
  echo "Usage: tmux-launch.sh <session> <command...>"
  exit 1
fi

CMD="$*"

if tmux has-session -t "${SESSION}" 2>/dev/null; then
  exit 0
fi

tmux new-session -d -s "${SESSION}" "${CMD}"
