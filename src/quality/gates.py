"""Quality gate definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence, Callable, Any, Dict, Iterable
import json
import os
import re
import subprocess
import sys
import time

from src.core.config import get_config
from src.core.providers import build_providers, FallbackManager, ProviderError
from src.orchestration.test_protection import (
    detect_test_modifications,
    assert_tests_unmodified,
    list_modified_paths,
)
from src.orchestration.permissions import PermissionManager
from src.orchestration.tool_proxy import ToolProxy, ToolResult

_DEFAULT_SECRET_PATTERNS = [
    r"password\s*=\s*['\"][^'\"]+['\"]",
    r"api_key\s*=\s*['\"][^'\"]+['\"]",
    r"secret\s*=\s*['\"][^'\"]+['\"]",
]

_STOPWORDS = {
    "the",
    "and",
    "with",
    "for",
    "from",
    "into",
    "that",
    "this",
    "these",
    "those",
    "when",
    "then",
    "than",
    "also",
    "only",
    "just",
    "over",
    "under",
    "your",
    "ours",
    "their",
    "task",
    "update",
    "change",
    "build",
    "make",
    "add",
    "remove",
}


def _is_truthy(value: Optional[str]) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in ("1", "true", "yes", "on")


@dataclass
class GateResult:
    name: str
    passed: bool
    required: bool = True
    message: str = ""
    duration_ms: Optional[int] = None
    details: dict = field(default_factory=dict)


class QualityGate:
    """Base class for quality gates."""

    name: str = "quality_gate"
    required: bool = True

    def run(self) -> GateResult:
        raise NotImplementedError


class ProtectedTestsGate(QualityGate):
    """Detects test modifications before running gates."""

    name = "protected_tests"
    required = True

    def __init__(
        self,
        *,
        repo_root: Optional[Path] = None,
        modified_paths: Optional[List[str]] = None,
    ) -> None:
        self.repo_root = repo_root
        self.modified_paths = modified_paths

    def run(self) -> GateResult:
        try:
            if self.modified_paths is None:
                assert_tests_unmodified(repo_root=self.repo_root)
            else:
                modified = detect_test_modifications(self.modified_paths)
                if modified:
                    raise RuntimeError(f"Test modifications detected: {', '.join(modified)}")
        except Exception as exc:
            return GateResult(
                name=self.name,
                passed=False,
                required=self.required,
                message=str(exc),
            )

        return GateResult(name=self.name, passed=True, required=self.required)


class CommandGate(QualityGate):
    """Run a shell command and check exit status."""

    def __init__(
        self,
        name: str,
        command: Sequence[str],
        *,
        required: bool = True,
        timeout_seconds: Optional[int] = None,
        permission_profile: Optional[str] = "elevated",
        requires_network: bool = False,
        runner: Optional[Callable[[Sequence[str], Optional[int]], Any]] = None,
        permission_manager: Optional[PermissionManager] = None,
    ) -> None:
        self.name = name
        self.command = list(command)
        self.required = required
        self.timeout_seconds = timeout_seconds
        self.permission_profile = permission_profile
        self.requires_network = requires_network
        self.runner = runner
        self.permission_manager = permission_manager or PermissionManager()

    def _run_command(self, command: Sequence[str], timeout: Optional[int]) -> Any:
        if self.runner:
            return self.runner(command, timeout)
        return subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def run(self) -> GateResult:
        start = time.monotonic()
        proxy = ToolProxy(
            agent_id="quality-gate",
            profile_name=self.permission_profile,
            permission_manager=self.permission_manager,
        )

        def _execute(command: Sequence[str], timeout: Optional[int]) -> Any:
            return self._run_command(command, timeout)

        tool_result: ToolResult = proxy.execute(
            "bash",
            _execute,
            operation="exec",
            parameters={"command": self.command, "timeout": self.timeout_seconds},
            requires_bash=True,
            requires_network=self.requires_network,
            profile_name=self.permission_profile,
        )

        duration_ms = int((time.monotonic() - start) * 1000)
        if not tool_result.success:
            return GateResult(
                name=self.name,
                passed=False,
                required=self.required,
                message=tool_result.error or "command_failed",
                duration_ms=duration_ms,
                details={"command": " ".join(self.command)},
            )

        result = tool_result.result
        if isinstance(result, subprocess.CompletedProcess):
            exit_code = result.returncode
            stdout = result.stdout or ""
            stderr = result.stderr or ""
        elif isinstance(result, dict):
            exit_code = result.get("returncode", result.get("exit_code", 1))
            stdout = result.get("stdout") or ""
            stderr = result.get("stderr") or ""
        else:
            exit_code = 0
            stdout = ""
            stderr = ""

        passed = exit_code == 0
        message = "" if passed else (stderr.strip() or "command_failed")
        return GateResult(
            name=self.name,
            passed=passed,
            required=self.required,
            message=message,
            duration_ms=duration_ms,
            details={
                "command": " ".join(self.command),
                "exit_code": exit_code,
                "stdout": _truncate_output(stdout),
                "stderr": _truncate_output(stderr),
            },
        )


class PytestGate(CommandGate):
    """Run pytest tests."""

    def __init__(self, *, required: bool = True, timeout_seconds: Optional[int] = None, **kwargs: Any) -> None:
        command = [sys.executable, "-m", "pytest", "tests", "-v"]
        super().__init__(
            "pytest",
            command,
            required=required,
            timeout_seconds=timeout_seconds,
            **kwargs,
        )


class CoverageGate(CommandGate):
    """Run pytest with coverage enforcement."""

    def __init__(
        self,
        *,
        required: bool = True,
        timeout_seconds: Optional[int] = None,
        coverage_threshold: int = 80,
        **kwargs: Any,
    ) -> None:
        command = [
            sys.executable,
            "-m",
            "pytest",
            "--cov=src",
            f"--cov-fail-under={coverage_threshold}",
        ]
        super().__init__(
            "coverage",
            command,
            required=required,
            timeout_seconds=timeout_seconds,
            **kwargs,
        )
        self.coverage_threshold = coverage_threshold


class DiffReviewGate(QualityGate):
    """Review diffs for task alignment."""

    name = "diff_review"
    required = False

    def __init__(
        self,
        *,
        task_id: Optional[str] = None,
        task_summary: Optional[str] = None,
        task_context: Optional[str] = None,
        repo_root: Optional[Path] = None,
        diff_text: Optional[str] = None,
        modified_paths: Optional[Iterable[str]] = None,
        permission_profile: Optional[str] = "elevated",
        permission_manager: Optional[PermissionManager] = None,
        provider_manager: Optional[FallbackManager] = None,
        use_provider: Optional[bool] = None,
        max_diff_chars: int = 12000,
        required: bool = False,
    ) -> None:
        self.task_id = task_id or os.getenv("SUBAGENT_DIFF_REVIEW_TASK_ID")
        self.task_summary = task_summary or os.getenv("SUBAGENT_DIFF_REVIEW_TASK_SUMMARY")
        self.task_context = task_context
        self.repo_root = repo_root or Path.cwd()
        self.diff_text = diff_text
        self.modified_paths = list(modified_paths) if modified_paths is not None else None
        self.permission_profile = permission_profile
        self.permission_manager = permission_manager or PermissionManager()
        self.provider_manager = provider_manager
        self.use_provider = use_provider if use_provider is not None else _is_truthy(
            os.getenv("SUBAGENT_DIFF_REVIEW_PROVIDER")
        )
        self.max_diff_chars = max_diff_chars
        self.required = required

    def _collect_diff(self) -> str:
        if self.diff_text is not None:
            return self.diff_text
        try:
            result = subprocess.run(
                ["git", "diff", "--no-color"],
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception:
            return ""
        if result.returncode != 0:
            return ""
        return result.stdout or ""

    def _collect_modified_paths(self) -> List[str]:
        if self.modified_paths is not None:
            return list(self.modified_paths)
        return list_modified_paths(repo_root=self.repo_root)

    def _load_tasks(self) -> List[Dict[str, Any]]:
        cfg = get_config(reload=True)
        tasks_path = cfg.claude_dir / "tasks" / "tasks.json"
        if not tasks_path.exists():
            return []
        try:
            return json.loads(tasks_path.read_text())
        except Exception:
            return []

    def _select_task(self, tasks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if self.task_id:
            for task in tasks:
                if task.get("id") == self.task_id:
                    return task
            return None
        candidates = [
            task
            for task in tasks
            if str(task.get("status", "")).lower() not in {"completed", "done", "closed"}
        ]
        if not candidates:
            candidates = tasks
        if not candidates:
            return None
        candidates.sort(key=lambda item: item.get("created_at") or "")
        return candidates[-1]

    def _build_task_context(self, task: Dict[str, Any]) -> str:
        parts = []
        description = task.get("description")
        if description:
            parts.append(str(description))
        criteria = task.get("acceptance_criteria") or []
        if criteria:
            parts.append("Acceptance criteria: " + "; ".join(str(item) for item in criteria))
        context = task.get("context") or []
        if context:
            parts.append("Context: " + "; ".join(str(item) for item in context))
        return "\n".join(parts)

    def _resolve_task_context(self) -> Optional[str]:
        if self.task_context:
            return self.task_context
        if self.task_summary:
            return self.task_summary
        tasks = self._load_tasks()
        task = self._select_task(tasks)
        if not task:
            return None
        return self._build_task_context(task)

    def _extract_keywords(self, text: str) -> List[str]:
        tokens = re.findall(r"[a-z0-9_]{4,}", text.lower())
        return [token for token in tokens if token not in _STOPWORDS]

    def _parse_provider_output(self, output: str) -> Optional[Dict[str, Any]]:
        if not output:
            return None
        try:
            return json.loads(output)
        except Exception:
            match = re.search(r"\{.*\}", output, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    return None
        return None

    def _review_with_provider(self, task_context: str, diff_text: str) -> Optional[Dict[str, Any]]:
        provider_manager = self.provider_manager or FallbackManager(build_providers())
        if not provider_manager.providers:
            return None
        if not any(getattr(provider, "allow_live", False) for provider in provider_manager.providers):
            return None
        decision = self.permission_manager.validate(
            tool="provider",
            requires_network=True,
            profile_name=self.permission_profile,
        )
        if not decision.allowed:
            raise ProviderError(decision.reason or "provider_permission_denied")

        prompt = (
            "Review the following code diff for alignment with the task. "
            "Return JSON with fields: passed (boolean), issues (list), summary (string).\n\n"
            f"Task:\n{task_context}\n\nDiff:\n{diff_text}"
        )
        output = provider_manager.generate(prompt)
        parsed = self._parse_provider_output(output)
        if parsed is None:
            raise ProviderError("diff_review_unparseable")
        return parsed

    def run(self) -> GateResult:
        start = time.monotonic()
        details: Dict[str, Any] = {}

        modified_paths = self._collect_modified_paths()
        if modified_paths:
            details["modified_paths"] = modified_paths
        test_mods = detect_test_modifications(modified_paths)
        if test_mods:
            return GateResult(
                name=self.name,
                passed=False,
                required=self.required,
                message=f"Test modifications detected: {', '.join(test_mods)}",
                duration_ms=int((time.monotonic() - start) * 1000),
                details={"tests_modified": test_mods},
            )

        diff_text = self._collect_diff()
        if not diff_text.strip():
            details["skipped"] = True
            return GateResult(
                name=self.name,
                passed=True,
                required=self.required,
                message="no_diff",
                duration_ms=int((time.monotonic() - start) * 1000),
                details=details,
            )

        if len(diff_text) > self.max_diff_chars:
            diff_text = diff_text[: self.max_diff_chars].rstrip() + "..."
            details["diff_truncated"] = True
        details["diff_chars"] = len(diff_text)

        task_context = self._resolve_task_context()
        if not task_context:
            details["skipped"] = True
            return GateResult(
                name=self.name,
                passed=True,
                required=self.required,
                message="no_task_context",
                duration_ms=int((time.monotonic() - start) * 1000),
                details=details,
            )

        if self.use_provider:
            try:
                review = self._review_with_provider(task_context, diff_text)
            except ProviderError as exc:
                details["provider_error"] = str(exc)
            else:
                passed_value = review.get("passed")
                issues = review.get("issues") if isinstance(review.get("issues"), list) else []
                summary = review.get("summary") or ""
                passed = bool(passed_value) if passed_value is not None else not issues
                message = "; ".join(str(item) for item in issues) or str(summary)
                details["provider_review"] = review
                return GateResult(
                    name=self.name,
                    passed=passed,
                    required=self.required,
                    message=message,
                    duration_ms=int((time.monotonic() - start) * 1000),
                    details=details,
                )

        keywords = self._extract_keywords(task_context)
        if not keywords:
            details["skipped"] = True
            return GateResult(
                name=self.name,
                passed=True,
                required=self.required,
                message="no_task_keywords",
                duration_ms=int((time.monotonic() - start) * 1000),
                details=details,
            )

        diff_lower = diff_text.lower()
        overlap = [kw for kw in keywords if kw in diff_lower]
        details["keyword_overlap"] = overlap[:10]
        details["keyword_count"] = len(keywords)

        if overlap:
            return GateResult(
                name=self.name,
                passed=True,
                required=self.required,
                duration_ms=int((time.monotonic() - start) * 1000),
                details=details,
            )

        return GateResult(
            name=self.name,
            passed=False,
            required=self.required,
            message="diff_review_off_task",
            duration_ms=int((time.monotonic() - start) * 1000),
            details=details,
        )


class SecretScanGate(QualityGate):
    """Scan for hardcoded secrets in modified files."""

    name = "no_secrets"
    required = True

    def __init__(
        self,
        *,
        patterns: Optional[Iterable[str]] = None,
        repo_root: Optional[Path] = None,
        paths: Optional[Iterable[str]] = None,
        max_file_bytes: int = 200000,
        required: bool = True,
    ) -> None:
        self.patterns = list(patterns) if patterns is not None else list(_DEFAULT_SECRET_PATTERNS)
        self.repo_root = repo_root or Path.cwd()
        self.paths = list(paths) if paths is not None else None
        self.max_file_bytes = max_file_bytes
        self.required = required
        self._compiled: List[re.Pattern[str]] = []
        for pattern in self.patterns:
            try:
                self._compiled.append(re.compile(pattern, re.IGNORECASE))
            except re.error:
                continue

    def _collect_paths(self) -> List[Path]:
        if self.paths is not None:
            return [Path(path) for path in self.paths]
        return [Path(path) for path in list_modified_paths(repo_root=self.repo_root)]

    def _should_scan(self, path: Path) -> bool:
        parts = set(path.parts)
        if ".git" in parts or ".subagent" in parts or "venv" in parts:
            return False
        return True

    def run(self) -> GateResult:
        start = time.monotonic()
        matches: List[Dict[str, Any]] = []
        scanned: List[str] = []

        for raw_path in self._collect_paths():
            path = raw_path
            if not path.is_absolute():
                path = (self.repo_root / path).resolve()
            if not path.exists() or not path.is_file():
                continue
            if not self._should_scan(path):
                continue
            if self.max_file_bytes and path.stat().st_size > self.max_file_bytes:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            try:
                rel = path.relative_to(self.repo_root).as_posix()
            except ValueError:
                rel = path.as_posix()
            scanned.append(rel)

            for line_no, line in enumerate(text.splitlines(), start=1):
                for pattern in self._compiled:
                    if pattern.search(line):
                        matches.append(
                            {
                                "path": rel,
                                "line": line_no,
                                "pattern": pattern.pattern,
                            }
                        )

        duration_ms = int((time.monotonic() - start) * 1000)
        details = {"matches": matches, "scanned_files": scanned}
        if matches:
            return GateResult(
                name=self.name,
                passed=False,
                required=self.required,
                message=f"Secrets detected in {len({m['path'] for m in matches})} file(s)",
                duration_ms=duration_ms,
                details=details,
            )

        return GateResult(
            name=self.name,
            passed=True,
            required=self.required,
            duration_ms=duration_ms,
            details=details,
        )


def _truncate_output(text: str, limit: int = 2000) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "..."


__all__ = [
    "GateResult",
    "QualityGate",
    "ProtectedTestsGate",
    "CommandGate",
    "PytestGate",
    "CoverageGate",
    "DiffReviewGate",
    "SecretScanGate",
]
