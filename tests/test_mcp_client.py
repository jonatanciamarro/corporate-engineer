import json
from pathlib import Path
from unittest.mock import MagicMock, patch

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
