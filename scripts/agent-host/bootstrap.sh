#!/usr/bin/env bash
set -euo pipefail

AGENT_USER="${AGENT_USER:-agent}"
WORKDIR="${WORKDIR:-/opt/agents}"
REPO_URL="${REPO_URL:-https://github.com/jcmd13/subAgentTracking.git}"
REPO_DIR="${REPO_DIR:-${WORKDIR}/subAgentTracking}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root to install packages and create the agent user."
  exit 1
fi

apt-get update
apt-get install -y git python3 python3-venv python3-pip tmux direnv

if ! id -u "${AGENT_USER}" >/dev/null 2>&1; then
  useradd -m -s /bin/bash "${AGENT_USER}"
fi

install -d -o "${AGENT_USER}" -g "${AGENT_USER}" "${WORKDIR}"

if command -v runuser >/dev/null 2>&1; then
  runuser -u "${AGENT_USER}" -- bash -lc "
    set -euo pipefail
    cd '${WORKDIR}'
    if [ ! -d '${REPO_DIR}' ]; then
      git clone '${REPO_URL}' '${REPO_DIR}'
    fi
    cd '${REPO_DIR}'
    ${PYTHON_BIN} -m venv venv
    ./venv/bin/pip install -r requirements.txt
    ./venv/bin/pip install -e .
    ./venv/bin/subagent init
  "
else
  su - "${AGENT_USER}" -c "
    set -euo pipefail
    cd '${WORKDIR}'
    if [ ! -d '${REPO_DIR}' ]; then
      git clone '${REPO_URL}' '${REPO_DIR}'
    fi
    cd '${REPO_DIR}'
    ${PYTHON_BIN} -m venv venv
    ./venv/bin/pip install -r requirements.txt
    ./venv/bin/pip install -e .
    ./venv/bin/subagent init
  "
fi
