"""
Bootstrap helpers for SubAgent Tracking.

Provides a single entry point to initialize the local project layout with
safe defaults and minimal prompting.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional

import yaml

from src.core.config import get_config, Config


_DEFAULT_CLI_CONFIG: Dict[str, Any] = {
    "task_defaults": {"priority": 3},
    "status": {"watch_interval": 2.0},
}

_CODEX_PROMPT_NAME = "subagent-init"
_CODEX_PROMPT_CONTENT = """---
description: Initialize SubAgent Tracking for this project.
argument-hint: [confirm]
---

Initialize SubAgent Tracking with plug-and-play defaults.

If `.subagent/config.yaml` is missing, run:
- `./venv/bin/python -m src.subagent_cli.app init`
If `./venv/bin/python` does not exist, use `python3` or `python`.

If already initialized, confirm and do nothing.
"""


def _cli_config_path(cfg: Config) -> Path:
    return cfg.claude_dir / "config.yaml"


def _init_dirs(cfg: Config) -> None:
    base = cfg.claude_dir
    subdirs = [
        base,
        base / "logs",
        base / "state",
        base / "sessions",
        base / "tasks",
        base / "handoffs",
        base / "quality",
        base / "analytics",
        base / "credentials",
        base / "requirements",
        base / "hooks",
    ]
    for directory in subdirs:
        directory.mkdir(parents=True, exist_ok=True)
        gitkeep = directory / ".gitkeep"
        if not gitkeep.exists() and not any(directory.iterdir()):
            gitkeep.touch()


def _codex_prompts_dir() -> Path:
    return Path.home() / ".codex" / "prompts"


def _should_install_codex_prompt() -> bool:
    mode = os.getenv("SUBAGENT_CODEX_PROMPT_INSTALL", "auto").strip().lower()
    if mode in ("false", "0", "no"):
        return False
    if mode in ("true", "1", "yes"):
        return True
    return (Path.home() / ".codex").exists()


def ensure_codex_prompt_installed() -> bool:
    if not _should_install_codex_prompt():
        return False
    prompts_dir = _codex_prompts_dir()
    prompts_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = prompts_dir / f"{_CODEX_PROMPT_NAME}.md"
    if prompt_path.exists():
        return True
    prompt_path.write_text(_CODEX_PROMPT_CONTENT)
    return True


def is_initialized(cfg: Optional[Config] = None) -> bool:
    cfg = cfg or get_config(reload=True)
    return _cli_config_path(cfg).exists()


def initialize_project(cfg: Optional[Config] = None) -> Dict[str, Any]:
    cfg = cfg or get_config(reload=True)
    _init_dirs(cfg)

    config_path = _cli_config_path(cfg)
    created_config = False
    if not config_path.exists():
        config_path.write_text(yaml.safe_dump(_DEFAULT_CLI_CONFIG))
        created_config = True

    codex_prompt_installed = False
    try:
        codex_prompt_installed = ensure_codex_prompt_installed()
    except Exception:
        codex_prompt_installed = False

    return {
        "initialized": True,
        "config_path": str(config_path),
        "data_dir": str(cfg.claude_dir),
        "created_config": created_config,
        "codex_prompt_installed": codex_prompt_installed,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def _should_auto_init() -> str:
    return os.getenv("SUBAGENT_AUTO_INIT", "ask").strip().lower()


def ensure_initialized(
    *,
    prompt_if_needed: bool = True,
    assume_yes: bool = True,
) -> bool:
    """
    Ensure the project is initialized.

    Returns True if initialization is complete or already done.
    """
    cfg = get_config(reload=True)
    if is_initialized(cfg):
        return True

    mode = _should_auto_init()
    if mode in ("false", "0", "no"):
        return False

    if mode in ("true", "1", "yes"):
        initialize_project(cfg)
        return True

    if not prompt_if_needed:
        if assume_yes:
            initialize_project(cfg)
            return True
        return False

    if not sys.stdin.isatty():
        initialize_project(cfg)
        return True

    answer = input("Initialize SubAgent Tracking for this project now? [Y/n]: ").strip().lower()
    if answer in ("", "y", "yes"):
        initialize_project(cfg)
        return True

    return False


__all__ = [
    "ensure_initialized",
    "ensure_codex_prompt_installed",
    "initialize_project",
    "is_initialized",
]
