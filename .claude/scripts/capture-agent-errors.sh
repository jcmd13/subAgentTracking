#!/bin/bash

# PostToolUse hook - Capture agent errors for RCA

set -euo pipefail

INPUT=$(cat)
TOOL=$(echo "$INPUT" | jq -r '.tool')

# Only trigger on Task tool (agent invocations)
if [[ "$TOOL" != "Task" ]]; then
    exit 0
fi

AGENT=$(echo "$INPUT" | jq -r '.params.subagent_type // "unknown"')
RESULT=$(echo "$INPUT" | jq -r '.result // ""')

# Check for error indicators
if echo "$RESULT" | grep -iE "error|failed|exception|traceback" > /dev/null; then
    # Extract error context
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # Log to agent_errors.jsonl
    mkdir -p .claude/logs
    cat >> .claude/logs/agent_errors.jsonl <<EOF
{
  "timestamp": "$TIMESTAMP",
  "agent": "$AGENT",
  "status": "failed",
  "output_sample": "$(echo "$RESULT" | head -c 500 | jq -Rs .)"
}
EOF
    
    echo "⚠️  Agent error logged to .claude/logs/agent_errors.jsonl"
fi

exit 0
