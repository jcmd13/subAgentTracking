import json
from io import BytesIO

from src.subagent.mcp.server import MCPServer


def _encode_message(payload):
    body = json.dumps(payload).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
    return header + body


def _decode_single_response(buffer):
    raw = buffer.getvalue()
    header, body = raw.split(b"\r\n\r\n", 1)
    length = None
    for line in header.splitlines():
        if line.lower().startswith(b"content-length"):
            length = int(line.split(b":", 1)[1].strip())
            break
    assert length is not None
    payload = body[:length]
    return json.loads(payload.decode("utf-8"))


def test_mcp_server_tools_list():
    request = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    input_stream = BytesIO(_encode_message(request))
    output_stream = BytesIO()
    server = MCPServer(
        in_stream=input_stream,
        out_stream=output_stream,
        tool_handlers={},
        tool_definitions=[{"name": "subagent_status", "inputSchema": {"type": "object"}}],
    )
    server.serve_forever()
    response = _decode_single_response(output_stream)
    assert response["result"]["tools"][0]["name"] == "subagent_status"


def test_mcp_server_tool_call():
    request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "subagent_status", "arguments": {"verbose": True}},
    }
    input_stream = BytesIO(_encode_message(request))
    output_stream = BytesIO()

    def handler(**kwargs):
        return {"ok": kwargs}

    server = MCPServer(
        in_stream=input_stream,
        out_stream=output_stream,
        tool_handlers={"subagent_status": handler},
        tool_definitions=[{"name": "subagent_status", "inputSchema": {"type": "object"}}],
    )
    server.serve_forever()
    response = _decode_single_response(output_stream)
    assert response["result"]["structured"]["ok"]["verbose"] is True


def test_mcp_server_initialize():
    request = {"jsonrpc": "2.0", "id": 3, "method": "initialize", "params": {}}
    input_stream = BytesIO(_encode_message(request))
    output_stream = BytesIO()
    server = MCPServer(in_stream=input_stream, out_stream=output_stream, tool_handlers={})
    server.serve_forever()
    response = _decode_single_response(output_stream)
    assert response["result"]["serverInfo"]["name"] == "subagent"
