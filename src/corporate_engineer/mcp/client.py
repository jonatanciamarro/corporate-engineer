"""
Local and Remote MCP Tool Adapters for sandboxed execution and remote SSE connectivity.
"""

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from corporate_engineer.mcp.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from corporate_engineer.models import MCPToolCall, MCPToolResult

SAFE_COMMAND_PREFIXES: set[str] = {
    "python",
    "pytest",
    "mypy",
    "ruff",
    "flake8",
    "git",
    "npm",
    "pnpm",
    "yarn",
    "tsc",
    "cargo",
    "go",
    "mvn",
    "gradle",
    "dotnet",
}
DISALLOWED_PATTERNS = [
    "rm -rf",
    "drop table",
    "drop database",
    "format ",
    ":(){ :|:& };:",
    "mkfs",
    "dd if=",
    "chmod 777",
    "shutdown",
    "reboot",
]


class LocalMCPToolAdapter:
    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.resolve()

    def _resolve_safe_path(self, relative_path: str) -> Path:
        resolved = (self.workspace_root / relative_path).resolve()
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError:
            raise PermissionError(
                f"Path traversal detected: {relative_path} escapes workspace root."
            )
        return resolved

    def ping(self) -> dict[str, Any]:
        return {"status": "ok", "mode": "local", "workspace": str(self.workspace_root)}

    def list_tools(self) -> list[dict[str, Any]]:
        return [
            {
                "name": "read_file",
                "server_name": "filesystem",
                "description": "Read contents of a file within the workspace",
                "inputSchema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
            {
                "name": "write_file",
                "server_name": "filesystem",
                "description": "Write contents to a file safely within the workspace",
                "inputSchema": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                    "required": ["path", "content"],
                },
            },
            {
                "name": "run_command",
                "server_name": "shell",
                "description": "Run an authorized developer command in the workspace",
                "inputSchema": {
                    "type": "object",
                    "properties": {"command": {"type": "string"}},
                    "required": ["command"],
                },
            },
        ]

    def execute(self, tool_call: MCPToolCall) -> MCPToolResult:
        try:
            if tool_call.server_name == "filesystem":
                return self._handle_filesystem(tool_call)
            elif tool_call.server_name == "shell":
                return self._handle_shell(tool_call)
            else:
                return MCPToolResult(
                    tool_name=tool_call.tool_name,
                    is_error=True,
                    content=f"Unsupported MCP server: {tool_call.server_name}",
                )
        except (OSError, PermissionError, ValueError) as e:
            return MCPToolResult(tool_name=tool_call.tool_name, is_error=True, content=str(e))

    def _handle_filesystem(self, call: MCPToolCall) -> MCPToolResult:
        args = call.arguments
        path_str = args.get("path", "")
        safe_path = self._resolve_safe_path(path_str)
        if call.tool_name == "read_file":
            if not safe_path.exists():
                return MCPToolResult(tool_name="read_file", is_error=True, content="File not found")
            content = safe_path.read_text(encoding="utf-8", errors="ignore")
            return MCPToolResult(tool_name="read_file", is_error=False, content=content)
        elif call.tool_name == "write_file":
            content = args.get("content", "")
            safe_path.parent.mkdir(parents=True, exist_ok=True)
            safe_path.write_text(content, encoding="utf-8")
            return MCPToolResult(
                tool_name="write_file", is_error=False, content=f"Wrote {len(content)} chars"
            )
        return MCPToolResult(
            tool_name=call.tool_name, is_error=True, content="Unknown filesystem tool"
        )

    def _handle_shell(self, call: MCPToolCall) -> MCPToolResult:
        cmd = call.arguments.get("command", "").strip()
        cmd_lower = cmd.lower()
        if any(bad in cmd_lower for bad in DISALLOWED_PATTERNS):
            return MCPToolResult(
                tool_name="run_command",
                is_error=True,
                content=f"Command blocked by security allowlist: dangerous pattern detected in '{cmd}'",
            )
        tokens = cmd.split()
        if not tokens:
            return MCPToolResult(tool_name="run_command", is_error=True, content="Empty command")
        raw_bin = tokens[0].strip("\"'")
        base_bin = Path(raw_bin).stem.lower()
        if base_bin not in SAFE_COMMAND_PREFIXES and (not base_bin.startswith("python")):
            return MCPToolResult(
                tool_name="run_command",
                is_error=True,
                content=f"Command blocked by security allowlist: '{base_bin}' is not authorized.",
            )
        env = os.environ.copy()
        python_dir = str(Path(sys.executable).parent)
        git_dir = "C:\\Program Files\\Git\\cmd"
        current_path = env.get("PATH", "")
        if python_dir not in current_path:
            current_path = f"{python_dir};{current_path}"
        if Path(git_dir).exists() and git_dir not in current_path:
            current_path = f"{git_dir};{current_path}"
        env["PATH"] = current_path
        try:
            res = subprocess.run(
                cmd,
                check=False,
                shell=True,
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
                timeout=60,
                env=env,
            )
            return MCPToolResult(
                tool_name="run_command",
                is_error=res.returncode != 0,
                content=res.stdout + ("\nSTDERR:\n" + res.stderr if res.stderr else ""),
            )
        except (subprocess.SubprocessError, OSError) as e:
            return MCPToolResult(tool_name="run_command", is_error=True, content=str(e))


class RemoteMCPSSEClient:
    """
    Client for remote MCP servers using Server-Sent Events (SSE) / JSON-RPC over HTTP.
    Supports corporate Bearer authentication, enterprise endpoint connectivity, and circuit breaker.
    """

    def __init__(
        self,
        endpoint: str,
        auth_token: str | None = None,
        timeout: float = 10.0,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.auth_token = auth_token
        self.timeout = timeout
        self.circuit_breaker = circuit_breaker
        self.headers: dict[str, str] = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": "CorporateEngineer-MCPClient/0.1.0",
        }
        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"

    def _send_request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.circuit_breaker and (not self.circuit_breaker.can_execute()):
            raise CircuitBreakerOpenError(
                f"Circuit breaker is OPEN: endpoint '{self.endpoint}' is temporarily unavailable."
            )
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.endpoint, data=data, headers=self.headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw_bytes = resp.read()
                res = json.loads(raw_bytes.decode("utf-8"))
                if self.circuit_breaker:
                    self.circuit_breaker.record_success()
                return res
        except Exception as e:
            if self.circuit_breaker:
                self.circuit_breaker.record_failure()
            raise ConnectionError(
                f"Connection error reaching MCP endpoint '{self.endpoint}': {e}"
            ) from e

    def ping(self) -> dict[str, Any]:
        try:
            res = self._send_request("ping")
            return {
                "status": "ok",
                "mode": "remote-sse",
                "endpoint": self.endpoint,
                "response": res.get("result", {}),
            }
        except (ConnectionError, CircuitBreakerOpenError) as e:
            return {
                "status": "error",
                "mode": "remote-sse",
                "endpoint": self.endpoint,
                "error": str(e),
            }

    def list_tools(self) -> list[dict[str, Any]]:
        try:
            res = self._send_request("tools/list")
            tools = res.get("result", {}).get("tools", [])
            return list(tools)
        except (ConnectionError, CircuitBreakerOpenError):
            return []

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        try:
            res = self._send_request("tools/call", {"name": tool_name, "arguments": arguments})
            result_data = res.get("result", {})
            content_list = result_data.get("content", [])
            is_error = bool(result_data.get("isError", False))
            text_parts = [
                item.get("text", "")
                for item in content_list
                if isinstance(item, dict) and item.get("type") == "text"
            ]
            content = "\n".join(text_parts) if text_parts else str(result_data)
            return MCPToolResult(tool_name=tool_name, is_error=is_error, content=content)
        except (ConnectionError, CircuitBreakerOpenError) as e:
            return MCPToolResult(
                tool_name=tool_name,
                is_error=True,
                content=f"Connection error calling remote tool '{tool_name}': {e}",
            )
