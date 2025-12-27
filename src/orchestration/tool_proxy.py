"""Tool interception with permission checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import time
from typing import Any, Callable, Dict, Optional

from src.core import activity_logger_compat as activity_logger
from src.core.approval_store import get_approval, record_required
from src.orchestration.permissions import PermissionManager


WRITE_OPERATIONS = {"write", "edit", "delete", "modify"}
_TRUTHY = {"1", "true", "yes", "on"}
_DEFAULT_APPROVAL_THRESHOLD = 0.7


def _is_truthy(value: Optional[str]) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in _TRUTHY


@dataclass
class ToolResult:
    success: bool
    result: Any = None
    error: Optional[str] = None


class ToolProxy:
    """Validates tool calls and logs usage/violations."""

    def __init__(
        self,
        *,
        agent_id: str = "unknown",
        profile_name: Optional[str] = None,
        permission_manager: Optional[PermissionManager] = None,
    ) -> None:
        self.agent_id = agent_id
        self.profile_name = profile_name
        self.permission_manager = permission_manager or PermissionManager()

    def _resolve_path(self, path: str) -> tuple[Path, str, bool]:
        raw = Path(path)
        try:
            resolved = raw.expanduser()
        except RuntimeError:
            resolved = raw
        if not resolved.is_absolute():
            resolved = (self.permission_manager.project_root / resolved).resolve()
        else:
            resolved = resolved.resolve()
        try:
            rel = resolved.relative_to(self.permission_manager.project_root)
            return resolved, rel.as_posix(), False
        except ValueError:
            return resolved, resolved.as_posix(), True

    def _assess_risk(
        self,
        *,
        tool: str,
        operation: Optional[str],
        parameters: Dict[str, Any],
        file_path: Optional[str],
        requires_network: bool,
        requires_bash: bool,
        modifies_tests: bool,
    ) -> tuple[float, list[str]]:
        score = 0.0
        reasons: list[str] = []
        tool_lower = tool.lower()
        operation_lower = (operation or "").lower()

        if any(token in operation_lower for token in ("delete", "remove", "rm")) or tool_lower in {"delete", "rm"}:
            score += 0.7
            reasons.append("delete_operation")

        if any(token in operation_lower for token in ("write", "edit", "modify")):
            score += 0.25
            reasons.append("write_operation")

        if modifies_tests:
            score += 0.3
            reasons.append("modifies_tests")

        if requires_bash:
            score += 0.2
            reasons.append("bash_execution")

        if requires_network:
            score += 0.15
            reasons.append("network_access")

        command_value = parameters.get("command")
        if command_value:
            if isinstance(command_value, (list, tuple)):
                command_str = " ".join(str(part) for part in command_value)
            else:
                command_str = str(command_value)
            lowered = command_str.lower()
            if "git reset --hard" in lowered or "rm -rf" in lowered or "sudo " in lowered:
                score += 0.6
                reasons.append("destructive_command")

        content_value = parameters.get("content")
        if isinstance(content_value, str) and len(content_value) > 10000:
            score += 0.2
            reasons.append("large_write")

        if file_path:
            _, rel_posix, outside = self._resolve_path(file_path)
            rel_lower = rel_posix.lower()
            if outside:
                score += 0.5
                reasons.append("outside_project")
            if rel_posix.startswith(".") or "/." in rel_posix:
                score += 0.2
                reasons.append("dotfile_path")
            if rel_lower.endswith("requirements.txt") or rel_lower.endswith("pyproject.toml"):
                score += 0.2
                reasons.append("dependency_manifest")
            if rel_lower.endswith("setup.py") or rel_lower.endswith("setup.cfg"):
                score += 0.2
                reasons.append("build_config")
            if "config" in rel_lower and "permissions" in rel_lower:
                score += 0.3
                reasons.append("permissions_config")

        score = min(score, 1.0)
        return score, reasons

    def _approvals_enabled(self) -> bool:
        return _is_truthy(os.getenv("SUBAGENT_APPROVALS_ENABLED", "1"))

    def _approval_bypass(self, parameters: Dict[str, Any]) -> bool:
        if _is_truthy(os.getenv("SUBAGENT_APPROVALS_BYPASS")):
            return True
        approved_flag = parameters.get("approved") or parameters.get("approval_granted")
        if approved_flag:
            return True
        approval_id = parameters.get("approval_id")
        if approval_id:
            try:
                record = get_approval(str(approval_id))
            except Exception:
                record = None
            if record and record.get("status") == "granted":
                return True
        return False

    def execute(
        self,
        tool: str,
        func: Callable[..., Any],
        *,
        operation: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        file_path: Optional[str] = None,
        requires_network: bool = False,
        requires_bash: bool = False,
        modifies_tests: bool = False,
        profile_name: Optional[str] = None,
    ) -> ToolResult:
        params = dict(parameters or {})
        operation_name = operation or params.get("operation")

        decision = self.permission_manager.validate(
            tool=tool,
            operation=operation_name,
            path=file_path or params.get("file_path"),
            requires_network=requires_network,
            requires_bash=requires_bash,
            modifies_tests=modifies_tests,
            profile_name=profile_name or self.profile_name,
        )

        if not decision.allowed:
            try:
                activity_logger.log_tool_usage(
                    agent=self.agent_id,
                    tool=tool,
                    operation=operation_name,
                    parameters=params or None,
                    success=False,
                    error_message=decision.reason,
                    error_type="PermissionDenied",
                )
            except Exception:
                pass
            return ToolResult(success=False, error=decision.reason)

        if self._approvals_enabled() and not self._approval_bypass(params):
            risk_score, reasons = self._assess_risk(
                tool=tool,
                operation=operation_name,
                parameters=params,
                file_path=file_path or params.get("file_path"),
                requires_network=requires_network,
                requires_bash=requires_bash,
                modifies_tests=modifies_tests,
            )
            threshold_raw = os.getenv("SUBAGENT_APPROVAL_THRESHOLD")
            threshold = _DEFAULT_APPROVAL_THRESHOLD
            if threshold_raw is not None:
                try:
                    threshold = float(threshold_raw)
                except ValueError:
                    threshold = _DEFAULT_APPROVAL_THRESHOLD
            if risk_score >= threshold:
                summary_parts = [tool]
                if operation_name:
                    summary_parts.append(str(operation_name))
                if file_path or params.get("file_path"):
                    summary_parts.append(str(file_path or params.get("file_path")))
                summary = " ".join(summary_parts)
                try:
                    approval_record = record_required(
                        tool=tool,
                        risk_score=risk_score,
                        reasons=reasons or ["risk_threshold_exceeded"],
                        action="blocked",
                        session_id=None,
                        operation=operation_name,
                        file_path=file_path or params.get("file_path"),
                        agent=self.agent_id,
                        profile=profile_name or self.profile_name,
                        requires_network=requires_network,
                        requires_bash=requires_bash,
                        modifies_tests=modifies_tests,
                        summary=summary,
                    )
                except Exception:
                    approval_record = None
                try:
                    activity_logger.log_approval_required(
                        tool=tool,
                        operation=operation_name,
                        file_path=file_path or params.get("file_path"),
                        risk_score=risk_score,
                        reasons=reasons or ["risk_threshold_exceeded"],
                        action="blocked",
                        approval_id=approval_record.approval_id if approval_record else None,
                        agent=self.agent_id,
                        profile=profile_name or self.profile_name,
                        requires_network=requires_network,
                        requires_bash=requires_bash,
                        modifies_tests=modifies_tests,
                        summary=summary,
                    )
                except Exception:
                    pass
                params_with_approval = dict(params)
                if approval_record:
                    params_with_approval["approval_id"] = approval_record.approval_id
                try:
                    activity_logger.log_tool_usage(
                        agent=self.agent_id,
                        tool=tool,
                        operation=operation_name,
                        parameters=params_with_approval or None,
                        success=False,
                        error_message="approval_required",
                        error_type="ApprovalRequired",
                    )
                except Exception:
                    pass
                result_payload = None
                if approval_record:
                    result_payload = {"approval_id": approval_record.approval_id}
                return ToolResult(success=False, error="approval_required", result=result_payload)

        start = time.monotonic()
        try:
            result = func(**params)
            duration_ms = int((time.monotonic() - start) * 1000)
            try:
                activity_logger.log_tool_usage(
                    agent=self.agent_id,
                    tool=tool,
                    operation=operation_name,
                    parameters=params or None,
                    duration_ms=duration_ms,
                    success=True,
                )
            except Exception:
                pass
            return ToolResult(success=True, result=result)
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            try:
                activity_logger.log_tool_usage(
                    agent=self.agent_id,
                    tool=tool,
                    operation=operation_name,
                    parameters=params or None,
                    duration_ms=duration_ms,
                    success=False,
                    error_message=str(exc),
                    error_type="ToolExecutionError",
                )
            except Exception:
                pass
            return ToolResult(success=False, error=str(exc))


__all__ = ["ToolProxy", "ToolResult"]
