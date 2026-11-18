"""
Local MCP Tool Adapter for sandboxed execution of tools inside corporate workspaces.
"""

import os
import subprocess
import sys
from pathlib import Path

from corporate_engineer.models import MCPToolCall, MCPToolResult

# Deterministic allowlist of safe base commands
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
    def __init__(self, workspace_root: Path):
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
            return MCPToolResult(
                tool_name=tool_call.tool_name,
                is_error=True,
                content=str(e),
            )

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

        # Check security allowlist
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

        if base_bin not in SAFE_COMMAND_PREFIXES and not base_bin.startswith("python"):
            return MCPToolResult(
                tool_name="run_command",
                is_error=True,
                content=f"Command blocked by security allowlist: '{base_bin}' is not authorized.",
            )

        # Environment PATH enhancement for Python & Git if missing in subshell
        env = os.environ.copy()
        python_dir = str(Path(sys.executable).parent)
        git_dir = r"C:\Program Files\Git\cmd"
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
