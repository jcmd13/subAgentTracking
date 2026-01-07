#!/usr/bin/env bash
set -euo pipefail

INTERACTIVE="${INTERACTIVE:-0}"
CT_ID_DEFAULT="${CT_ID_DEFAULT:-120}"
CT_ID="${CT_ID:-}"
CT_CORES="${CT_CORES:-4}"
CT_MEMORY="${CT_MEMORY:-8192}"
CT_SWAP="${CT_SWAP:-1024}"
CT_DISK_TARGET_GB="${CT_DISK_TARGET_GB:-40}"
CT_DISK_GROW="${CT_DISK_GROW:-}"
CT_START="${CT_START:-1}"
CT_HOSTNAME="${CT_HOSTNAME:-subagent}"
CT_TEMPLATE_STORAGE="${CT_TEMPLATE_STORAGE:-}"
CT_TEMPLATE="${CT_TEMPLATE:-}"
CT_ROOTFS_STORAGE="${CT_ROOTFS_STORAGE:-}"
CT_ROOTFS_SIZE="${CT_ROOTFS_SIZE:-}"
CT_BRIDGE="${CT_BRIDGE:-vmbr0}"
CT_IP="${CT_IP:-dhcp}"
CT_GATEWAY="${CT_GATEWAY:-}"
CT_OSTYPE="${CT_OSTYPE:-}"

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
HELPER_URL="${HELPER_URL:-https://raw.githubusercontent.com/jcmd13/subAgentTracking/master/scripts/agent-host/proxmox-ubuntu-helper.sh}"
LXC_URL="${LXC_URL:-https://raw.githubusercontent.com/jcmd13/subAgentTracking/master/scripts/agent-host/proxmox-lxc.sh}"

SCRIPT_SOURCE="${BASH_SOURCE[0]:-}"
if [ -n "${SCRIPT_SOURCE}" ] && [ -f "${SCRIPT_SOURCE}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${SCRIPT_SOURCE}")" && pwd)"
else
  SCRIPT_DIR="$(pwd)"
fi
HELPER_PATH="${SCRIPT_DIR}/proxmox-ubuntu-helper.sh"
LXC_PATH="${SCRIPT_DIR}/proxmox-lxc.sh"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run on the Proxmox host as root."
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

normalize_rootfs_size() {
  local size="${1:-}"
  local mb=0
  local gb=0

  if [ -z "${size}" ]; then
    echo ""
    return 0
  fi

  if echo "${size}" | grep -Eq '^[0-9]+[Gg]$'; then
    echo "${size%[Gg]}"
    return 0
  fi

  if echo "${size}" | grep -Eq '^[0-9]+[Mm]$'; then
    mb="${size%[Mm]}"
    gb=$(( (mb + 1023) / 1024 ))
    if [ "${gb}" -lt 1 ]; then
      gb=1
    fi
    echo "${gb}"
    return 0
  fi

  if echo "${size}" | grep -Eq '^[0-9]+$'; then
    echo "${size}"
    return 0
  fi

  echo "CT_ROOTFS_SIZE must be an integer GiB value (example: 40 or 40G)." >&2
  exit 1
}

pick_available_ct_id() {
  local base="${CT_ID_DEFAULT}"
  local max="${CT_ID_MAX:-999}"
  local id

  for id in $(seq "${base}" "${max}"); do
    if ! pct status "${id}" >/dev/null 2>&1; then
      CT_ID="${id}"
      return 0
    fi
  done

  echo "No available CT_ID found in range ${base}-${max}."
  exit 1
}

prepare_ct_id() {
  if [ -z "${CT_ID}" ]; then
    if is_truthy "${RUN_HELPER}"; then
      if is_truthy "${INTERACTIVE}"; then
        pick_available_ct_id
        read -r -p "Enter CT_ID (container ID) [${CT_ID}]: " input_ct_id
        if [ -n "${input_ct_id}" ]; then
          CT_ID="${input_ct_id}"
        fi
      else
        pick_available_ct_id
      fi
    else
      if is_truthy "${INTERACTIVE}"; then
        read -r -p "Enter existing CT_ID (container ID): " CT_ID
      fi
    fi
  fi

  if [ -z "${CT_ID}" ]; then
    echo "Set CT_ID (container ID) before running."
    exit 1
  fi

  if is_truthy "${RUN_HELPER}" && pct status "${CT_ID}" >/dev/null 2>&1; then
    echo "Container ${CT_ID} already exists. Set RUN_HELPER=0 to reuse it."
    exit 1
  fi
}

detect_storage() {
  local content="${1}"
  local preferred="${2:-}"
  local storage=""

  if command -v pvesm >/dev/null 2>&1; then
    if [ -n "${preferred}" ] && pvesm status -content "${content}" | awk 'NR>1 {print $1}' | grep -qx "${preferred}"; then
      storage="${preferred}"
    else
      storage="$(pvesm status -content "${content}" | awk 'NR>1 {print $1; exit}')"
    fi
  fi

  echo "${storage}"
}

resolve_template() {
  if [ -n "${CT_TEMPLATE}" ]; then
    return
  fi

  if command -v pveam >/dev/null 2>&1; then
    CT_TEMPLATE="$(pveam available 2>/dev/null | awk '/ubuntu-22.04-standard/ {print $2; exit}')"
    if [ -z "${CT_TEMPLATE}" ]; then
      CT_TEMPLATE="$(pveam available 2>/dev/null | awk '/debian-12-standard/ {print $2; exit}')"
    fi
  fi

  if [ -z "${CT_TEMPLATE}" ]; then
    CT_TEMPLATE="ubuntu-22.04-standard_22.04-1_amd64.tar.zst"
  fi
}

prepare_lxc_defaults() {
  if [ -z "${CT_TEMPLATE_STORAGE}" ]; then
    CT_TEMPLATE_STORAGE="$(detect_storage vztmpl local)"
    CT_TEMPLATE_STORAGE="${CT_TEMPLATE_STORAGE:-local}"
  fi

  if [ -z "${CT_ROOTFS_STORAGE}" ]; then
    CT_ROOTFS_STORAGE="$(detect_storage rootdir local-lvm)"
    CT_ROOTFS_STORAGE="${CT_ROOTFS_STORAGE:-local-lvm}"
  fi

  if [ -z "${CT_ROOTFS_SIZE}" ]; then
    CT_ROOTFS_SIZE="${CT_DISK_TARGET_GB}"
  fi
  CT_ROOTFS_SIZE="$(normalize_rootfs_size "${CT_ROOTFS_SIZE}")"

  resolve_template

  if [ -z "${CT_OSTYPE}" ]; then
    if echo "${CT_TEMPLATE}" | grep -qi "ubuntu"; then
      CT_OSTYPE="ubuntu"
    elif echo "${CT_TEMPLATE}" | grep -qi "debian"; then
      CT_OSTYPE="debian"
    else
      CT_OSTYPE="ubuntu"
    fi
  fi
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

run_lxc() {
  prepare_lxc_defaults

  if [ -f "${LXC_PATH}" ]; then
    CT_ID="${CT_ID}" CT_HOSTNAME="${CT_HOSTNAME}" CT_TEMPLATE_STORAGE="${CT_TEMPLATE_STORAGE}" \
      CT_TEMPLATE="${CT_TEMPLATE}" CT_ROOTFS_STORAGE="${CT_ROOTFS_STORAGE}" CT_ROOTFS_SIZE="${CT_ROOTFS_SIZE}" \
      CT_MEMORY="${CT_MEMORY}" CT_SWAP="${CT_SWAP}" CT_CORES="${CT_CORES}" CT_BRIDGE="${CT_BRIDGE}" \
      CT_IP="${CT_IP}" CT_GATEWAY="${CT_GATEWAY}" CT_START="${CT_START}" CT_OSTYPE="${CT_OSTYPE}" \
      bash "${LXC_PATH}"
    return 0
  fi

  if ! command -v curl >/dev/null 2>&1; then
    echo "curl not found and LXC script is missing. Install curl or run from a cloned repo."
    exit 1
  fi

  tmp_dir="$(mktemp -d)"
  curl -fsSL "${LXC_URL}" -o "${tmp_dir}/proxmox-lxc.sh"
  CT_ID="${CT_ID}" CT_HOSTNAME="${CT_HOSTNAME}" CT_TEMPLATE_STORAGE="${CT_TEMPLATE_STORAGE}" \
    CT_TEMPLATE="${CT_TEMPLATE}" CT_ROOTFS_STORAGE="${CT_ROOTFS_STORAGE}" CT_ROOTFS_SIZE="${CT_ROOTFS_SIZE}" \
    CT_MEMORY="${CT_MEMORY}" CT_SWAP="${CT_SWAP}" CT_CORES="${CT_CORES}" CT_BRIDGE="${CT_BRIDGE}" \
    CT_IP="${CT_IP}" CT_GATEWAY="${CT_GATEWAY}" CT_START="${CT_START}" CT_OSTYPE="${CT_OSTYPE}" \
    bash "${tmp_dir}/proxmox-lxc.sh"
  rm -rf "${tmp_dir}"
}

run_helper() {
  if [ -f "${HELPER_PATH}" ]; then
    INTERACTIVE="${INTERACTIVE}" CT_ID_DEFAULT="${CT_ID_DEFAULT}" CT_ID="${CT_ID}" CT_CORES="${CT_CORES}" \
      CT_MEMORY="${CT_MEMORY}" CT_SWAP="${CT_SWAP}" CT_DISK_GROW="${CT_DISK_GROW}" \
      CT_DISK_TARGET_GB="${CT_DISK_TARGET_GB}" CT_START="${CT_START}" bash "${HELPER_PATH}"
    return 0
  fi

  if ! command -v curl >/dev/null 2>&1; then
    echo "curl not found and helper script is missing. Install curl or run from a cloned repo."
    exit 1
  fi

  tmp_dir="$(mktemp -d)"
  curl -fsSL "${HELPER_URL}" -o "${tmp_dir}/proxmox-ubuntu-helper.sh"
  INTERACTIVE="${INTERACTIVE}" CT_ID_DEFAULT="${CT_ID_DEFAULT}" CT_ID="${CT_ID}" CT_CORES="${CT_CORES}" \
    CT_MEMORY="${CT_MEMORY}" CT_SWAP="${CT_SWAP}" CT_DISK_GROW="${CT_DISK_GROW}" \
    CT_DISK_TARGET_GB="${CT_DISK_TARGET_GB}" CT_START="${CT_START}" bash "${tmp_dir}/proxmox-ubuntu-helper.sh"
  rm -rf "${tmp_dir}"
}

prepare_ct_id

if is_truthy "${RUN_HELPER}"; then
  if is_truthy "${INTERACTIVE}"; then
    run_helper
  else
    run_lxc
  fi
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
