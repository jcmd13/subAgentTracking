#!/usr/bin/env bash
set -euo pipefail

SESSION="${1:-subagent}"
shift || true

if [ "$#" -eq 0 ]; then
  CMD="bash"
else
  CMD="$*"
fi

if tmux has-session -t "${SESSION}" 2>/dev/null; then
  tmux attach -t "${SESSION}"
else
  tmux new-session -d -s "${SESSION}" "${CMD}"
  tmux attach -t "${SESSION}"
fi
