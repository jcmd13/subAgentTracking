#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [ -d "${ROOT_DIR}/venv/bin" ]; then
  export PATH="${ROOT_DIR}/venv/bin:${PATH}"
fi

export SUBAGENT_PROJECT_DIR="${SUBAGENT_PROJECT_DIR:-${ROOT_DIR}}"
export SUBAGENT_DATA_DIR="${SUBAGENT_DATA_DIR:-${ROOT_DIR}/.subagent}"

cd "${ROOT_DIR}"
exec "$@"
