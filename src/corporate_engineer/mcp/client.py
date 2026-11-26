"""
Local and Remote MCP Tool Adapters for sandboxed execution and remote SSE connectivity.
"""

import json
import os
import shlex
import shutil
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
SHELL_METACHARACTERS: tuple[str, ...] = (
    "&&",
    "||",
    ";",
    "|",
    ">",
    "<",
    "`",
    "$(",
    "\n",
    "\r",
)
INTERPRETER_INLINE_FLAGS: frozenset[str] = frozenset({"-c", "--command", "-e", "--eval", "-"})


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
        if any(meta in cmd for meta in SHELL_METACHARACTERS):
            return MCPToolResult(
                tool_name="run_command",
                is_error=True,
                content=f"Command blocked by security allowlist: shell metacharacter detected in '{cmd}'",
            )
        try:
            tokens = shlex.split(cmd, posix=(os.name != "nt"))
        except ValueError as exc:
            return MCPToolResult(
                tool_name="run_command",
                is_error=True,
                content=f"Command blocked by security allowlist: invalid command syntax ({exc})",
            )
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
        if base_bin.startswith("python"):
            for arg in tokens[1:]:
                arg_lower = arg.strip("\"'").lower()
                if arg_lower in INTERPRETER_INLINE_FLAGS or arg_lower.startswith(
                    ("-c", "-e", "--command=", "--eval=")
                ):
                    return MCPToolResult(
                        tool_name="run_command",
                        is_error=True,
                        content=(
                            "Command blocked by security allowlist: "
                            "inline interpreter execution is prohibited."
                        ),
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

        resolved_cmd = list(tokens)
        if base_bin in ("python", "python3") and not Path(raw_bin).is_absolute():
            resolved_cmd[0] = sys.executable
        else:
            located = shutil.which(raw_bin, path=env["PATH"])
            if located:
                resolved_cmd[0] = located

        try:
            res = subprocess.run(
                resolved_cmd,
                check=False,
                shell=False,
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

    @staticmethod
    def _extract_content_type(resp: Any) -> str:
        """Safely extract Content-Type header as a real str, ignoring mock objects."""
        headers = getattr(resp, "headers", None)
        if headers is None:
            return ""
        get_header = getattr(headers, "get", None)
        if callable(get_header):
            for key in ("Content-Type", "content-type"):
                value = get_header(key)
                if isinstance(value, str):
                    return value
        if isinstance(headers, dict):
            for key, value in headers.items():
                if (
                    isinstance(key, str)
                    and key.lower() == "content-type"
                    and isinstance(value, str)
                ):
                    return value
        return ""

    @staticmethod
    def _looks_like_sse(raw_text: str) -> bool:
        """Return True when non-JSON text contains SSE data: or event: frame headers."""
        normalized = raw_text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
        return any(line.startswith(("data:", "event:")) for line in normalized.split("\n"))

    @staticmethod
    def _extract_sse_events(raw_text: str) -> list[str]:
        """Split an SSE stream into concatenated data payloads per blank-line event block."""
        normalized = raw_text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
        events: list[str] = []
        data_lines: list[str] = []

        for line in normalized.split("\n"):
            if line == "":
                if data_lines:
                    events.append("\n".join(data_lines))
                    data_lines = []
                continue
            if line.startswith(":"):
                continue
            if line.startswith("data:"):
                data_lines.append(line.removeprefix("data:").removeprefix(" "))

        if data_lines:
            events.append("\n".join(data_lines))
        return events

    @staticmethod
    def _parse_sse_payload(raw_text: str, request_id: int | str = 1) -> dict[str, Any]:
        """Parse an HTTP text/event-stream body and select the matching JSON-RPC payload."""
        parsed_dicts: list[dict[str, Any]] = []
        for event_payload in RemoteMCPSSEClient._extract_sse_events(raw_text):
            stripped_payload = event_payload.strip()
            if not stripped_payload or stripped_payload == "[DONE]":
                continue
            try:
                parsed = json.loads(stripped_payload)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                parsed_dicts.append(parsed)

        if not parsed_dicts:
            raise ValueError("SSE stream contained no valid JSON-RPC payload.")

        matching_id_response: dict[str, Any] | None = None
        matching_id: dict[str, Any] | None = None
        result_or_error: dict[str, Any] | None = None

        for item in parsed_dicts:
            has_body = "result" in item or "error" in item
            item_id = item.get("id")
            id_matches = (
                "id" in item
                and item_id is not None
                and not isinstance(item_id, bool)
                and not isinstance(request_id, bool)
                and item_id == request_id
            )
            if id_matches:
                matching_id = item
                if has_body:
                    matching_id_response = item
            if has_body:
                result_or_error = item

        if matching_id_response is not None:
            return matching_id_response
        if matching_id is not None:
            return matching_id
        if result_or_error is not None:
            return result_or_error
        return parsed_dicts[-1]

    @staticmethod
    def _parse_response_payload(
        raw_text: str,
        content_type: str = "",
        request_id: int | str = 1,
    ) -> dict[str, Any]:
        """Parse either JSON-RPC or text/event-stream HTTP response payloads."""
        normalized_ct = content_type.lower() if isinstance(content_type, str) else ""
        if "text/event-stream" in normalized_ct:
            return RemoteMCPSSEClient._parse_sse_payload(raw_text, request_id=request_id)

        stripped = raw_text.lstrip("\ufeff").strip()
        if not stripped:
            raise ValueError("Empty MCP response payload.")

        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as exc:
            if RemoteMCPSSEClient._looks_like_sse(raw_text):
                return RemoteMCPSSEClient._parse_sse_payload(raw_text, request_id=request_id)
            raise ValueError(f"Malformed JSON MCP response payload: {exc}") from exc

        if isinstance(parsed, dict):
            return parsed
        raise ValueError(
            f"Invalid MCP JSON-RPC payload: expected object, got {type(parsed).__name__}."
        )

    @staticmethod
    def _is_protocol_error(res: dict[str, Any]) -> bool:
        if "error" in res:
            return True
        result_data = res.get("result")
        return isinstance(result_data, dict) and bool(result_data.get("isError", False))

    def _send_request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.circuit_breaker and (not self.circuit_breaker.can_execute()):
            raise CircuitBreakerOpenError(
                f"Circuit breaker is OPEN: endpoint '{self.endpoint}' is temporarily unavailable."
            )
        request_id = 1
        payload = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.endpoint, data=data, headers=self.headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw_bytes = resp.read()
                raw_text: str = (
                    raw_bytes if isinstance(raw_bytes, str) else raw_bytes.decode("utf-8")
                )
                content_type = self._extract_content_type(resp)
                res = self._parse_response_payload(
                    raw_text,
                    content_type=content_type,
                    request_id=request_id,
                )
                if self.circuit_breaker and not self._is_protocol_error(res):
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
            result_data = res.get("result")
            if not isinstance(result_data, dict):
                return []
            tools = result_data.get("tools", [])
            return list(tools) if isinstance(tools, list) else []
        except (ConnectionError, CircuitBreakerOpenError):
            return []

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> MCPToolResult:
        try:
            res = self._send_request("tools/call", {"name": tool_name, "arguments": arguments})
            if "error" in res:
                error_obj = res.get("error", {})
                error_msg = (
                    error_obj.get("message", str(error_obj))
                    if isinstance(error_obj, dict)
                    else str(error_obj)
                )
                if self.circuit_breaker:
                    self.circuit_breaker.record_failure()
                return MCPToolResult(
                    tool_name=tool_name,
                    is_error=True,
                    content=f"JSON-RPC Error: {error_msg}",
                )

            result_data = res.get("result", {})
            if not isinstance(result_data, dict):
                result_data = {}
            content_list = result_data.get("content", [])
            is_error = bool(result_data.get("isError", False))
            if is_error and self.circuit_breaker:
                self.circuit_breaker.record_failure()
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
