"""
Command Line Interface for Autonomous Corporate Software Engineer.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from corporate_engineer.mcp.client import LocalMCPToolAdapter, RemoteMCPSSEClient
from corporate_engineer.models import MCPToolCall, TaskInput
from corporate_engineer.orchestrator.graph import AutonomousEngineeringGraph
from corporate_engineer.quality.gate import QualityGateRunner
from corporate_engineer.rag.ast_indexer import ASTCodebaseIndexer

DAG_PHASES = ["PLANNING", "TDD", "IMPLEMENT", "AUDIT", "DELIVER"]
DAG_TRANSITIONS = [
    {"from": "PLANNING", "to": "TDD", "trigger": "step_plan"},
    {"from": "TDD", "to": "IMPLEMENT", "trigger": "step_tdd"},
    {"from": "IMPLEMENT", "to": "AUDIT", "trigger": "step_implement"},
    {"from": "AUDIT", "to": "DELIVER", "trigger": "step_audit(passed=True)"},
    {"from": "AUDIT", "to": "IMPLEMENT", "trigger": "step_audit(passed=False)"},
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="corporate-engineer",
        description="Autonomous Corporate Software Engineer - Open Source Enterprise Framework",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: run
    run_parser = subparsers.add_parser("run", help="Run an autonomous engineering task")
    run_parser.add_argument("--ticket", required=True, help="Ticket ID (e.g. JIRA-101)")
    run_parser.add_argument("--task", required=True, help="Task description")
    run_parser.add_argument("--workspace", default=".", help="Workspace path")
    run_parser.add_argument("--max-turns", type=int, default=20, help="Max iteration turns")

    # Command: index
    index_parser = subparsers.add_parser("index", help="Index codebase using AST")
    index_parser.add_argument("--path", default=".", help="Path to index")
    index_parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )
    index_parser.add_argument("--output", default=None, help="Optional file path to write output")

    # Command: audit
    audit_parser = subparsers.add_parser("audit", help="Run pre-flight security and quality audit")
    audit_parser.add_argument("--path", default=".", help="Path to audit")
    audit_parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )
    audit_parser.add_argument(
        "--strict", action="store_true", help="Run strict checks including test suite verification"
    )

    # Command: dag
    dag_parser = subparsers.add_parser("dag", help="Inspect and operate agent orchestrator DAG")
    dag_parser.add_argument(
        "--show-phases", action="store_true", help="Display FSM lifecycle phases and transitions"
    )
    dag_parser.add_argument(
        "--checkpoints", action="store_true", help="List saved state checkpoints in workspace"
    )
    dag_parser.add_argument(
        "--workspace", default=".", help="Workspace path to inspect checkpoints"
    )
    dag_parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )

    # Command: mcp
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

    return parser


def handle_run(args: argparse.Namespace) -> int:
    task = TaskInput(
        ticket_id=args.ticket,
        description=args.task,
        workspace_path=str(Path(args.workspace).resolve()),
        max_iterations=args.max_turns,
    )
    graph = AutonomousEngineeringGraph(task=task)
    print(f"🚀 Iniciando Engenheiro Autônomo para o ticket: {task.ticket_id}")
    print(f"📝 Descrição: {task.description}")
    print(f"🔄 Fase Inicial: {graph.state.phase}")
    print("✅ Grafo inicializado com sucesso.")
    return 0


def handle_index(args: argparse.Namespace) -> int:
    target = Path(args.path).resolve()
    indexer = ASTCodebaseIndexer(root_path=target)

    if args.format == "json":
        indexed_files: list[dict[str, Any]] = []
        for root, dirs, files in os.walk(target):
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".") and d not in {"venv", ".venv", "__pycache__"}
            ]
            for f in sorted(files):
                if f.endswith(".py"):
                    full_p = Path(root) / f
                    rel_p = str(full_p.relative_to(target))
                    symbols = indexer.index_file(full_p)
                    indexed_files.append({"file": rel_p, "symbols": symbols})
        payload = {"root": str(target), "files": indexed_files}
        output_str = json.dumps(payload, indent=2)
    else:
        output_str = indexer.build_codebase_outline()

    if args.output:
        out_p = Path(args.output).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(output_str, encoding="utf-8")
        print(f"✅ Índice AST salvo com sucesso em: {out_p}")
    else:
        print(output_str)

    return 0


def handle_audit(args: argparse.Namespace) -> int:
    target = Path(args.path).resolve()
    runner = QualityGateRunner(project_root=target)
    secret_res = runner.run_secret_scan()

    test_res: dict[str, Any] | None = None
    strict_passed = True
    if args.strict:
        test_res = runner.run_tests()
        strict_passed = bool(test_res.get("passed", False))

    overall_passed = bool(secret_res["passed"] and strict_passed)

    if args.format == "json":
        payload = {
            "passed": overall_passed,
            "secret_scan": secret_res,
            "findings": secret_res.get("findings", []),
            "strict_mode": args.strict,
            "test_verification": test_res,
        }
        print(json.dumps(payload, indent=2))
    else:
        if secret_res["passed"]:
            print("✅ Pre-Flight Secret Scan PASS: Zero segredos detectados.")
        else:
            print("❌ Segredos encontrados:")
            for f in secret_res["findings"]:
                print(f" - {f['file']}:{f['line']} [{f['type']}]")

        if args.strict:
            if test_res and test_res["passed"]:
                print("✅ Strict Test Verification PASS: Todos os testes passaram.")
            else:
                print("❌ Strict Test Verification FAIL.")

    return 0 if overall_passed else 1


def handle_dag(args: argparse.Namespace) -> int:
    if getattr(args, "checkpoints", False):
        ws = Path(getattr(args, "workspace", ".")).resolve()
        checkpoints = AutonomousEngineeringGraph.list_checkpoints(ws)
        if args.format == "json":
            print(json.dumps({"workspace": str(ws), "checkpoints": checkpoints}, indent=2))
        else:
            print(f"📦 Checkpoints salvos em: {ws}")
            if not checkpoints:
                print("  (Nenhum checkpoint encontrado)")
            for cp in checkpoints:
                ticket = cp.get("ticket_id") or "N/A"
                phase = cp.get("phase") or "N/A"
                iter_cnt = cp.get("iteration_count", 0)
                print(f"  - [{ticket}] {cp['filename']} (Fase: {phase}, Iteração: {iter_cnt})")
        return 0

    if args.format == "json":
        payload = {
            "phases": DAG_PHASES,
            "transitions": DAG_TRANSITIONS,
        }
        print(json.dumps(payload, indent=2))
    else:
        print("📊 Ciclo de Vida e Fases da Orquestração DAG:")
        for idx, phase in enumerate(DAG_PHASES, start=1):
            print(f"  {idx}. {phase}")
        print("\n🔀 Transições Válidas:")
        for t in DAG_TRANSITIONS:
            print(f"  [{t['from']}] --({t['trigger']})--> [{t['to']}]")
    return 0


def handle_mcp(args: argparse.Namespace) -> int:
    is_remote = args.server == "remote"

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

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        return handle_run(args)
    elif args.command == "index":
        return handle_index(args)
    elif args.command == "audit":
        return handle_audit(args)
    elif args.command == "dag":
        return handle_dag(args)
    elif args.command == "mcp":
        return handle_mcp(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
