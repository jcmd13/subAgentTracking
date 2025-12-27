"""File tool operations with permission checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.orchestration.permissions import PermissionManager
from src.orchestration.tool_proxy import ToolProxy, ToolResult


@dataclass
class FileToolProxy:
    """Wrap file operations with ToolProxy checks."""

    agent_id: str = "system"
    profile_name: Optional[str] = None
    permission_manager: Optional[PermissionManager] = None

    def _proxy(self) -> ToolProxy:
        return ToolProxy(
            agent_id=self.agent_id,
            profile_name=self.profile_name,
            permission_manager=self.permission_manager or PermissionManager(),
        )

    def read(self, path: str, *, encoding: str = "utf-8") -> ToolResult:
        proxy = self._proxy()

        def _read(path: str, encoding: str) -> str:
            return Path(path).read_text(encoding=encoding)

        return proxy.execute(
            "read",
            _read,
            operation="read_file",
            parameters={"path": path, "encoding": encoding},
            file_path=path,
        )

    def write(
        self,
        path: str,
        content: str,
        *,
        encoding: str = "utf-8",
    ) -> ToolResult:
        proxy = self._proxy()

        def _write(path: str, content: str, encoding: str) -> str:
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding=encoding)
            return str(target)

        return proxy.execute(
            "write",
            _write,
            operation="write_file",
            parameters={"path": path, "content": content, "encoding": encoding},
            file_path=path,
            modifies_tests=True,
        )

    def edit(
        self,
        path: str,
        *,
        find: str,
        replace: str,
        count: int = 1,
        encoding: str = "utf-8",
    ) -> ToolResult:
        proxy = self._proxy()

        def _edit(path: str, find: str, replace: str, count: int, encoding: str) -> dict:
            target = Path(path)
            content = target.read_text(encoding=encoding)
            if find not in content:
                raise ValueError("Pattern not found")
            replace_count = count if count > 0 else content.count(find)
            new_content = content.replace(find, replace, replace_count)
            target.write_text(new_content, encoding=encoding)
            return {
                "path": str(target),
                "replacements": min(replace_count, content.count(find)),
            }

        return proxy.execute(
            "edit",
            _edit,
            operation="edit_file",
            parameters={
                "path": path,
                "find": find,
                "replace": replace,
                "count": count,
                "encoding": encoding,
            },
            file_path=path,
            modifies_tests=True,
        )


__all__ = ["FileToolProxy"]
