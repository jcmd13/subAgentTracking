#!/usr/bin/env bash
set -euo pipefail
target="$HOME/.claude/CLAUDE.md"
src="$(dirname "$0")/response-block.md"
mkdir -p "$(dirname "$target")"
touch "$target"
if grep -q '^## Response format' "$target"; then
  echo "Response format block already present in $target"
else
  printf '\n' >> "$target"
  cat "$src" >> "$target"
  echo "Appended response format block to $target"
fi
