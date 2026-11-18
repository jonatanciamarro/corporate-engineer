from pathlib import Path

from corporate_engineer.mcp.client import LocalMCPToolAdapter
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
