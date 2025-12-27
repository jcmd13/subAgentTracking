"""Permission system for tools and file access."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple
import fnmatch
import os

import yaml

from src.core.config import get_config


DEFAULT_PERMISSION_PROFILES: Dict[str, Dict[str, Any]] = {
    "default_worker": {
        "tools": ["read", "write", "edit", "provider"],
        "paths_allowed": ["src/**", "tests/**"],
        "paths_forbidden": [".env*", "*.secret", ".subagent/config.yaml"],
        "can_spawn_subagents": False,
        "can_modify_tests": False,
        "can_run_bash": False,
        "can_access_network": False,
    },
    "elevated": {
        "can_run_bash": True,
        "can_access_network": True,
    },
}


def _normalize_tools(tools: Iterable[str]) -> List[str]:
    return [str(tool).strip().lower() for tool in tools if str(tool).strip()]


def _resolve_path(path: str, project_root: Path) -> Tuple[Path, str]:
    raw = Path(path)
    try:
        resolved = raw.expanduser()
    except RuntimeError:
        resolved = raw
    if not resolved.is_absolute():
        resolved = (project_root / resolved).resolve()
    else:
        resolved = resolved.resolve()
    try:
        rel = resolved.relative_to(project_root)
        rel_posix = rel.as_posix()
    except ValueError:
        rel_posix = resolved.as_posix()
    return resolved, rel_posix


def _match_patterns(path_posix: str, patterns: Iterable[str]) -> bool:
    for pattern in patterns:
        if not pattern:
            continue
        pattern_str = str(pattern)
        if pattern_str.startswith("~"):
            pattern_str = str(Path(pattern_str).expanduser())
        if fnmatch.fnmatch(path_posix, pattern_str):
            return True
    return False


def _is_test_path(path_posix: str) -> bool:
    if path_posix.startswith("tests/") or path_posix == "tests":
        return True
    return Path(path_posix).name.startswith("test_")


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    reason: Optional[str] = None
    violations: List[str] = field(default_factory=list)


@dataclass
class PermissionProfile:
    name: str
    tools: List[str] = field(default_factory=list)
    paths_allowed: List[str] = field(default_factory=list)
    paths_forbidden: List[str] = field(default_factory=list)
    can_spawn_subagents: bool = False
    can_modify_tests: bool = False
    can_run_bash: bool = False
    can_access_network: bool = False

    def allows_tool(self, tool: str) -> bool:
        normalized = tool.strip().lower()
        if not self.tools:
            return True
        return normalized in self.tools


class PermissionManager:
    """Loads permission profiles and validates tool/file access."""

    def __init__(
        self,
        config_path: Optional[Path] = None,
        config: Optional[Dict[str, Any]] = None,
        project_root: Optional[Path] = None,
    ) -> None:
        cfg = get_config(reload=True)
        self.project_root = project_root or cfg.project_root
        self.config_path = config_path or (cfg.claude_dir / "config" / "permissions.yaml")
        self._profiles: Dict[str, PermissionProfile] = {}
        self.default_profile = "default_worker"
        self._load_profiles(config)

    def _load_profiles(self, override: Optional[Dict[str, Any]]) -> None:
        permissions_cfg: Dict[str, Any] = {}

        if self.config_path.exists():
            try:
                data = yaml.safe_load(self.config_path.read_text()) or {}
                permissions_cfg = data.get("permissions", {}) if isinstance(data, dict) else {}
            except Exception:
                permissions_cfg = {}
        else:
            config_yaml = self._load_root_config()
            if config_yaml:
                permissions_cfg = config_yaml.get("permissions", {}) if isinstance(config_yaml, dict) else {}

        if override:
            override_permissions = override.get("permissions") if isinstance(override, dict) else None
            if isinstance(override_permissions, dict):
                permissions_cfg = override_permissions

        if isinstance(permissions_cfg, dict):
            self.default_profile = str(
                permissions_cfg.get("default_profile")
                or permissions_cfg.get("default")
                or self.default_profile
            )
            profiles_cfg = permissions_cfg.get("profiles")
            if isinstance(profiles_cfg, dict):
                permissions_cfg = profiles_cfg
            else:
                permissions_cfg = {
                    key: value
                    for key, value in permissions_cfg.items()
                    if key not in {"default_profile", "default"}
                }
        else:
            permissions_cfg = {}

        merged_profiles = dict(DEFAULT_PERMISSION_PROFILES)
        for name, values in permissions_cfg.items():
            if not isinstance(values, dict):
                continue
            merged = dict(merged_profiles.get(name, {}))
            merged.update(values)
            merged_profiles[name] = merged

        self._profiles = {
            name: self._profile_from_dict(name, values)
            for name, values in merged_profiles.items()
        }

    def _load_root_config(self) -> Optional[Dict[str, Any]]:
        root_config_path = self.project_root / ".subagent" / "config.yaml"
        if not root_config_path.exists():
            return None
        try:
            return yaml.safe_load(root_config_path.read_text()) or {}
        except Exception:
            return None

    def _profile_from_dict(self, name: str, data: Dict[str, Any]) -> PermissionProfile:
        tools = _normalize_tools(data.get("tools", []))
        return PermissionProfile(
            name=name,
            tools=tools,
            paths_allowed=list(data.get("paths_allowed", []) or []),
            paths_forbidden=list(data.get("paths_forbidden", []) or []),
            can_spawn_subagents=bool(data.get("can_spawn_subagents", False)),
            can_modify_tests=bool(data.get("can_modify_tests", False)),
            can_run_bash=bool(data.get("can_run_bash", False)),
            can_access_network=bool(data.get("can_access_network", False)),
        )

    def get_profile(self, name: Optional[str] = None) -> PermissionProfile:
        profile_name = name or self.default_profile
        profile = self._profiles.get(profile_name)
        if profile is None:
            profile = self._profiles[self.default_profile]
        return profile

    def validate(
        self,
        *,
        tool: str,
        operation: Optional[str] = None,
        path: Optional[str] = None,
        requires_network: bool = False,
        requires_bash: bool = False,
        modifies_tests: bool = False,
        profile_name: Optional[str] = None,
    ) -> PermissionDecision:
        profile = self.get_profile(profile_name)
        violations: List[str] = []

        if not profile.allows_tool(tool):
            violations.append(f"tool:{tool}")

        if requires_bash and not profile.can_run_bash:
            violations.append("bash")

        if requires_network and not profile.can_access_network:
            violations.append("network")

        if path:
            resolved, rel_posix = _resolve_path(path, self.project_root)
            if _match_patterns(rel_posix, profile.paths_forbidden) or _match_patterns(
                resolved.as_posix(), profile.paths_forbidden
            ):
                violations.append("path_forbidden")
            elif profile.paths_allowed:
                if not _match_patterns(rel_posix, profile.paths_allowed):
                    violations.append("path_not_allowed")

            if modifies_tests or (operation and operation.lower() in {"write", "edit", "delete"}):
                if _is_test_path(rel_posix) and not profile.can_modify_tests:
                    violations.append("tests_protected")

        if violations:
            reason = ", ".join(violations)
            return PermissionDecision(allowed=False, reason=reason, violations=violations)

        return PermissionDecision(allowed=True)


__all__ = [
    "PermissionDecision",
    "PermissionProfile",
    "PermissionManager",
]
