#!/usr/bin/env bash
set -euo pipefail

INTERACTIVE="${INTERACTIVE:-1}"
CT_ID_DEFAULT="${CT_ID_DEFAULT:-120}"
CT_ID="${CT_ID:-}"
CT_CORES="${CT_CORES:-4}"
CT_MEMORY="${CT_MEMORY:-8192}"
CT_SWAP="${CT_SWAP:-1024}"
CT_DISK_GROW="${CT_DISK_GROW:-}"
CT_DISK_TARGET_GB="${CT_DISK_TARGET_GB:-40}"
CT_START="${CT_START:-1}"

is_truthy() {
  case "${1:-}" in
    1|true|TRUE|yes|YES|on|ON) return 0 ;;
  esac
  return 1
}

if [ "$(id -u)" -ne 0 ]; then
  echo "Run on the Proxmox host as root."
  exit 1
fi

if [ -z "${CT_ID}" ]; then
  if is_truthy "${INTERACTIVE}" && [ -t 0 ]; then
    read -r -p "Enter CT_ID (container ID) [${CT_ID_DEFAULT}]: " input_ct_id
    CT_ID="${input_ct_id:-${CT_ID_DEFAULT}}"
  else
    CT_ID="${CT_ID_DEFAULT}"
  fi
fi

if [ -z "${CT_ID}" ]; then
  echo "Set CT_ID (container ID) before running."
  exit 1
fi

if ! command -v pct >/dev/null 2>&1; then
  echo "pct command not found. Run this on a Proxmox host."
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl not found. Install curl on the Proxmox host."
  exit 1
fi

echo "Running Proxmox VE Helper (Ubuntu LXC)."
echo "During prompts, set CT ID to: ${CT_ID}"
echo "Recommended resources: ${CT_CORES} cores, ${CT_MEMORY} MB RAM, ${CT_SWAP} MB swap, 40G disk."
echo "Proceeding to run the helper script..."

bash -c "$(curl -fsSL https://raw.githubusercontent.com/community-scripts/ProxmoxVE/main/ct/ubuntu.sh)"

if ! pct status "${CT_ID}" >/dev/null 2>&1; then
  echo "Container ${CT_ID} not found after helper script. Verify the CT ID."
  exit 1
fi

pct set "${CT_ID}" --cores "${CT_CORES}" --memory "${CT_MEMORY}" --swap "${CT_SWAP}"

if [ -n "${CT_DISK_GROW}" ]; then
  pct resize "${CT_ID}" rootfs "${CT_DISK_GROW}"
else
  rootfs_line="$(pct config "${CT_ID}" | awk '/^rootfs:/ {print $0}')"
  size_field="$(echo "${rootfs_line}" | sed -n 's/.*size=\\([^,]*\\).*/\\1/p')"
  if [ -n "${size_field}" ]; then
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
  else
    echo "Could not read rootfs size. Set CT_DISK_GROW if you need to resize."
  fi
fi

if [ "${CT_START}" = "1" ]; then
  pct start "${CT_ID}" || true
fi

echo "LXC ${CT_ID} configured. Next: pct exec ${CT_ID} -- bash -lc '<bootstrap>'"
