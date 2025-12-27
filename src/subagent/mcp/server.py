"""MCP server implementation for SubAgent."""

from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, Optional, Callable, Iterable

from src.subagent.mcp.tools import get_tool_definitions
from src.subagent.mcp.handlers import (
    MCPToolError,
    handle_subagent_status,
    handle_subagent_task_create,
    handle_subagent_spawn,
    handle_subagent_agent_control,
    handle_subagent_review,
    handle_subagent_handoff,
    handle_subagent_metrics,
)


SERVER_NAME = "subagent"
SERVER_VERSION = "0.1.0"
PROTOCOL_VERSION = "2024-11-05"


ToolHandler = Callable[..., Dict[str, Any]]


DEFAULT_TOOL_HANDLERS: Dict[str, ToolHandler] = {
    "subagent_status": handle_subagent_status,
    "subagent_task_create": handle_subagent_task_create,
    "subagent_spawn": handle_subagent_spawn,
    "subagent_agent_control": handle_subagent_agent_control,
    "subagent_review": handle_subagent_review,
    "subagent_handoff": handle_subagent_handoff,
    "subagent_metrics": handle_subagent_metrics,
}


class MCPServer:
    """Simple MCP JSON-RPC server over stdio."""

    def __init__(
        self,
        *,
        in_stream: Optional[Any] = None,
        out_stream: Optional[Any] = None,
        tool_handlers: Optional[Dict[str, ToolHandler]] = None,
        tool_definitions: Optional[Iterable[Dict[str, Any]]] = None,
    ) -> None:
        self.in_stream = in_stream or sys.stdin.buffer
        self.out_stream = out_stream or sys.stdout.buffer
        self.tool_handlers = tool_handlers or dict(DEFAULT_TOOL_HANDLERS)
        self.tool_definitions = list(tool_definitions or get_tool_definitions())
        self._shutdown = False

    def serve_forever(self) -> None:
        while not self._shutdown:
            request = self._read_message()
            if request is None:
                break
            response = self._handle_request(request)
            if response is not None:
                self._send_message(response)

    def _read_message(self) -> Optional[Dict[str, Any]]:
        header_line = self.in_stream.readline()
        if not header_line:
            return None

        header_line = header_line.strip()
        if not header_line:
            return None

        if header_line.startswith(b"{"):
            try:
                return json.loads(header_line.decode("utf-8"))
            except Exception:
                return None

        headers: Dict[str, str] = {}
        line = header_line
        while line:
            if line == b"\r\n" or line == b"\n":
                break
            try:
                key, value = line.decode("utf-8").split(":", 1)
            except ValueError:
                key, value = line.decode("utf-8"), ""
            headers[key.strip().lower()] = value.strip()
            line = self.in_stream.readline()

        length_value = headers.get("content-length")
        if not length_value:
            return None
        try:
            length = int(length_value)
        except ValueError:
            return None
        payload = self.in_stream.read(length)
        if not payload:
            return None
        try:
            return json.loads(payload.decode("utf-8"))
        except Exception:
            return None

    def _send_message(self, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
        self.out_stream.write(header + body)
        self.out_stream.flush()

    def _handle_request(self, request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params") or {}

        if method == "initialize":
            result = {
                "protocolVersion": PROTOCOL_VERSION,
                "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
                "capabilities": {"tools": {}},
            }
            return self._response(request_id, result)

        if method in {"initialized", "exit"}:
            if method == "exit":
                self._shutdown = True
            return None

        if method == "shutdown":
            self._shutdown = True
            return self._response(request_id, None)

        if method == "tools/list":
            return self._response(request_id, {"tools": self.tool_definitions})

        if method == "tools/call":
            if request_id is None:
                return None
            name = params.get("name")
            arguments = params.get("arguments") or {}
            return self._response(request_id, self._invoke_tool(name, arguments))

        if request_id is None:
            return None

        return self._error_response(request_id, -32601, f"Method not found: {method}")

    def _invoke_tool(self, name: Optional[str], arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not name:
            return {
                "isError": True,
                "content": [{"type": "text", "text": "Missing tool name"}],
            }
        handler = self.tool_handlers.get(name)
        if not handler:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
            }
        try:
            result = handler(**arguments)
        except MCPToolError as exc:
            return {
                "isError": True,
                "content": [{"type": "text", "text": str(exc)}],
            }
        except Exception as exc:
            return {
                "isError": True,
                "content": [{"type": "text", "text": f"Tool failed: {exc}"}],
            }

        try:
            serialized = json.dumps(result, indent=2)
        except TypeError:
            serialized = str(result)

        return {
            "content": [{"type": "text", "text": serialized}],
            "structured": result,
        }

    def _response(self, request_id: Any, result: Any) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def _error_response(self, request_id: Any, code: int, message: str) -> Dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def _maybe_chdir() -> None:
    project_dir = os.getenv("SUBAGENT_PROJECT_DIR") or os.getenv("SUBAGENT_PROJECT_ROOT")
    if project_dir:
        try:
            os.chdir(project_dir)
        except Exception:
            pass


def main() -> None:
    _maybe_chdir()
    server = MCPServer()
    server.serve_forever()


if __name__ == "__main__":
    main()
