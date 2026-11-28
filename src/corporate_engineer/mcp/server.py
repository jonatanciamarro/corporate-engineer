"""
Native Stdio MCP (Model Context Protocol) Server (IMP-0042 / ADR-036).
Zero-dependency JSON-RPC 2.0 newline-delimited stdio server exposing deterministic
corporate-engineer analysis and audit tools under strict workspace path confinement
and read-only least privilege by default.
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, TextIO

from corporate_engineer.eval.fixer import ASTSelfHealingFixer
from corporate_engineer.eval.scorecard import SemanticCodeEvaluator
from corporate_engineer.models import MCPServerCapabilitiesReport, MCPServerToolSpec
from corporate_engineer.quality.secret_scanner import CanonicalSecretScanner
from corporate_engineer.quality.surgical_runner import SurgicalTestRunner
from corporate_engineer.quality.wiring_auditor import CapabilityWiringAuditor
from corporate_engineer.rag.cached_ast_indexer import CachedASTCodebaseIndexer
from corporate_engineer.rag.impact import BlastRadiusAnalyzer

MCP_SERVER_NAME = "corporate-engineer-mcp"
MCP_SERVER_VERSION = "0.1.0"
MCP_PROTOCOL_VERSION = "2024-11-05"

_EXCLUDED_AST_DIRS: frozenset[str] = frozenset(
    {
        "venv",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        ".git",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
    }
)

_TOOL_SPECS: tuple[MCPServerToolSpec, ...] = (
    MCPServerToolSpec(
        name="blast_radius",
        description=(
            "Compute reverse dependency blast radius and affected tests for a file or symbol."
        ),
        mutating=False,
        input_schema={
            "type": "object",
            "properties": {
                "target_file": {"type": "string"},
                "target_symbol": {"type": "string"},
                "max_depth": {"type": "integer", "default": 3},
            },
        },
    ),
    MCPServerToolSpec(
        name="eval_scorecard",
        description="Evaluate Python modules against the 5-axis corporate EDD scorecard.",
        mutating=False,
        input_schema={
            "type": "object",
            "properties": {
                "target_path": {"type": "string", "default": "."},
                "min_score": {"type": "number", "default": 80.0},
            },
        },
    ),
    MCPServerToolSpec(
        name="audit_wiring",
        description=(
            "Audit repository auto-wiring across __all__, tests, CLI registration, "
            "and prompt refiner."
        ),
        mutating=False,
        input_schema={
            "type": "object",
            "properties": {"workspace_path": {"type": "string", "default": "."}},
        },
    ),
    MCPServerToolSpec(
        name="secret_scan",
        description="Scan workspace files for leaked credentials returning masked findings only.",
        mutating=False,
        input_schema={
            "type": "object",
            "properties": {"target_path": {"type": "string", "default": "."}},
        },
    ),
    MCPServerToolSpec(
        name="surgical_tests_plan",
        description=(
            "Plan affected pytest suites from git changes or changed_files without "
            "executing arbitrary commands."
        ),
        mutating=False,
        input_schema={
            "type": "object",
            "properties": {
                "base_branch": {"type": "string", "default": "main"},
                "max_depth": {"type": "integer", "default": 3},
                "changed_files": {"type": "array", "items": {"type": "string"}},
                "fallback_all": {"type": "boolean", "default": False},
            },
        },
    ),
    MCPServerToolSpec(
        name="ast_symbols",
        description=(
            "Extract cached AST classes, methods, functions, and calls for workspace Python files."
        ),
        mutating=False,
        input_schema={
            "type": "object",
            "properties": {"target_path": {"type": "string", "default": "."}},
        },
    ),
    MCPServerToolSpec(
        name="fix_auto",
        description=(
            "Apply conservative AST self-healing transformations (requires allow_mutations=True)."
        ),
        mutating=True,
        input_schema={
            "type": "object",
            "properties": {
                "target_path": {"type": "string", "default": "."},
                "dry_run": {"type": "boolean", "default": False},
            },
        },
    ),
)

ToolHandler = Callable[[dict[str, Any]], dict[str, Any]]


def _success_response(req_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    """Build a JSON-RPC 2.0 success response envelope."""
    payload: dict[str, Any] = {"jsonrpc": "2.0", "id": req_id, "result": result}
    return payload


def _error_response(req_id: Any, code: int, message: str) -> dict[str, Any]:
    """Build a JSON-RPC 2.0 error response envelope."""
    payload: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": code, "message": message},
    }
    return payload


def _tool_text_response(req_id: Any, data: dict[str, Any], *, is_error: bool) -> dict[str, Any]:
    """Wrap a tool execution payload inside an MCP tools/call result envelope."""
    result_obj: dict[str, Any] = {
        "content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False)}],
        "isError": is_error,
    }
    return _success_response(req_id, result_obj)


class CorporateEngineerMCPServer:
    """Zero-dependency JSON-RPC 2.0 stdio MCP server for corporate-engineer tools."""

    def __init__(
        self,
        workspace_root: str | Path = ".",
        allow_mutations: bool = False,
    ) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.allow_mutations = bool(allow_mutations)
        self.server_name = MCP_SERVER_NAME
        self.protocol_version = MCP_PROTOCOL_VERSION
        self._tool_catalog = self._build_tool_catalog()

    def _resolve_safe_path(
        self,
        raw_path: str | None,
        default_subpath: str = ".",
    ) -> Path:
        """Resolve a user-supplied path strictly within workspace_root."""
        candidate_str = default_subpath if raw_path is None else str(raw_path).strip()
        if "\x00" in candidate_str:
            raise PermissionError("Path traversal detected: null byte in path.")
        if not candidate_str:
            candidate_str = default_subpath

        candidate = Path(candidate_str)
        resolved = (
            candidate.resolve()
            if candidate.is_absolute()
            else (self.workspace_root / candidate).resolve()
        )
        try:
            resolved.relative_to(self.workspace_root)
        except ValueError as exc:
            raise PermissionError(
                f"Path traversal detected: '{raw_path}' escapes workspace root."
            ) from exc
        return resolved

    def _build_tool_catalog(self) -> dict[str, tuple[MCPServerToolSpec, ToolHandler]]:
        """Bind immutable tool specifications to their handler methods."""
        handlers: dict[str, ToolHandler] = {
            "blast_radius": self._tool_blast_radius,
            "eval_scorecard": self._tool_eval_scorecard,
            "audit_wiring": self._tool_audit_wiring,
            "secret_scan": self._tool_secret_scan,
            "surgical_tests_plan": self._tool_surgical_tests_plan,
            "ast_symbols": self._tool_ast_symbols,
            "fix_auto": self._tool_fix_auto,
        }
        return {spec.name: (spec, handlers[spec.name]) for spec in _TOOL_SPECS}

    def _active_specs(self) -> list[MCPServerToolSpec]:
        """Return tool specs visible under current mutation policy."""
        return [
            spec
            for spec, _ in self._tool_catalog.values()
            if self.allow_mutations or not spec.mutating
        ]

    def get_capabilities(self) -> MCPServerCapabilitiesReport:
        """Return structured Pydantic v2 capabilities report for this server instance."""
        return MCPServerCapabilitiesReport(
            server_name=self.server_name,
            protocol_version=self.protocol_version,
            workspace_root=str(self.workspace_root),
            allow_mutations=self.allow_mutations,
            registered_tools=[spec.name for spec in self._active_specs()],
        )

    def list_tools(self) -> list[dict[str, Any]]:
        """Return MCP-formatted tool definitions allowed by the current policy."""
        return [
            {
                "name": spec.name,
                "description": spec.description,
                "inputSchema": spec.input_schema,
            }
            for spec in self._active_specs()
        ]

    def handle_request(self, request: Any) -> dict[str, Any] | None:
        """Process a single JSON-RPC 2.0 message, returning None for notifications."""
        envelope_err, req_id, method = self._validate_envelope(request)
        if envelope_err is not None:
            return envelope_err
        if req_id is None:
            return None

        params_err, params = self._extract_params(request, req_id)
        if params_err is not None:
            return params_err
        return self._dispatch_method(req_id, method, params)

    @staticmethod
    def _validate_envelope(request: Any) -> tuple[dict[str, Any] | None, Any, str]:
        """Validate JSON-RPC 2.0 envelope fields and distinguish notifications."""
        if not isinstance(request, dict):
            return _error_response(None, -32600, "Invalid Request: expected JSON object."), None, ""

        req_id = request.get("id")
        err_id = req_id if "id" in request else None
        if request.get("jsonrpc") != "2.0":
            return (
                _error_response(err_id, -32600, "Invalid Request: jsonrpc must be '2.0'."),
                None,
                "",
            )

        method = request.get("method")
        if not isinstance(method, str) or not method.strip():
            return (
                _error_response(err_id, -32600, "Invalid Request: method must be a string."),
                None,
                "",
            )
        return None, req_id, method

    @staticmethod
    def _extract_params(
        request: dict[str, Any], req_id: Any
    ) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        """Validate optional JSON-RPC params object."""
        raw_params = request.get("params")
        if raw_params is None:
            return None, {}
        if isinstance(raw_params, dict):
            return None, raw_params
        return _error_response(req_id, -32602, "Invalid params: expected JSON object."), {}

    def _dispatch_method(self, req_id: Any, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a validated JSON-RPC request to the matching MCP handler."""
        if method == "initialize":
            result_obj: dict[str, Any] = {
                "protocolVersion": self.protocol_version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": self.server_name, "version": MCP_SERVER_VERSION},
            }
            return _success_response(req_id, result_obj)
        if method == "ping":
            ping_obj: dict[str, Any] = {
                "status": "ok",
                "server": self.server_name,
                "workspace_root": str(self.workspace_root),
                "allow_mutations": self.allow_mutations,
            }
            return _success_response(req_id, ping_obj)
        if method == "tools/list":
            list_obj: dict[str, Any] = {"tools": self.list_tools()}
            return _success_response(req_id, list_obj)
        if method == "tools/call":
            return self._handle_tools_call(req_id, params)
        return _error_response(req_id, -32601, f"Method not found: {method}")

    def _handle_tools_call(self, req_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Validate tool call params and enforce read/mutation policy before execution."""
        parse_err, tool_name, arguments = self._parse_call_params(req_id, params)
        if parse_err is not None:
            return parse_err

        entry = self._tool_catalog.get(tool_name)
        if entry is None:
            return _tool_text_response(
                req_id, {"error": f"Unknown MCP tool: '{tool_name}'."}, is_error=True
            )

        spec, handler = entry
        if spec.mutating and not self.allow_mutations:
            msg = (
                f"Tool '{tool_name}' is disabled: server is in read-only mode "
                "(allow_mutations=False)."
            )
            return _tool_text_response(req_id, {"error": msg}, is_error=True)

        return self._execute_tool_handler(req_id, tool_name, handler, arguments)

    @staticmethod
    def _parse_call_params(
        req_id: Any, params: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, str, dict[str, Any]]:
        """Validate tools/call name and arguments fields."""
        tool_name = params.get("name")
        if not isinstance(tool_name, str) or not tool_name.strip():
            return (
                _error_response(req_id, -32602, "Invalid params: 'name' must be a string."),
                "",
                {},
            )

        raw_args = params.get("arguments")
        if raw_args is None:
            return None, tool_name, {}
        if isinstance(raw_args, dict):
            return None, tool_name, raw_args
        return (
            _error_response(req_id, -32602, "Invalid params: 'arguments' must be a JSON object."),
            "",
            {},
        )

    @staticmethod
    def _execute_tool_handler(
        req_id: Any,
        tool_name: str,
        handler: ToolHandler,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a tool handler with stdout redirected to stderr for stdio frame safety."""
        try:
            with contextlib.redirect_stdout(sys.stderr):
                payload = handler(arguments)
        except (PermissionError, ValueError, FileNotFoundError, OSError) as exc:
            return _tool_text_response(req_id, {"error": str(exc)}, is_error=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[mcp-server] Tool '{tool_name}' error: {exc}", file=sys.stderr)
            return _tool_text_response(
                req_id,
                {"error": f"Tool execution error ({type(exc).__name__}): {exc}"},
                is_error=True,
            )
        return _tool_text_response(req_id, payload, is_error=False)

    def serve(self, stdin: TextIO | None = None, stdout: TextIO | None = None) -> int:
        """Run the newline-delimited JSON-RPC 2.0 stdio loop until EOF."""
        in_stream = stdin if stdin is not None else sys.stdin
        out_stream = stdout if stdout is not None else sys.stdout

        try:
            while True:
                raw_line = in_stream.readline()
                if raw_line == "":
                    break
                self._process_raw_line(raw_line, out_stream)
        except BrokenPipeError:
            return 0
        return 0

    def _process_raw_line(self, raw_line: str, out_stream: TextIO) -> None:
        """Parse one stdin line and emit any JSON-RPC response onto stdout."""
        if not raw_line.strip():
            return
        try:
            request_obj = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            self._write_frame(out_stream, _error_response(None, -32700, f"Parse error: {exc}"))
            return

        response = self.handle_request(request_obj)
        if response is not None:
            self._write_frame(out_stream, response)

    @staticmethod
    def _write_frame(out_stream: TextIO, response: dict[str, Any]) -> None:
        """Serialize and flush a single JSON-RPC 2.0 frame onto stdout."""
        out_stream.write(json.dumps(response, ensure_ascii=False) + "\n")
        out_stream.flush()

    def _to_rel_posix(self, path: Path) -> str:
        """Convert an already-confined path to workspace-relative POSIX notation."""
        rel = str(path.relative_to(self.workspace_root)).replace("\\", "/")
        return rel if rel else "."

    def _tool_blast_radius(self, args: dict[str, Any]) -> dict[str, Any]:
        """Execute BlastRadiusAnalyzer for target_file or target_symbol."""
        raw_file = args.get("target_file")
        raw_symbol = args.get("target_symbol")
        max_depth = int(args.get("max_depth", 3))

        rel_file: str | None = None
        if raw_file is not None and str(raw_file).strip():
            rel_file = self._to_rel_posix(self._resolve_safe_path(str(raw_file)))

        symbol = (
            str(raw_symbol).strip() if raw_symbol is not None and str(raw_symbol).strip() else None
        )
        if rel_file is None and symbol is None:
            raise ValueError("blast_radius requires 'target_file' or 'target_symbol'.")

        analyzer = BlastRadiusAnalyzer(workspace_root=self.workspace_root)
        report = analyzer.analyze_impact(
            target_symbol=symbol,
            target_file=rel_file,
            max_depth=max_depth,
        )
        return report.model_dump()

    def _tool_eval_scorecard(self, args: dict[str, Any]) -> dict[str, Any]:
        """Execute SemanticCodeEvaluator on a confined file or directory."""
        raw_target = args.get("target_path", ".")
        min_score = float(args.get("min_score", 80.0))
        safe_target = self._resolve_safe_path(str(raw_target), default_subpath=".")
        if not safe_target.exists():
            raise FileNotFoundError(f"Target path does not exist: {raw_target}")

        evaluator = SemanticCodeEvaluator(workspace_root=self.workspace_root)
        if safe_target.is_file():
            content = safe_target.read_text(encoding="utf-8", errors="ignore")
            report = evaluator.evaluate_source(
                content,
                file_path=self._to_rel_posix(safe_target),
                min_passing_score=min_score,
            )
        else:
            report = evaluator.evaluate_directory(safe_target, min_passing_score=min_score)
        return report.model_dump()

    def _tool_audit_wiring(self, args: dict[str, Any]) -> dict[str, Any]:
        """Execute CapabilityWiringAuditor across the confined workspace."""
        raw_ws = args.get("workspace_path")
        safe_ws = (
            self._resolve_safe_path(str(raw_ws), default_subpath=".")
            if raw_ws is not None
            else self.workspace_root
        )
        report = CapabilityWiringAuditor(workspace_root=safe_ws).audit()
        return report.model_dump()

    def _tool_secret_scan(self, args: dict[str, Any]) -> dict[str, Any]:
        """Execute CanonicalSecretScanner returning masked findings only."""
        raw_target = args.get("target_path", ".")
        safe_target = self._resolve_safe_path(str(raw_target), default_subpath=".")
        if not safe_target.exists():
            raise FileNotFoundError(f"Target path does not exist: {raw_target}")

        scanner = CanonicalSecretScanner()
        if safe_target.is_file():
            findings = scanner.scan_file(safe_target)
            rel_file = self._to_rel_posix(safe_target)
            for item in findings:
                item["file"] = rel_file
        else:
            findings = scanner.scan_directory(safe_target)

        payload: dict[str, Any] = {
            "target_path": self._to_rel_posix(safe_target),
            "passed": len(findings) == 0,
            "total_findings": len(findings),
            "findings": findings,
        }
        return payload

    def _tool_surgical_tests_plan(self, args: dict[str, Any]) -> dict[str, Any]:
        """Compute affected surgical tests in dry_run mode."""
        base_branch = str(args.get("base_branch", "main"))
        max_depth = int(args.get("max_depth", 3))
        fallback_all = bool(args.get("fallback_all", False))
        raw_changed = args.get("changed_files")

        normalized_changed: list[str] | None = None
        if raw_changed is not None:
            if not isinstance(raw_changed, list):
                raise ValueError("'changed_files' must be a list of relative file paths.")
            normalized_changed = [
                self._to_rel_posix(self._resolve_safe_path(str(item))) for item in raw_changed
            ]

        runner = SurgicalTestRunner(root_path=self.workspace_root)
        report = runner.run(
            base_branch=base_branch,
            max_depth=max_depth,
            dry_run=True,
            changed_files=normalized_changed,
            fallback_all=fallback_all,
        )
        return report.model_dump()

    def _tool_ast_symbols(self, args: dict[str, Any]) -> dict[str, Any]:
        """Extract cached AST symbols for a confined Python file or directory."""
        raw_target = args.get("target_path", ".")
        safe_target = self._resolve_safe_path(str(raw_target), default_subpath=".")
        if not safe_target.exists():
            raise FileNotFoundError(f"Target path does not exist: {raw_target}")

        indexer = CachedASTCodebaseIndexer(root_path=self.workspace_root)
        files_payload = self._collect_ast_files(indexer, safe_target)
        payload: dict[str, Any] = {
            "target_path": self._to_rel_posix(safe_target),
            "total_files": len(files_payload),
            "total_symbols": sum(len(item["symbols"]) for item in files_payload),
            "files": files_payload,
        }
        return payload

    def _collect_ast_files(
        self, indexer: CachedASTCodebaseIndexer, safe_target: Path
    ) -> list[dict[str, Any]]:
        """Collect AST symbols across a single Python file or directory tree."""
        if safe_target.is_file():
            return [
                {
                    "file": self._to_rel_posix(safe_target),
                    "symbols": indexer.get_file_symbols(safe_target),
                }
            ]

        files_payload: list[dict[str, Any]] = []
        for root, dirs, files in os.walk(safe_target):
            dirs[:] = sorted(
                d for d in dirs if not d.startswith(".") and d not in _EXCLUDED_AST_DIRS
            )
            for fname in sorted(files):
                if not fname.endswith(".py"):
                    continue
                py_file = Path(root) / fname
                files_payload.append(
                    {
                        "file": self._to_rel_posix(py_file),
                        "symbols": indexer.get_file_symbols(py_file),
                    }
                )
        return files_payload

    def _tool_fix_auto(self, args: dict[str, Any]) -> dict[str, Any]:
        """Apply conservative AST fixes when allow_mutations=True."""
        raw_target = args.get("target_path", ".")
        dry_run = bool(args.get("dry_run", False))
        safe_target = self._resolve_safe_path(str(raw_target), default_subpath=".")
        if not safe_target.exists():
            raise FileNotFoundError(f"Target path does not exist: {raw_target}")

        fixer = ASTSelfHealingFixer()
        report = (
            fixer.fix_file(safe_target, dry_run=dry_run)
            if safe_target.is_file()
            else fixer.fix_workspace(safe_target, dry_run=dry_run)
        )
        return report.model_dump()
