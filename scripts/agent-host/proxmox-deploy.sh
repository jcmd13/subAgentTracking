#!/usr/bin/env bash
set -euo pipefail

CT_ID="${CT_ID:-}"
CT_CORES="${CT_CORES:-4}"
CT_MEMORY="${CT_MEMORY:-8192}"
CT_SWAP="${CT_SWAP:-1024}"
CT_DISK_TARGET_GB="${CT_DISK_TARGET_GB:-40}"
CT_DISK_GROW="${CT_DISK_GROW:-}"
CT_START="${CT_START:-1}"

REPO_URL="${REPO_URL:-https://github.com/jcmd13/subAgentTracking.git}"
WORKDIR="${WORKDIR:-/opt/agents}"
REPO_DIR="${REPO_DIR:-${WORKDIR}/subAgentTracking}"
AGENT_USER="${AGENT_USER:-agent}"

RUN_HELPER="${RUN_HELPER:-1}"
INSTALL_NODE="${INSTALL_NODE:-1}"
INSTALL_CLIS="${INSTALL_CLIS:-1}"
INSTALL_TAILSCALE="${INSTALL_TAILSCALE:-0}"
ENABLE_SERVICES="${ENABLE_SERVICES:-1}"
TAILSCALE_AUTHKEY="${TAILSCALE_AUTHKEY:-}"
TAILSCALE_HOSTNAME="${TAILSCALE_HOSTNAME:-subagent-host}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run on the Proxmox host as root."
  exit 1
fi

if [ -z "${CT_ID}" ]; then
  echo "Set CT_ID (container ID) before running."
  exit 1
fi

if ! command -v pct >/dev/null 2>&1; then
  echo "pct command not found. Run this on a Proxmox host."
  exit 1
fi

is_truthy() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
  esac
  return 1
}

resize_disk_if_needed() {
  if [ -n "${CT_DISK_GROW}" ]; then
    pct resize "${CT_ID}" rootfs "${CT_DISK_GROW}"
    return 0
  fi

  rootfs_line="$(pct config "${CT_ID}" | awk '/^rootfs:/ {print $0}')"
  size_field="$(echo "${rootfs_line}" | sed -n 's/.*size=\\([^,]*\\).*/\\1/p')"
  if [ -z "${size_field}" ]; then
    echo "Could not read rootfs size. Set CT_DISK_GROW if you need to resize."
    return 0
  fi

  size_unit="${size_field: -1}"
  size_value="${size_field%?}"
  current_mb=0
  if [ "${size_unit}" = "G" ] && [ -n "${size_value}" ]; then
    current_mb=$((size_value * 1024))
  elif [ "${size_unit}" = "M" ] && [ -n "${size_value}" ]; then
    current_mb=$((size_value))
  fi

  target_mb=$((CT_DISK_TARGET_GB * 1024))
  if [ "${current_mb}" -gt 0 ] && [ "${current_mb}" -lt "${target_mb}" ]; then
    delta_mb=$((target_mb - current_mb))
    if [ $((delta_mb % 1024)) -eq 0 ]; then
      pct resize "${CT_ID}" rootfs "+$((delta_mb / 1024))G"
    else
      pct resize "${CT_ID}" rootfs "+${delta_mb}M"
    fi
  else
    echo "Disk size looks >= ${CT_DISK_TARGET_GB}G or unknown. Skipping resize."
  fi
}

if is_truthy "${RUN_HELPER}"; then
  bash "${SCRIPT_DIR}/proxmox-ubuntu-helper.sh"
else
  if ! pct status "${CT_ID}" >/dev/null 2>&1; then
    echo "Container ${CT_ID} not found. Set RUN_HELPER=1 to create it."
    exit 1
  fi
  pct set "${CT_ID}" --cores "${CT_CORES}" --memory "${CT_MEMORY}" --swap "${CT_SWAP}"
  resize_disk_if_needed
  if [ "${CT_START}" = "1" ]; then
    pct start "${CT_ID}" || true
  fi
fi

echo "Bootstrapping container ${CT_ID}..."
pct exec "${CT_ID}" -- bash -lc "set -euo pipefail
apt-get update
apt-get install -y git curl ca-certificates
if [ ! -d '${REPO_DIR}' ]; then
  mkdir -p '${WORKDIR}'
  git clone '${REPO_URL}' '${REPO_DIR}'
fi
AGENT_USER='${AGENT_USER}' WORKDIR='${WORKDIR}' REPO_URL='${REPO_URL}' REPO_DIR='${REPO_DIR}' \
  bash '${REPO_DIR}/scripts/agent-host/bootstrap.sh'
"

if is_truthy "${INSTALL_NODE}"; then
  pct exec "${CT_ID}" -- bash -lc "set -euo pipefail
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs
"
fi

if is_truthy "${INSTALL_CLIS}"; then
  pct exec "${CT_ID}" -- bash -lc "set -euo pipefail
npm i -g @openai/codex @anthropic-ai/claude-code @google/gemini-cli
"
fi

if is_truthy "${INSTALL_TAILSCALE}"; then
  pct exec "${CT_ID}" -- bash -lc "set -euo pipefail
curl -fsSL https://tailscale.com/install.sh | sh
"
  if [ -n "${TAILSCALE_AUTHKEY}" ]; then
    pct exec "${CT_ID}" -- bash -lc "tailscale up --ssh --authkey '${TAILSCALE_AUTHKEY}' --hostname '${TAILSCALE_HOSTNAME}'"
  else
    echo "Run inside container: tailscale up --ssh --hostname ${TAILSCALE_HOSTNAME}"
  fi
fi

if is_truthy "${ENABLE_SERVICES}"; then
  pct exec "${CT_ID}" -- bash -lc "set -euo pipefail
cd '${REPO_DIR}'
AGENT_USER='${AGENT_USER}' REPO_DIR='${REPO_DIR}' bash scripts/agent-host/enable-services.sh
"
fi

echo "Deployment complete."
echo "Next: edit /etc/subagent/agent.env inside the container to add API keys."
