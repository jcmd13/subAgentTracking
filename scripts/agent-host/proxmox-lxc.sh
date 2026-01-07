#!/usr/bin/env bash
set -euo pipefail

CT_ID="${CT_ID:-}"
CT_HOSTNAME="${CT_HOSTNAME:-subagent}"
CT_TEMPLATE_STORAGE="${CT_TEMPLATE_STORAGE:-local}"
CT_TEMPLATE="${CT_TEMPLATE:-debian-12-standard_12.2-1_amd64.tar.zst}"
CT_OSTYPE="${CT_OSTYPE:-debian}"
CT_ROOTFS_STORAGE="${CT_ROOTFS_STORAGE:-local-lvm}"
CT_ROOTFS_SIZE="${CT_ROOTFS_SIZE:-40}"
CT_MEMORY="${CT_MEMORY:-8192}"
CT_SWAP="${CT_SWAP:-1024}"
CT_CORES="${CT_CORES:-4}"
CT_BRIDGE="${CT_BRIDGE:-vmbr0}"
CT_IP="${CT_IP:-dhcp}"
CT_GATEWAY="${CT_GATEWAY:-}"
CT_START="${CT_START:-1}"

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

if pct list | awk '{print $1}' | grep -q "^${CT_ID}$"; then
  echo "Container ID ${CT_ID} already exists."
  exit 1
fi

if ! command -v pveam >/dev/null 2>&1; then
  echo "pveam command not found. Install Proxmox template tools."
  exit 1
fi

if ! pveam list "${CT_TEMPLATE_STORAGE}" | grep -q "${CT_TEMPLATE}"; then
  pveam update
  pveam download "${CT_TEMPLATE_STORAGE}" "${CT_TEMPLATE}"
fi

NET0="name=eth0,bridge=${CT_BRIDGE},ip=${CT_IP}"
if [ -n "${CT_GATEWAY}" ]; then
  NET0="${NET0},gw=${CT_GATEWAY}"
fi

pct create "${CT_ID}" "${CT_TEMPLATE_STORAGE}:vztmpl/${CT_TEMPLATE}" \
  --hostname "${CT_HOSTNAME}" \
  --cores "${CT_CORES}" \
  --memory "${CT_MEMORY}" \
  --swap "${CT_SWAP}" \
  --rootfs "${CT_ROOTFS_STORAGE}:${CT_ROOTFS_SIZE}" \
  --net0 "${NET0}" \
  --unprivileged 1 \
  --features "keyctl=1,nesting=1" \
  --ostype "${CT_OSTYPE}" \
  --onboot 1 \
  --start "${CT_START}"

echo "Container ${CT_ID} created. Next: pct exec ${CT_ID} -- bash -lc '<bootstrap>'"
