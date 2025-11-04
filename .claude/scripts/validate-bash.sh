#!/usr/bin/env bash

set -euo pipefail

# Read stdin
INPUT=$(cat || true)

# Simple pattern matching without jq dependency

# Extract command from JSON-like input if present
if [[ "$INPUT" =~ \"command\"[[:space:]]*:[[:space:]]*\"([^\"]+)\" ]]; then
    COMMAND="${BASH_REMATCH[1]}"
else
    # If no JSON pattern found, treat entire input as command
    COMMAND="$INPUT"
fi

# If command is empty, allow it
if [ -z "$COMMAND" ]; then
    exit 0
fi

# Define blocked patterns
BLOCKED_PATTERNS=(
    "node_modules"
    "\.env"
    "__pycache__"
    "\.git/"
    "dist/"
    "build/"
    "venv/"
)

# Check each pattern
for pattern in "${BLOCKED_PATTERNS[@]}"; do
    if echo "$COMMAND" | grep -qE "$pattern"; then
        echo "ERROR: Blocked directory pattern '$pattern' detected in command" >&2
        echo "Command: $COMMAND" >&2
        exit 2
    fi
done

# Allow the command
exit 0
