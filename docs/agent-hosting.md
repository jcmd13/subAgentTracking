# Agent Hosting on Proxmox + Linux

This guide covers a long-running host for SubAgent Tracking System, plus
integration notes for Codex CLI, Claude Code CLI, and Gemini CLI. Project
requirements and roadmap live only in `README.md`.

## Host baseline (VM or LXC)
- Debian 12 or Ubuntu 22.04 recommended.
- 2-4 vCPU, 8GB RAM, 40GB disk.
- One dedicated `agent` user and a single workspace root (ex: `/opt/agents`).
- Tailscale for access instead of public ports.

## Proxmox helper (Ubuntu LXC, recommended)
If you use Proxmox, you can either clone this repo on the Proxmox host (to run
the helper wrapper) or curl the wrapper directly. Start with the
community helper script and apply
the recommended resources using the repo wrapper:

```bash
INTERACTIVE=1 bash scripts/agent-host/proxmox-ubuntu-helper.sh
```

Optional overrides:
```bash
INTERACTIVE=1 CT_ID=120 CT_CORES=4 CT_MEMORY=8192 CT_SWAP=1024 CT_DISK_TARGET_GB=40 \
  bash scripts/agent-host/proxmox-ubuntu-helper.sh
```

During the helper prompts, choose a CT ID and an Ubuntu LTS base image. The
wrapper will enforce CPU/RAM/swap and resize the disk to 40G by default unless
you override `CT_DISK_TARGET_GB` or `CT_DISK_GROW`.

## One-shot Proxmox deployment (recommended)
This creates the LXC with defaults (auto-picks a free CT_ID starting at 120),
bootstraps the container, installs CLIs, and enables services.

```bash
bash scripts/agent-host/proxmox-deploy.sh
```

Force interactive Ubuntu helper prompts:
```bash
INTERACTIVE=1 bash scripts/agent-host/proxmox-deploy.sh
```

Optional overrides for non-interactive runs:
```bash
CT_ID=120 CT_CORES=4 CT_MEMORY=8192 CT_SWAP=1024 CT_DISK_TARGET_GB=40 \
  REPO_URL=https://github.com/jcmd13/subAgentTracking.git INSTALL_TAILSCALE=1 \
  bash scripts/agent-host/proxmox-deploy.sh
```

If you prefer to avoid cloning on the Proxmox host, you can run it via curl:
```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/jcmd13/subAgentTracking/master/scripts/agent-host/proxmox-deploy.sh)"
```
Use `INTERACTIVE=1` for the Ubuntu helper prompts, or inline env overrides
above for non-interactive runs.

## Minimal curl-only flow (no host clone)
This path uses curl for everything and never clones the repo on the Proxmox host.

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/jcmd13/subAgentTracking/master/scripts/agent-host/proxmox-deploy.sh)"
```

After the script completes (replace `120` with your CT ID):
```bash
pct exec 120 -- bash -lc "nano /etc/subagent/agent.env"
pct exec 120 -- bash -lc "systemctl status subagent-dashboard subagent-monitor subagent-codex subagent-claude-code"
```

Then bootstrap inside the container:
```bash
pct exec 120 -- bash -lc \
  "apt-get update && apt-get install -y git && \
  git clone https://github.com/jcmd13/subAgentTracking.git /opt/agents/subAgentTracking && \
  cd /opt/agents/subAgentTracking && bash scripts/agent-host/bootstrap.sh"
```

## Step-by-step (scripted)
Step 1: Create the Ubuntu LXC with resources:
```bash
export CT_ID=120
export CT_CORES=4
export CT_MEMORY=8192
export CT_SWAP=1024
export CT_DISK_TARGET_GB=40
bash scripts/agent-host/proxmox-ubuntu-helper.sh
```

Step 2: Bootstrap and install CLIs inside the container:
```bash
pct exec 120 -- bash -lc \
  "apt-get update && apt-get install -y git curl ca-certificates && \
  git clone https://github.com/jcmd13/subAgentTracking.git /opt/agents/subAgentTracking && \
  cd /opt/agents/subAgentTracking && \
  bash scripts/agent-host/bootstrap.sh && \
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
  apt-get install -y nodejs && \
  npm i -g @openai/codex @anthropic-ai/claude-code @google/gemini-cli"
```

Step 3: Authenticate (add API keys) inside the container:
```bash
nano /etc/subagent/agent.env
```
Set `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`, and `SUBAGENT_PROVIDER_LIVE=1` if
you want live calls.

Step 4: Launch services:
```bash
cd /opt/agents/subAgentTracking
sudo AGENT_USER=agent REPO_DIR=/opt/agents/subAgentTracking \
  bash scripts/agent-host/enable-services.sh
```

## Proxmox helper (fully scripted LXC)
If you want a non-interactive LXC build without the community helper,
use the repo script:

```bash
export CT_ID=120
export CT_HOSTNAME=subagent
export CT_TEMPLATE_STORAGE=local
export CT_ROOTFS_STORAGE=local-lvm
export CT_BRIDGE=vmbr0
export CT_IP=dhcp
bash scripts/agent-host/proxmox-lxc.sh
```

## Bootstrap the host
Use the repo script (preferred) or your own provisioning.

Script: `scripts/agent-host/bootstrap.sh`
- Installs Python, git, tmux, direnv.
- Creates the `agent` user.
- Clones the repo and sets up the venv.
- Runs `subagent init`.

Example:
```bash
sudo AGENT_USER=agent WORKDIR=/opt/agents REPO_URL=https://github.com/jcmd13/subAgentTracking.git \
  bash scripts/agent-host/bootstrap.sh
```

## Environment file (secrets live outside git)
Copy the example environment file to `/etc/subagent/agent.env` and fill in keys.

Example template: `scripts/agent-host/agent.env.example`

## Systemd services (dashboard + monitor)
Templates live in `scripts/agent-host/systemd/`.

Install helper:
```bash
sudo AGENT_USER=agent REPO_DIR=/opt/agents/subAgentTracking \
  bash scripts/agent-host/install-systemd.sh
```

One-shot setup (recommended):
```bash
sudo AGENT_USER=agent REPO_DIR=/opt/agents/subAgentTracking \
  bash scripts/agent-host/enable-services.sh
```

Start services:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now subagent-dashboard.service subagent-monitor.service
```

## Tailscale access
Keep services bound to localhost and use Tailscale for access.

```bash
sudo tailscale up --ssh --hostname=subagent-host
tailscale serve --bg http://127.0.0.1:7841
tailscale serve --bg http://127.0.0.1:7842
```

## Codex CLI (ChatGPT) on a long-running host
Codex CLI is interactive, so prefer a tmux session or the provided systemd
launcher that creates a tmux session.

Install Node.js (LTS) and the CLIs (per vendor guidance):
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo bash -
sudo apt-get install -y nodejs
npm i -g @openai/codex @anthropic-ai/claude-code @google/gemini-cli
```

Start a session:
```bash
scripts/agent-host/codex-session.sh
```

Notes:
- Set `CODEX_CLI_CMD` and optional `CODEX_CLI_ARGS` in `/etc/subagent/agent.env`.
- Use `subagent session-start` and `subagent session-end` around long tasks.
- Keep secrets in `/etc/subagent/agent.env`, not in the repo.

Systemd (tmux) wrapper:
```bash
sudo systemctl enable --now subagent-codex
```
Set the binary and args in `/etc/subagent/agent.env`:
- `CODEX_CLI_CMD`
- `CODEX_CLI_ARGS`

## Claude Code CLI (MCP integration)
Start the MCP server from the repo:
```bash
scripts/agent-host/runner.sh python -m subagent.mcp.server
```

Then add an MCP server in Claude Code CLI that runs:
- Command: `python`
- Args: `-m subagent.mcp.server`
- Working directory: your repo root
Template configs live in `docs/mcp/`.

Optional env overrides:
- `SUBAGENT_PROJECT_DIR` (repo root)
- `SUBAGENT_DATA_DIR` (default: `.subagent/`)

Interactive session wrapper:
```bash
scripts/agent-host/claude-session.sh
```

Systemd (tmux) wrapper:
```bash
sudo systemctl enable --now subagent-claude-code
```
Set the binary and args in `/etc/subagent/agent.env`:
- `CLAUDE_CODE_CMD`
- `CLAUDE_CODE_ARGS`

## Gemini CLI (repo-native wrapper)
This repo includes a lightweight wrapper around the Gemini provider.

Script: `scripts/agent-host/gemini_cli.py`
```bash
export GOOGLE_API_KEY="..."
export SUBAGENT_PROVIDER_LIVE=1
./venv/bin/python scripts/agent-host/gemini_cli.py "Summarize the last log"
```

## GitHub hygiene (recommended)
- Use the PR template in `.github/PULL_REQUEST_TEMPLATE.md`.
- Keep CI green via `.github/workflows/ci.yml`.
- Log tasks using `subagent task add` and close with `subagent task complete`.

## Proxmox helper scripts
If you use community Proxmox helper scripts, choose a Debian/Ubuntu LXC or VM
template and run the bootstrap script from this repo after install.
