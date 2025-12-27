"""Helpers to detect and block test modifications."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional
import subprocess


def is_test_path(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if normalized.startswith("tests/") or normalized == "tests":
        return True
    return Path(normalized).name.startswith("test_")


def detect_test_modifications(paths: Iterable[str]) -> List[str]:
    return [path for path in paths if is_test_path(path)]


def list_modified_paths(repo_root: Optional[Path] = None) -> List[str]:
    root = repo_root or Path.cwd()
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return []

    if result.returncode != 0:
        return []

    paths = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        parts = line.split(maxsplit=1)
        if len(parts) != 2:
            continue
        paths.append(parts[1])
    return paths


def assert_tests_unmodified(repo_root: Optional[Path] = None) -> List[str]:
    paths = list_modified_paths(repo_root=repo_root)
    modified = detect_test_modifications(paths)
    if modified:
        raise RuntimeError(f"Test modifications detected: {', '.join(modified)}")
    return modified


__all__ = [
    "is_test_path",
    "detect_test_modifications",
    "list_modified_paths",
    "assert_tests_unmodified",
]
