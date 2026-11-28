"""
tests/test_mcp_server_and_plugin.py - Shift-Left TDD Suite for IMP-0042 Pillar 1 (ADR-036).

Validates:
1. Frozen Pydantic v2 DTOs: MCPServerToolSpec and MCPServerCapabilitiesReport.
2. Public exports and PromptRefiner DOMAIN_KEYWORDS wiring for mcp/server.py.
3. CorporateEngineerMCPServer JSON-RPC 2.0 stdio protocol:
   initialize, notifications/initialized, ping, tools/list, tools/call for all 6 read/audit tools
   (blast_radius, eval_scorecard, audit_wiring, secret_scan, surgical_tests_plan, ast_symbols).
4. Security boundaries: path traversal rejection and allow_mutations=False gating fix_auto.
5. CLI `mcp serve [--workspace ...] [--allow-mutations]` parser and subprocess stdio handshake.
6. Workspace plugin manifests in .agents/plugins/corporate-engineer/{plugin.json,mcp_config.json}.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_DIR = WORKSPACE_ROOT / ".agents" / "plugins" / "corporate-engineer"
ALLOWED_PLUGIN_TOP_LEVEL_KEYS: frozenset[str] = frozenset(
    {
        "name",
        "description",
        "logo",
        "suggestedPrompts",
        "displayName",
        "version",
        "author",
        "homepage",
        "repository",
        "disabled",
    }
)
READ_AUDIT_TOOLS: frozenset[str] = frozenset(
    {
        "blast_radius",
        "eval_scorecard",
        "audit_wiring",
        "secret_scan",
        "surgical_tests_plan",
        "ast_symbols",
    }
)


def _create_sample_workspace(root: Path) -> None:
    """Create a clean mini Python workspace for deterministic MCP server tool calls."""
    src_pkg = root / "src" / "corporate_engineer"
    src_pkg.mkdir(parents=True)
    tests_dir = root / "tests"
    tests_dir.mkdir(parents=True)

    (src_pkg / "__init__.py").write_text(
        'from corporate_engineer.core import CoreEngine\n\n__all__ = ["CoreEngine"]\n',
        encoding="utf-8",
    )
    (src_pkg / "core.py").write_text(
        "class CoreEngine:\n"
        '    """Minimal clean engine for MCP server analysis."""\n\n'
        "    def compute(self, value: int) -> int:\n"
        "        return value + 1\n",
        encoding="utf-8",
    )
    (tests_dir / "test_core.py").write_text(
        "from corporate_engineer.core import CoreEngine\n\n\n"
        "def test_core_compute() -> None:\n"
        "    assert CoreEngine().compute(1) == 2\n",
        encoding="utf-8",
    )


def _extract_tool_payload(response: dict[str, Any]) -> dict[str, Any]:
    """Extract and parse JSON text payload from an MCP tools/call JSON-RPC result."""
    assert "error" not in response, f"Unexpected JSON-RPC error: {response}"
    result = response["result"]
    assert result.get("isError", False) is False, f"Tool reported error: {result}"
    content = result["content"]
    assert isinstance(content, list) and len(content) >= 1
    assert content[0]["type"] == "text"
    parsed: dict[str, Any] = json.loads(content[0]["text"])
    return parsed


# =============================================================================
# 1. DTO Contracts, Exports & Auto-Wiring
# =============================================================================


def test_mcp_server_dto_contracts_frozen() -> None:
    """MCPServerToolSpec and MCPServerCapabilitiesReport must inherit _FrozenDTO."""
    from corporate_engineer.models import (
        MCPServerCapabilitiesReport,
        MCPServerToolSpec,
    )

    spec = MCPServerToolSpec(
        name="blast_radius",
        description="Analyze reverse dependency blast radius",
        mutating=False,
        input_schema={"type": "object", "properties": {"target_file": {"type": "string"}}},
    )
    assert spec.name == "blast_radius"
    assert spec.mutating is False

    with pytest.raises(ValidationError):
        spec.mutating = True  # type: ignore[misc]

    caps = MCPServerCapabilitiesReport(
        workspace_root="/tmp/repo",
        allow_mutations=False,
        registered_tools=["blast_radius", "eval_scorecard"],
    )
    assert caps.server_name == "corporate-engineer-mcp"
    assert caps.protocol_version == "2024-11-05"
    assert caps.allow_mutations is False

    with pytest.raises(ValidationError):
        caps.allow_mutations = True  # type: ignore[misc]


def test_mcp_server_public_exports_and_prompt_refiner_wiring() -> None:
    """CorporateEngineerMCPServer must be exported and wired in PromptRefiner."""
    from corporate_engineer.mcp.server import CorporateEngineerMCPServer

    import corporate_engineer
    import corporate_engineer.mcp as mcp_pkg
    from corporate_engineer.prompt.refiner import ContextAwarePromptRefiner

    assert mcp_pkg.CorporateEngineerMCPServer is CorporateEngineerMCPServer
    assert corporate_engineer.CorporateEngineerMCPServer is CorporateEngineerMCPServer

    mcp_modules = ContextAwarePromptRefiner.DOMAIN_KEYWORDS["mcp"]["modules"]
    assert "src/corporate_engineer/mcp/server.py" in mcp_modules


# =============================================================================
# 2. JSON-RPC 2.0 Stdio Protocol & Tools Execution
# =============================================================================


def test_mcp_server_stdio_handshake_ping_and_tools_list(tmp_path: Path) -> None:
    """Verify initialize, notifications/initialized (silent), ping, and tools/list over stdio."""
    from corporate_engineer.mcp.server import CorporateEngineerMCPServer

    _create_sample_workspace(tmp_path)
    server = CorporateEngineerMCPServer(workspace_root=tmp_path, allow_mutations=False)

    requests = [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "pytest-client", "version": "1.0.0"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "ping"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/list"},
    ]
    stdin_buf = io.StringIO("\n".join(json.dumps(r) for r in requests) + "\n")
    stdout_buf = io.StringIO()

    exit_code = server.serve(stdin=stdin_buf, stdout=stdout_buf)
    assert exit_code == 0

    raw_lines = [line for line in stdout_buf.getvalue().splitlines() if line.strip()]
    # notifications/initialized has no id and MUST NOT produce a response frame
    assert len(raw_lines) == 3

    responses = [json.loads(line) for line in raw_lines]
    by_id = {resp["id"]: resp for resp in responses}

    init_res = by_id[1]["result"]
    assert init_res["protocolVersion"] == "2024-11-05"
    assert "tools" in init_res["capabilities"]
    assert "corporate-engineer" in init_res["serverInfo"]["name"]

    ping_res = by_id[2]
    assert "error" not in ping_res
    assert isinstance(ping_res["result"], dict)

    tools = by_id[3]["result"]["tools"]
    tool_names = {t["name"] for t in tools}
    assert READ_AUDIT_TOOLS.issubset(tool_names)
    assert "fix_auto" not in tool_names

    caps = server.get_capabilities()
    assert caps.allow_mutations is False
    assert READ_AUDIT_TOOLS.issubset(set(caps.registered_tools))


def test_mcp_server_calls_all_six_read_audit_tools(tmp_path: Path) -> None:
    """Execute all 6 read/audit tools via JSON-RPC 2.0 tools/call and verify real results."""
    from corporate_engineer.mcp.server import CorporateEngineerMCPServer

    _create_sample_workspace(tmp_path)
    server = CorporateEngineerMCPServer(workspace_root=tmp_path, allow_mutations=False)

    calls = [
        {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "blast_radius",
                "arguments": {"target_file": "src/corporate_engineer/core.py"},
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {
                "name": "eval_scorecard",
                "arguments": {"target_path": "src/corporate_engineer"},
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 12,
            "method": "tools/call",
            "params": {"name": "audit_wiring", "arguments": {}},
        },
        {
            "jsonrpc": "2.0",
            "id": 13,
            "method": "tools/call",
            "params": {"name": "secret_scan", "arguments": {"target_path": "."}},
        },
        {
            "jsonrpc": "2.0",
            "id": 14,
            "method": "tools/call",
            "params": {
                "name": "surgical_tests_plan",
                "arguments": {"changed_files": ["src/corporate_engineer/core.py"]},
            },
        },
        {
            "jsonrpc": "2.0",
            "id": 15,
            "method": "tools/call",
            "params": {
                "name": "ast_symbols",
                "arguments": {"target_path": "src/corporate_engineer/core.py"},
            },
        },
    ]

    stdin_buf = io.StringIO("\n".join(json.dumps(c) for c in calls) + "\n")
    stdout_buf = io.StringIO()
    server.serve(stdin=stdin_buf, stdout=stdout_buf)

    responses = {
        resp["id"]: resp
        for resp in (
            json.loads(line) for line in stdout_buf.getvalue().splitlines() if line.strip()
        )
    }

    blast_data = _extract_tool_payload(responses[10])
    assert "tests/test_core.py" in blast_data["affected_tests"]

    eval_data = _extract_tool_payload(responses[11])
    assert eval_data["composite_score"] >= 80.0
    assert eval_data["passed_gate"] is True

    wiring_data = _extract_tool_payload(responses[12])
    assert wiring_data["total_modules"] >= 1
    assert wiring_data["passed"] is True

    secret_data = _extract_tool_payload(responses[13])
    assert secret_data["passed"] is True
    assert secret_data["findings"] == []

    surgical_data = _extract_tool_payload(responses[14])
    assert "tests/test_core.py" in surgical_data["affected_tests"]

    ast_data = _extract_tool_payload(responses[15])
    serialized_ast = json.dumps(ast_data)
    assert "CoreEngine" in serialized_ast


def test_mcp_server_secret_scan_masks_detected_secret(tmp_path: Path) -> None:
    """secret_scan must detect credentials and never expose raw secret values in stdout."""
    from corporate_engineer.mcp.server import CorporateEngineerMCPServer

    _create_sample_workspace(tmp_path)
    prefix = "AKIA"
    raw_secret = f"{prefix}0123456789ABCDEF"
    (tmp_path / "src" / "corporate_engineer" / "leak.py").write_text(
        f'AWS_KEY = "{raw_secret}"\n',
        encoding="utf-8",
    )

    server = CorporateEngineerMCPServer(workspace_root=tmp_path, allow_mutations=False)
    req = {
        "jsonrpc": "2.0",
        "id": 20,
        "method": "tools/call",
        "params": {"name": "secret_scan", "arguments": {"target_path": "."}},
    }
    stdout_buf = io.StringIO()
    server.serve(stdin=io.StringIO(json.dumps(req) + "\n"), stdout=stdout_buf)

    raw_stdout = stdout_buf.getvalue()
    assert raw_secret not in raw_stdout

    payload = _extract_tool_payload(json.loads(raw_stdout.strip()))
    assert payload["passed"] is False
    assert len(payload["findings"]) >= 1
    assert "*" in payload["findings"][0]["masked_secret"]


def test_mcp_server_jsonrpc_error_handling_keeps_loop_alive(tmp_path: Path) -> None:
    """Malformed JSON, invalid requests, and unknown methods must return JSON-RPC errors."""
    from corporate_engineer.mcp.server import CorporateEngineerMCPServer

    _create_sample_workspace(tmp_path)
    server = CorporateEngineerMCPServer(workspace_root=tmp_path, allow_mutations=False)

    lines = [
        "{not-valid-json",
        json.dumps({"jsonrpc": "1.0", "id": 1, "method": "ping"}),
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "unknown/method"}),
        json.dumps({"jsonrpc": "2.0", "id": 3, "method": "ping"}),
    ]
    stdout_buf = io.StringIO()
    server.serve(stdin=io.StringIO("\n".join(lines) + "\n"), stdout=stdout_buf)

    responses = [json.loads(line) for line in stdout_buf.getvalue().splitlines() if line.strip()]
    assert len(responses) == 4
    assert responses[0]["error"]["code"] == -32700
    assert responses[1]["error"]["code"] == -32600
    assert responses[2]["error"]["code"] == -32601
    assert responses[3]["id"] == 3 and "result" in responses[3]


# =============================================================================
# 3. Security: Path Traversal Rejection & Least-Privilege Mutation Gating
# =============================================================================


@pytest.mark.parametrize(
    ("tool_name", "arg_key"),
    [
        ("blast_radius", "target_file"),
        ("eval_scorecard", "target_path"),
        ("secret_scan", "target_path"),
        ("ast_symbols", "target_path"),
    ],
)
def test_mcp_server_rejects_path_traversal(tmp_path: Path, tool_name: str, arg_key: str) -> None:
    """All workspace path inputs must reject relative traversal and external absolute paths."""
    from corporate_engineer.mcp.server import CorporateEngineerMCPServer

    workspace = tmp_path / "repo"
    workspace.mkdir()
    _create_sample_workspace(workspace)

    outside_file = tmp_path / "outside_secret.py"
    outside_file.write_text("SECRET_VALUE = 'external'\n", encoding="utf-8")

    server = CorporateEngineerMCPServer(workspace_root=workspace, allow_mutations=False)

    for bad_path in ("../../etc/passwd", "../outside_secret.py", str(outside_file)):
        resp = server.handle_request(
            {
                "jsonrpc": "2.0",
                "id": 99,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": {arg_key: bad_path}},
            }
        )
        assert resp is not None
        is_rejected = ("error" in resp) or bool(resp.get("result", {}).get("isError"))
        assert is_rejected, f"Expected path traversal rejection for {tool_name}({bad_path})"
        assert "external" not in json.dumps(resp)


def test_mcp_server_allow_mutations_gates_fix_auto(tmp_path: Path) -> None:
    """fix_auto must be hidden and blocked when allow_mutations=False, and allowed when True."""
    from corporate_engineer.mcp.server import CorporateEngineerMCPServer

    _create_sample_workspace(tmp_path)
    fixable = tmp_path / "src" / "corporate_engineer" / "fixable.py"
    original_src = "class Fixable:\n    def __init__(self):\n        self.x = 1\n"
    fixable.write_text(original_src, encoding="utf-8")

    readonly_server = CorporateEngineerMCPServer(workspace_root=tmp_path, allow_mutations=False)
    blocked_resp = readonly_server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 50,
            "method": "tools/call",
            "params": {
                "name": "fix_auto",
                "arguments": {"target_path": "src/corporate_engineer/fixable.py"},
            },
        }
    )
    assert blocked_resp is not None
    assert ("error" in blocked_resp) or bool(blocked_resp.get("result", {}).get("isError"))
    assert fixable.read_text(encoding="utf-8") == original_src

    mutating_server = CorporateEngineerMCPServer(workspace_root=tmp_path, allow_mutations=True)
    listed_names = {tool["name"] for tool in mutating_server.list_tools()}
    assert "fix_auto" in listed_names

    allowed_resp = mutating_server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 51,
            "method": "tools/call",
            "params": {
                "name": "fix_auto",
                "arguments": {"target_path": "src/corporate_engineer/fixable.py"},
            },
        }
    )
    assert allowed_resp is not None
    fix_payload = _extract_tool_payload(allowed_resp)
    assert fix_payload.get("files_modified", 0) >= 1 or fix_payload.get("success") is True
    assert "-> None" in fixable.read_text(encoding="utf-8")


# =============================================================================
# 4. CLI `mcp serve` Parser & Subprocess Stdio Handshake
# =============================================================================


def test_cli_mcp_serve_parser_defaults_and_flags() -> None:
    """Verify `corporate-engineer mcp serve` parser supports --workspace and --allow-mutations."""
    from corporate_engineer.cli.parser import build_parser

    parser = build_parser()
    default_args = parser.parse_args(["mcp", "serve"])
    assert default_args.command == "mcp"
    assert default_args.mcp_action == "serve"
    assert default_args.workspace == "."
    assert default_args.allow_mutations is False

    mut_args = parser.parse_args(["mcp", "serve", "--workspace", "/tmp/ws", "--allow-mutations"])
    assert mut_args.mcp_action == "serve"
    assert mut_args.workspace == "/tmp/ws"
    assert mut_args.allow_mutations is True


def test_cli_mcp_serve_subprocess_stdio_clean_framing(tmp_path: Path) -> None:
    """Spawn `python -m corporate_engineer.cli mcp serve` and verify pure JSON-RPC 2.0 stdout."""
    _create_sample_workspace(tmp_path)
    frames = [
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
            }
        ),
        json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}),
        json.dumps({"jsonrpc": "2.0", "id": 2, "method": "ping"}),
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "audit_wiring", "arguments": {}},
            }
        ),
    ]
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "corporate_engineer.cli",
            "mcp",
            "serve",
            "--workspace",
            str(tmp_path),
        ],
        input="\n".join(frames) + "\n",
        capture_output=True,
        text=True,
        cwd=str(WORKSPACE_ROOT),
        timeout=20,
        check=False,
    )
    assert proc.returncode == 0, f"mcp serve failed: {proc.stderr}"

    stdout_lines = [line for line in proc.stdout.splitlines() if line.strip()]
    assert len(stdout_lines) == 3
    parsed = [json.loads(line) for line in stdout_lines]
    assert all(item.get("jsonrpc") == "2.0" for item in parsed)
    audit_payload = _extract_tool_payload(parsed[2])
    assert audit_payload["passed"] is True


# =============================================================================
# 5. Antigravity Workspace Plugin Manifests
# =============================================================================


def test_workspace_plugin_manifests_valid_and_least_privilege() -> None:
    """Validate .agents/plugins/corporate-engineer/{plugin.json,mcp_config.json}."""
    from corporate_engineer.quality.secret_scanner import CanonicalSecretScanner

    plugin_json_path = PLUGIN_DIR / "plugin.json"
    mcp_config_path = PLUGIN_DIR / "mcp_config.json"

    assert plugin_json_path.exists(), f"Missing plugin manifest: {plugin_json_path}"
    assert mcp_config_path.exists(), f"Missing MCP config: {mcp_config_path}"

    plugin_data = json.loads(plugin_json_path.read_text(encoding="utf-8"))
    assert plugin_data["name"] == "corporate-engineer"
    assert isinstance(plugin_data.get("description"), str) and len(plugin_data["description"]) > 10
    unknown_keys = set(plugin_data.keys()) - ALLOWED_PLUGIN_TOP_LEVEL_KEYS
    assert not unknown_keys, f"Unsupported plugin.json top-level fields: {unknown_keys}"

    mcp_raw = mcp_config_path.read_text(encoding="utf-8")
    assert CanonicalSecretScanner().scan_text(mcp_raw, str(mcp_config_path)) == []

    mcp_data = json.loads(mcp_raw)
    servers = mcp_data.get("mcpServers", {})
    assert isinstance(servers, dict) and len(servers) >= 1
    assert any("corporate-engineer" in name for name in servers)

    server_cfg = next(cfg for name, cfg in servers.items() if "corporate-engineer" in name)
    assert isinstance(server_cfg.get("command"), str) and server_cfg["command"].strip() != ""
    args = server_cfg.get("args", [])
    assert isinstance(args, list)
    joined_args = " ".join(str(a) for a in args)
    assert "corporate_engineer.cli" in joined_args
    assert "mcp" in args and "serve" in args
    assert "--allow-mutations" not in args
