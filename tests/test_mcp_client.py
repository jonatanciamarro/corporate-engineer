import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from corporate_engineer.mcp.circuit_breaker import CircuitBreaker, CircuitState
from corporate_engineer.mcp.client import LocalMCPToolAdapter, RemoteMCPSSEClient
from corporate_engineer.models import MCPToolCall


def test_mcp_read_write_file(tmp_path: Path):
    adapter = LocalMCPToolAdapter(workspace_root=tmp_path)

    # Write file
    write_call = MCPToolCall(
        server_name="filesystem",
        tool_name="write_file",
        arguments={"path": "hello.txt", "content": "Hello Corporate World!"},
    )
    write_res = adapter.execute(write_call)
    assert write_res.is_error is False
    assert (tmp_path / "hello.txt").exists()

    # Read file
    read_call = MCPToolCall(
        server_name="filesystem",
        tool_name="read_file",
        arguments={"path": "hello.txt"},
    )
    read_res = adapter.execute(read_call)
    assert read_res.is_error is False
    assert read_res.content == "Hello Corporate World!"


def test_mcp_path_traversal_protection(tmp_path: Path):
    adapter = LocalMCPToolAdapter(workspace_root=tmp_path)

    # Attempt path traversal
    escape_call = MCPToolCall(
        server_name="filesystem",
        tool_name="read_file",
        arguments={"path": "../../sensitive.txt"},
    )
    res = adapter.execute(escape_call)
    assert res.is_error is True
    assert "Path traversal detected" in res.content


def test_mcp_command_allowlist(tmp_path: Path):
    adapter = LocalMCPToolAdapter(workspace_root=tmp_path)

    # Safe command
    safe_call = MCPToolCall(
        server_name="shell",
        tool_name="run_command",
        arguments={"command": "python --version"},
    )
    res = adapter.execute(safe_call)
    assert res.is_error is False

    # Blocked dangerous command
    blocked_call = MCPToolCall(
        server_name="shell",
        tool_name="run_command",
        arguments={"command": "rm -rf /"},
    )
    res_blocked = adapter.execute(blocked_call)
    assert res_blocked.is_error is True
    assert "Command blocked by security allowlist" in res_blocked.content


def test_mcp_shell_blocks_injection_and_inline_execution(tmp_path: Path):
    adapter = LocalMCPToolAdapter(workspace_root=tmp_path)
    malicious_commands = [
        "pytest && whoami",
        "pytest || whoami",
        "pytest; whoami",
        "git status | cat",
        "python --version > leaked.txt",
        "python `whoami`",
        "python $(whoami)",
        'python -c "import os; print(os.getcwd())"',
        'python3 --command "print(1)"',
        'python -e "print(1)"',
        "python -",
    ]
    with patch("corporate_engineer.mcp.client.subprocess.run") as mock_run:
        for cmd in malicious_commands:
            call = MCPToolCall(
                server_name="shell",
                tool_name="run_command",
                arguments={"command": cmd},
            )
            res = adapter.execute(call)
            assert res.is_error is True, f"Expected block for: {cmd}"
            assert "Command blocked" in res.content
        mock_run.assert_not_called()


def test_mcp_shell_executes_with_shell_false(tmp_path: Path):
    adapter = LocalMCPToolAdapter(workspace_root=tmp_path)
    safe_call = MCPToolCall(
        server_name="shell",
        tool_name="run_command",
        arguments={"command": "python --version"},
    )
    mock_proc = MagicMock(returncode=0, stdout="Python 3.11.9\n", stderr="")
    with patch("corporate_engineer.mcp.client.subprocess.run", return_value=mock_proc) as mock_run:
        res = adapter.execute(safe_call)
    assert res.is_error is False
    assert mock_run.called
    call_args, call_kwargs = mock_run.call_args
    assert isinstance(call_args[0], list)
    assert call_kwargs.get("shell") is False


def test_local_mcp_list_tools(tmp_path: Path):
    adapter = LocalMCPToolAdapter(workspace_root=tmp_path)
    tools = adapter.list_tools()
    tool_names = [t["name"] for t in tools]
    assert "read_file" in tool_names
    assert "write_file" in tool_names
    assert "run_command" in tool_names


def test_local_mcp_ping(tmp_path: Path):
    adapter = LocalMCPToolAdapter(workspace_root=tmp_path)
    status = adapter.ping()
    assert status["status"] == "ok"
    assert status["mode"] == "local"


def test_remote_mcp_client_auth_and_url():
    client = RemoteMCPSSEClient(endpoint="https://mcp.internal/sse", auth_token="bearer-token-123")
    assert client.endpoint == "https://mcp.internal/sse"
    assert client.auth_token == "bearer-token-123"
    assert client.headers["Authorization"] == "Bearer bearer-token-123"


def test_remote_mcp_client_list_tools_mock():
    client = RemoteMCPSSEClient(endpoint="https://mcp.internal/sse")
    mock_resp_data = {
        "jsonrpc": "2.0",
        "result": {
            "tools": [
                {
                    "name": "query_db",
                    "description": "Execute database query",
                    "inputSchema": {"type": "object"},
                }
            ]
        },
        "id": 1,
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_resp_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        tools = client.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "query_db"


def test_remote_mcp_client_call_tool_mock():
    client = RemoteMCPSSEClient(endpoint="https://mcp.internal/sse")
    mock_resp_data = {
        "jsonrpc": "2.0",
        "result": {
            "content": [{"type": "text", "text": "Query results: 42 rows"}],
            "isError": False,
        },
        "id": 1,
    }

    mock_resp = MagicMock()
    mock_resp.read.return_value = json.dumps(mock_resp_data).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = client.call_tool("query_db", {"query": "SELECT * FROM metrics"})
        assert res.is_error is False
        assert "Query results: 42 rows" in res.content


def test_remote_mcp_client_connection_error():
    client = RemoteMCPSSEClient(endpoint="http://127.0.0.1:59999/sse", timeout=0.5)
    res = client.call_tool("ping", {})
    assert res.is_error is True
    assert "Connection error" in res.content or "failed" in res.content


def _make_mock_http_response(
    body: str, headers: dict[str, str] | MagicMock | None = None
) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.read.return_value = body.encode("utf-8")
    if headers is not None:
        mock_resp.headers = headers
    mock_resp.__enter__.return_value = mock_resp
    return mock_resp


def test_remote_mcp_client_sse_list_tools_multi_event():
    breaker = CircuitBreaker(failure_threshold=2)
    client = RemoteMCPSSEClient(endpoint="https://mcp.internal/sse", circuit_breaker=breaker)
    sse_body = (
        ": keepalive\r\n\r\n"
        "event: endpoint\r\n"
        "data: /messages?session_id=abc123\r\n\r\n"
        "event: message\r\n"
        'data: {"jsonrpc": "2.0", "method": "notifications/progress", "params": {"progress": 50}}\r\n\r\n'
        "event: message\r\n"
        'data: {"jsonrpc": "2.0",\r\n'
        'data:  "id": 1,\r\n'
        'data:  "result": {"tools": [{"name": "search_docs", "description": "Search"}]}}\r\n\r\n'
        "data: [DONE]\r\n\r\n"
    )
    mock_resp = _make_mock_http_response(
        sse_body, headers={"Content-Type": "text/event-stream; charset=utf-8"}
    )

    with patch("urllib.request.urlopen", return_value=mock_resp):
        tools = client.list_tools()

    assert len(tools) == 1
    assert tools[0]["name"] == "search_docs"
    assert breaker.state == CircuitState.CLOSED
    assert breaker.failure_count == 0


def test_remote_mcp_client_sse_call_tool_multiline_and_magicmock_headers():
    client = RemoteMCPSSEClient(endpoint="https://mcp.internal/sse")
    sse_body = (
        ": ping\n\n"
        "event: message\n"
        'data: {"jsonrpc": "2.0",\n'
        'data:  "id": 1,\n'
        'data:  "result": {"content": [{"type": "text", "text": "SSE multi-line ok"}], "isError": false}}\n\n'
    )
    # Default MagicMock headers simulate existing tests where headers.get(...) is not a str
    mock_resp = _make_mock_http_response(sse_body)

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = client.call_tool("query_db", {"query": "SELECT 1"})

    assert res.is_error is False
    assert res.content == "SSE multi-line ok"


def test_remote_mcp_client_sse_jsonrpc_error_records_circuit_failure():
    breaker = CircuitBreaker(failure_threshold=2)
    client = RemoteMCPSSEClient(endpoint="https://mcp.internal/sse", circuit_breaker=breaker)
    sse_error_body = (
        "event: message\n"
        'data: {"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "Tool execution denied"}}\n\n'
    )

    with patch(
        "urllib.request.urlopen",
        side_effect=[
            _make_mock_http_response(sse_error_body, headers={"Content-Type": "text/event-stream"}),
            _make_mock_http_response(sse_error_body, headers={"Content-Type": "text/event-stream"}),
        ],
    ):
        res1 = client.call_tool("restricted_tool", {})
        assert res1.is_error is True
        assert "Tool execution denied" in res1.content
        assert breaker.failure_count == 1
        assert breaker.state == CircuitState.CLOSED

        res2 = client.call_tool("restricted_tool", {})
        assert res2.is_error is True
        assert breaker.failure_count == 2
        assert breaker.state == CircuitState.OPEN


@pytest.mark.parametrize(
    ("body", "content_type"),
    [
        (": keepalive\n\n", "text/event-stream"),
        ("data: [DONE]\n\n", "text/event-stream"),
        ("data: [1, 2, 3]\n\n", "text/event-stream"),
        ("event: message\ndata: {not valid json\n\n", "text/event-stream"),
        ("{malformed json", "application/json"),
        ("[1, 2, 3]", "application/json"),
        ("", "application/json"),
    ],
)
def test_remote_mcp_client_malformed_or_empty_payload_trips_circuit(
    body: str, content_type: str
) -> None:
    breaker = CircuitBreaker(failure_threshold=2)
    client = RemoteMCPSSEClient(endpoint="https://mcp.internal/sse", circuit_breaker=breaker)
    mock_resp = _make_mock_http_response(body, headers={"Content-Type": content_type})

    with patch("urllib.request.urlopen", return_value=mock_resp), pytest.raises(ConnectionError):
        client._send_request("tools/list")

    assert breaker.failure_count == 1

    with patch("urllib.request.urlopen", return_value=mock_resp):
        res = client.call_tool("ping", {})

    assert res.is_error is True
    assert "Connection error" in res.content
    assert breaker.failure_count == 2
    assert breaker.state == CircuitState.OPEN


def test_parse_sse_payload_prefers_matching_request_id_and_preserves_multiline_spacing():
    sse_payload = (
        "event: message\n"
        'data: {"jsonrpc": "2.0", "id": 1, "result": {"content": [{"type": "text", "text": "line1\\n line2"}]}}\n\n'
        "event: message\n"
        'data: {"jsonrpc": "2.0", "id": 2, "result": {"other": true}}\n\n'
        "event: message\n"
        'data: {"jsonrpc": "2.0", "method": "notifications/log", "params": {"msg": "trailing"}}\n\n'
    )
    parsed = RemoteMCPSSEClient._parse_sse_payload(sse_payload, request_id=1)
    assert parsed["id"] == 1
    assert parsed["result"]["content"][0]["text"] == "line1\n line2"

    # Multi-line data concatenates with "\n" and strips only a single optional space after "data:"
    multiline_json_sse = (
        'data:{"jsonrpc": "2.0",\ndata: "id": 7,\ndata:  "result": {"value": 42}}\n\n'
    )
    extracted = RemoteMCPSSEClient._extract_sse_events(multiline_json_sse)
    assert extracted == ['{"jsonrpc": "2.0",\n"id": 7,\n "result": {"value": 42}}']

    parsed_multi = RemoteMCPSSEClient._parse_response_payload(
        multiline_json_sse, content_type="text/event-stream", request_id=7
    )
    assert parsed_multi == {"jsonrpc": "2.0", "id": 7, "result": {"value": 42}}

    # Fallback without matching id picks the last JSON-RPC dict with "result" or "error"
    fallback_sse = (
        'data: {"jsonrpc": "2.0", "id": 99, "result": {"step": 1}}\n\n'
        'data: {"jsonrpc": "2.0", "method": "notifications/done"}\n\n'
    )
    parsed_fallback = RemoteMCPSSEClient._parse_sse_payload(fallback_sse, request_id=1)
    assert parsed_fallback == {"jsonrpc": "2.0", "id": 99, "result": {"step": 1}}


def test_remote_mcp_client_sse_ping():
    client = RemoteMCPSSEClient(endpoint="https://mcp.internal/sse")
    sse_ping_body = (
        'event: message\ndata: {"jsonrpc": "2.0", "id": 1, "result": {"alive": true}}\n\n'
    )
    mock_resp = _make_mock_http_response(
        sse_ping_body, headers={"content-type": "text/event-stream"}
    )

    with patch("urllib.request.urlopen", return_value=mock_resp):
        status = client.ping()

    assert status["status"] == "ok"
    assert status["response"] == {"alive": True}
