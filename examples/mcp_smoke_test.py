"""
MCP Smoke Test - Start MCP server and issue basic requests.

Run from repo root (or adjust paths):
  venv/bin/python examples/mcp_smoke_test.py

This script starts the MCP server over stdio and sends:
- initialize
- tools/list
- tools/call (subagent_status)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List


def _encode_message(payload: Dict[str, object]) -> bytes:
    body = json.dumps(payload).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
    return header + body


def _parse_responses(raw: bytes) -> List[Dict[str, object]]:
    responses: List[Dict[str, object]] = []
    idx = 0
    while idx < len(raw):
        header_end = raw.find(b"\r\n\r\n", idx)
        if header_end == -1:
            break
        header = raw[idx:header_end].decode("utf-8", errors="ignore")
        idx = header_end + 4
        length = None
        for line in header.splitlines():
            if line.lower().startswith("content-length"):
                try:
                    length = int(line.split(":", 1)[1].strip())
                except ValueError:
                    length = None
                break
        if length is None:
            break
        body = raw[idx : idx + length]
        idx += length
        try:
            responses.append(json.loads(body.decode("utf-8")))
        except json.JSONDecodeError:
            continue
    return responses


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    env = dict(os.environ)
    env["SUBAGENT_PROJECT_DIR"] = str(project_root)
    env.setdefault("SUBAGENT_CODEX_PROMPT_INSTALL", "false")

    python_path = env.get("PYTHONPATH", "")
    src_path = str(project_root / "src")
    env["PYTHONPATH"] = src_path if not python_path else f"{src_path}:{python_path}"

    messages = b"".join(
        [
            _encode_message({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}),
            _encode_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}),
            _encode_message(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "subagent_status", "arguments": {"verbose": False}},
                }
            ),
        ]
    )

    proc = subprocess.Popen(
        [sys.executable, "-m", "subagent.mcp.server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    try:
        stdout, stderr = proc.communicate(input=messages, timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        print("Timed out waiting for MCP server response")
        if stderr:
            print(stderr.decode("utf-8", errors="ignore"))
        return 1

    if stderr:
        print("Server stderr:")
        print(stderr.decode("utf-8", errors="ignore"))

    responses = _parse_responses(stdout)
    for response in responses:
        print("Response:")
        print(json.dumps(response, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
