"""
MCP (Model Context Protocol) CLI Commands (ping, list-tools, call, hub).
Modular domain command package decomposed according to ADR-026 / IMP-0023.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from corporate_engineer.mcp.client import LocalMCPToolAdapter, RemoteMCPSSEClient
from corporate_engineer.models import MCPToolCall


def register_mcp_parser(subparsers: Any) -> argparse.ArgumentParser:
    """Register parser for `mcp` command."""
    mcp_parser = subparsers.add_parser("mcp", help="Inspect and execute tools via MCP protocol")
    mcp_subparsers = mcp_parser.add_subparsers(dest="mcp_action", help="MCP action")

    # mcp ping
    ping_parser = mcp_subparsers.add_parser("ping", help="Ping MCP server (local or remote)")
    ping_parser.add_argument("--server", choices=["local", "remote"], default="local")
    ping_parser.add_argument("--workspace", default=".", help="Workspace path for local mode")
    ping_parser.add_argument(
        "--url", default="http://localhost:8000/sse", help="Remote MCP endpoint"
    )
    ping_parser.add_argument("--token", default=None, help="Bearer auth token for remote MCP")
    ping_parser.add_argument("--format", choices=["text", "json"], default="text")

    # mcp list-tools
    list_parser = mcp_subparsers.add_parser(
        "list-tools", help="List available tools from MCP server"
    )
    list_parser.add_argument("--server", choices=["local", "remote"], default="local")
    list_parser.add_argument("--workspace", default=".", help="Workspace path for local mode")
    list_parser.add_argument(
        "--url", default="http://localhost:8000/sse", help="Remote MCP endpoint"
    )
    list_parser.add_argument("--token", default=None, help="Bearer auth token for remote MCP")
    list_parser.add_argument("--format", choices=["text", "json"], default="text")

    # mcp call
    call_parser = mcp_subparsers.add_parser("call", help="Execute an MCP tool")
    call_parser.add_argument("--tool", required=True, help="Tool name")
    call_parser.add_argument("--server", choices=["local", "remote"], default="local")
    call_parser.add_argument("--args", default="{}", help="Tool arguments in JSON format")
    call_parser.add_argument("--workspace", default=".", help="Workspace path for local mode")
    call_parser.add_argument(
        "--url", default="http://localhost:8000/sse", help="Remote MCP endpoint"
    )
    call_parser.add_argument("--token", default=None, help="Bearer auth token for remote MCP")
    call_parser.add_argument("--format", choices=["text", "json"], default="text")

    # mcp hub (IMP-0011)
    hub_parser = mcp_subparsers.add_parser(
        "hub", help="Enterprise MCP Multi-Server Hub (.mcp.json pools)"
    )
    hub_parser.add_argument("--config", default=".mcp.json", help="Path to .mcp.json config file")
    hub_parser.add_argument(
        "hub_action",
        choices=["list", "call", "prune"],
        default="list",
        nargs="?",
        help="Action: list tools/status, call namespaced tool, or prune for prompt",
    )
    hub_parser.add_argument(
        "--tool", default=None, help="Namespaced tool to call (e.g. postgres.query)"
    )
    hub_parser.add_argument("--args", default="{}", help="Tool arguments in JSON format")
    hub_parser.add_argument("--prompt", default="", help="Prompt for System-One tool pruning")
    hub_parser.add_argument("--format", choices=["text", "json"], default="text")

    # mcp serve (IMP-0042)
    serve_parser = mcp_subparsers.add_parser(
        "serve", help="Run native JSON-RPC 2.0 MCP server over stdio"
    )
    serve_parser.add_argument("--workspace", default=".", help="Workspace root path")
    serve_parser.add_argument(
        "--allow-mutations",
        action="store_true",
        help="Enable mutating tools such as fix_auto (disabled by default)",
    )

    return mcp_parser


def _handle_mcp_serve(args: argparse.Namespace) -> int:
    from corporate_engineer.mcp.server import CorporateEngineerMCPServer

    ws_root = Path(getattr(args, "workspace", ".")).resolve()
    allow_mutations = bool(getattr(args, "allow_mutations", False))
    server = CorporateEngineerMCPServer(
        workspace_root=ws_root,
        allow_mutations=allow_mutations,
    )
    return server.serve()


def handle_mcp(args: argparse.Namespace) -> int:
    if not getattr(args, "mcp_action", None):
        print(
            "Usage: corporate-engineer mcp {ping,list-tools,call,hub,serve} [options]",
            file=sys.stderr,
        )
        return 1

    if args.mcp_action == "serve":
        return _handle_mcp_serve(args)

    if args.mcp_action == "hub":
        from corporate_engineer.mcp.hub import MCPEnterpriseHub

        cfg_p = Path(args.config)
        hub = MCPEnterpriseHub(config_path=cfg_p if cfg_p.exists() else None)

        if args.hub_action == "call":
            if not args.tool:
                print("❌ Parâmetro --tool é obrigatório para hub call", file=sys.stderr)
                return 1
            try:
                parsed_args = json.loads(args.args)
            except json.JSONDecodeError as e:
                print(f"❌ Argumentos JSON inválidos: {e}", file=sys.stderr)
                return 1
            res = hub.call_tool(args.tool, parsed_args)
            print(json.dumps(res, indent=2) if args.format == "json" else f"✅ Resultado: {res}")
            return 0

        elif args.hub_action == "prune":
            pruned = hub.prune_tools_for_prompt(args.prompt or "")
            if args.format == "json":
                print(json.dumps([tool_item.model_dump() for tool_item in pruned], indent=2))
            else:
                print(f"\n🔍 FERRAMENTAS SELECIONADAS PELO SISTEMA 1 (Prompt: '{args.prompt}'):")
                for tool_item in pruned:
                    print(f"  • {tool_item.namespaced_name}: {tool_item.description}")
            return 0

        else:  # list
            hub_status = hub.get_status()
            hub_tools = hub.list_tools()
            if args.format == "json":
                print(
                    json.dumps(
                        {
                            "status": hub_status.model_dump(),
                            "tools": [ht.model_dump() for ht in hub_tools],
                        },
                        indent=2,
                    )
                )
            else:
                print(f"\n{'=' * 60}\n🌐 MCP ENTERPRISE HUB (IMP-0011)\n{'=' * 60}")
                print(f"📦 Total de Servidores : {hub_status.total_servers}")
                print(f"🛠️  Total de Ferramentas : {hub_status.total_tools}")
                print("🔌 Servidores Conectados:")
                for s in hub_status.active_servers:
                    st = hub_status.circuit_states.get(s, "UNKNOWN")
                    print(f"   • {s:<20} [Circuit: {st}]")
                if hub_tools:
                    print("\n📋 Ferramentas por Namespace:")
                    for ht in hub_tools:
                        print(f"   - {ht.namespaced_name:<25}: {ht.description}")
                print(f"{'=' * 60}\n")
            return 0

    is_remote = getattr(args, "server", "local") == "remote"

    if is_remote:
        client = RemoteMCPSSEClient(endpoint=args.url, auth_token=args.token)
    else:
        ws_root = Path(getattr(args, "workspace", ".")).resolve()
        adapter = LocalMCPToolAdapter(workspace_root=ws_root)

    if args.mcp_action == "ping":
        status = client.ping() if is_remote else adapter.ping()
        if args.format == "json":
            print(json.dumps(status, indent=2))
        else:
            mode_lbl = status.get("mode", args.server)
            st_lbl = status.get("status", "unknown")
            print(f"📡 MCP Ping [{mode_lbl}]: {st_lbl.upper()}")
        return 0 if status.get("status") == "ok" else 1

    elif args.mcp_action == "list-tools":
        tools = client.list_tools() if is_remote else adapter.list_tools()
        if args.format == "json":
            print(json.dumps({"server": args.server, "tools": tools}, indent=2))
        else:
            print(f"🛠️  Ferramentas MCP Disponíveis [{args.server}]:")
            for t in tools:
                print(f"  - {t['name']}: {t.get('description', '')}")
        return 0

    elif args.mcp_action == "call":
        try:
            parsed_args = json.loads(args.args)
        except json.JSONDecodeError as e:
            print(f"❌ Argumentos JSON inválidos: {e}", file=sys.stderr)
            return 1

        if is_remote:
            res = client.call_tool(args.tool, parsed_args)
        else:
            server_name = "filesystem" if args.tool in ("read_file", "write_file") else "shell"
            call = MCPToolCall(
                server_name=server_name,
                tool_name=args.tool,
                arguments=parsed_args,
            )
            res = adapter.execute(call)

        if args.format == "json":
            print(
                json.dumps(
                    {
                        "tool": res.tool_name,
                        "is_error": res.is_error,
                        "content": res.content,
                    },
                    indent=2,
                )
            )
        else:
            status_icon = "❌ Erro:" if res.is_error else "✅ Resultado:"
            print(f"{status_icon}\n{res.content}")

        return 1 if res.is_error else 0

    print(
        f"Unknown mcp action: {args.mcp_action}. "
        "Usage: corporate-engineer mcp {ping,list-tools,call,hub,serve} [options]",
        file=sys.stderr,
    )
    return 1
