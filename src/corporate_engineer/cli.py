"""
Command Line Interface for Autonomous Corporate Software Engineer.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from corporate_engineer.git_utils import generate_pr_url
from corporate_engineer.mcp.client import LocalMCPToolAdapter, RemoteMCPSSEClient
from corporate_engineer.models import MCPToolCall, TaskInput
from corporate_engineer.orchestrator.graph import AutonomousEngineeringGraph
from corporate_engineer.quality.gate import QualityGateRunner
from corporate_engineer.quality.mutation import ASTMutationEngine
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
    index_parser.add_argument(
        "--impact-of", default=None, help="Calculate blast radius for target symbol or file"
    )
    index_parser.add_argument(
        "--depth", type=int, default=3, help="Max propagation depth for impact analysis"
    )

    # Command: audit
    audit_parser = subparsers.add_parser("audit", help="Run pre-flight security and quality audit")
    audit_parser.add_argument("--path", default=".", help="Path to audit")
    audit_parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )
    audit_parser.add_argument(
        "--strict", action="store_true", help="Run strict checks including test suite verification"
    )
    audit_parser.add_argument(
        "--mutation",
        action="store_true",
        help="Run AST mutation testing to evaluate test suite quality",
    )
    audit_parser.add_argument("--target-file", default=None, help="Specific source file to mutate")
    audit_parser.add_argument(
        "--max-mutants", type=int, default=10, help="Maximum number of mutants to test"
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
        "--mermaid",
        action="store_true",
        help="Export FSM lifecycle or checkpoints as Mermaid flowchart",
    )
    dag_parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )
    dag_parser.add_argument("--output", default=None, help="Optional file path to write output")

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

    # Command: pr-link
    pr_parser = subparsers.add_parser(
        "pr-link", help="Generate 1-click pre-filled GitHub Pull Request URL"
    )
    pr_parser.add_argument(
        "--branch", default=None, help="Target branch name (default: active branch)"
    )
    pr_parser.add_argument("--base", default="main", help="Base branch (default: main)")
    pr_parser.add_argument("--doc", default=None, help="Path to specific PR markdown file")
    pr_parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )

    # Command: eval (IMP-0007)
    eval_parser = subparsers.add_parser(
        "eval", help="Evaluate code quality using semantic corporate scorecard (EDD)"
    )
    eval_parser.add_argument(
        "path", nargs="?", default="src", help="Path to file or directory to evaluate"
    )
    eval_parser.add_argument(
        "--min-score",
        type=float,
        default=80.0,
        help="Minimum composite score to pass gate (default: 80.0)",
    )
    eval_parser.add_argument(
        "--strict", action="store_true", help="Fail if any axis fails or any violation occurs"
    )
    eval_parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format (default: text)"
    )

    # Command: blast-radius (IMP-0008)
    blast_parser = subparsers.add_parser(
        "blast-radius", help="Calculate blast radius and affected tests for a code change"
    )
    blast_parser.add_argument("target", help="Target function, class name or file path")
    blast_parser.add_argument(
        "--depth", type=int, default=3, help="Max transitive propagation depth (default: 3)"
    )
    blast_parser.add_argument("--workspace", default=".", help="Workspace path (default: .)")
    blast_parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format (default: text)"
    )
    blast_parser.add_argument("--output", default=None, help="Optional file path to write output")

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

    if getattr(args, "impact_of", None):
        return _run_blast_radius_analysis(
            target_val=args.impact_of,
            workspace=str(target),
            depth=getattr(args, "depth", 3),
            format_type=args.format,
            output_path=args.output,
        )

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

    mutation_report = None
    if getattr(args, "mutation", False):
        engine = ASTMutationEngine(workspace_root=target)
        target_f: Path | None = None
        if getattr(args, "target_file", None):
            target_f = Path(args.target_file).resolve()
        else:
            for p in sorted(target.rglob("*.py")):
                if not any(
                    part.startswith(".") or part in ("venv", ".venv", "__pycache__", "tests")
                    for part in p.parts
                ):
                    target_f = p
                    break
        if target_f and target_f.exists():
            mutation_report = engine.run_mutation_testing(
                target_file=target_f, max_mutants=getattr(args, "max_mutants", 10)
            )

    overall_passed = bool(secret_res["passed"] and strict_passed)

    if args.format == "json":
        payload = {
            "passed": overall_passed,
            "secret_scan": secret_res,
            "findings": secret_res.get("findings", []),
            "strict_mode": args.strict,
            "test_verification": test_res,
            "mutation_report": mutation_report.model_dump() if mutation_report else None,
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

        if mutation_report:
            print("🧬 AST Mutation Testing:")
            print(f"  - Total de Mutantes: {mutation_report.total_mutants}")
            print(f"  - Mutantes Mortos (Killed): {mutation_report.killed}")
            print(f"  - Mutantes Sobreviventes: {mutation_report.survived}")
            print(f"  - Mutation Score: {mutation_report.mutation_score}%")
            for m in mutation_report.mutants:
                status_icon = "💀 KILLED" if m.status == "KILLED" else "⚠️ SURVIVED"
                print(f"    [{status_icon}] L{m.line_number}: {m.original_op} -> {m.mutated_op}")

    return 0 if overall_passed else 1


def handle_dag(args: argparse.Namespace) -> int:
    if getattr(args, "mermaid", False):
        if getattr(args, "checkpoints", False):
            ws = Path(getattr(args, "workspace", ".")).resolve()
            checkpoints = AutonomousEngineeringGraph.list_checkpoints(ws)
            output_str = AutonomousEngineeringGraph.checkpoints_to_mermaid(checkpoints)
        else:
            output_str = AutonomousEngineeringGraph.fsm_to_mermaid()

        if getattr(args, "output", None):
            out_p = Path(args.output).resolve()
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(output_str, encoding="utf-8")
            print(f"✅ Diagrama Mermaid salvo com sucesso em: {out_p}")
        else:
            print(output_str)
        return 0

    if getattr(args, "checkpoints", False):
        ws = Path(getattr(args, "workspace", ".")).resolve()
        checkpoints = AutonomousEngineeringGraph.list_checkpoints(ws)
        if args.format == "json":
            output_str = json.dumps({"workspace": str(ws), "checkpoints": checkpoints}, indent=2)
        else:
            lines = [f"📦 Checkpoints salvos em: {ws}"]
            if not checkpoints:
                lines.append("  (Nenhum checkpoint encontrado)")
            for cp in checkpoints:
                ticket = cp.get("ticket_id") or "N/A"
                phase = cp.get("phase") or "N/A"
                iter_cnt = cp.get("iteration_count", 0)
                lines.append(
                    f"  - [{ticket}] {cp['filename']} (Fase: {phase}, Iteração: {iter_cnt})"
                )
            output_str = "\n".join(lines)

        if getattr(args, "output", None):
            out_p = Path(args.output).resolve()
            out_p.parent.mkdir(parents=True, exist_ok=True)
            out_p.write_text(output_str, encoding="utf-8")
            print(f"✅ Saída salva com sucesso em: {out_p}")
        else:
            print(output_str)
        return 0

    if args.format == "json":
        payload = {
            "phases": DAG_PHASES,
            "transitions": DAG_TRANSITIONS,
        }
        output_str = json.dumps(payload, indent=2)
    else:
        lines = ["📊 Ciclo de Vida e Fases da Orquestração DAG:"]
        for idx, phase in enumerate(DAG_PHASES, start=1):
            lines.append(f"  {idx}. {phase}")
        lines.append("\n🔀 Transições Válidas:")
        for t in DAG_TRANSITIONS:
            lines.append(f"  [{t['from']}] --({t['trigger']})--> [{t['to']}]")
        output_str = "\n".join(lines)

    if getattr(args, "output", None):
        out_p = Path(args.output).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(output_str, encoding="utf-8")
        print(f"✅ Saída salva com sucesso em: {out_p}")
    else:
        print(output_str)
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


def handle_pr_link(args: argparse.Namespace) -> int:
    info = generate_pr_url(
        repo_path=".",
        branch=args.branch,
        base=args.base,
        pr_doc_path=args.doc,
    )
    if args.format == "json":
        print(json.dumps(info, indent=2))
    else:
        print(f"🔗 Pre-Filled GitHub PR Link [{info['branch']} -> {info['base']}]:")
        print(f"  - Ticket: {info['ticket_id']}")
        print(f"  - Título: {info['title']}")
        print(f"  - URL: {info['url']}")
    return 0


def handle_eval(args: argparse.Namespace) -> int:
    from corporate_engineer.eval.scorecard import SemanticCodeEvaluator

    evaluator = SemanticCodeEvaluator()
    target = Path(args.path)
    if target.is_file():
        content = target.read_text(encoding="utf-8", errors="ignore")
        report = evaluator.evaluate_source(
            content, file_path=str(target), min_passing_score=args.min_score
        )
    else:
        report = evaluator.evaluate_directory(target, min_passing_score=args.min_score)

    if args.format == "json":
        print(report.model_dump_json(indent=2))
    else:
        print("\n" + "=" * 60)
        print(f"📊 Corporate Scorecard (EDD) - Target: {report.target_path}")
        print("=" * 60)
        print(
            f"• Composite Score: {report.composite_score:.1f} / 100.0  [Grade: {report.letter_grade}]"
        )
        print(
            f"• Gate Status: {'✅ PASS' if report.passed_gate else '❌ FAIL'} "
            f"(Min required: {report.min_passing_score:.1f})"
        )
        print(f"• Total Files Evaluated: {report.total_files_evaluated}")
        print(f"• Total Functions Evaluated: {report.total_functions_evaluated}")
        print(f"• Total Violations: {report.total_violations}")
        print("\n--- Corporate Axes Breakdown ---")
        for ax in report.axes:
            status = "✅ PASS" if ax.passed else "❌ FAIL"
            bar_len = int(ax.score // 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            print(f"[{bar}] {ax.score:5.1f}% (Weight: {ax.weight:.2f}) {status} - {ax.axis_name}")
            if ax.violations:
                for v in ax.violations[:3]:
                    print(f"    ⚠️  {v}")
                if len(ax.violations) > 3:
                    print(f"    ... e mais {len(ax.violations) - 3} violação(ões)")
        print("=" * 60 + "\n")

    if args.strict and (not report.passed_gate or report.total_violations > 0):
        return 1
    return 0 if report.passed_gate else 1


def _run_blast_radius_analysis(
    target_val: str,
    workspace: str = ".",
    depth: int = 3,
    format_type: str = "text",
    output_path: str | None = None,
) -> int:
    from corporate_engineer.models import BlastRadiusReport
    from corporate_engineer.rag.impact import BlastRadiusAnalyzer

    is_file = target_val.endswith(".py") or "/" in target_val or "\\" in target_val
    analyzer = BlastRadiusAnalyzer(workspace_root=workspace)
    report: BlastRadiusReport = analyzer.analyze_impact(
        target_file=target_val if is_file else None,
        target_symbol=target_val if not is_file else None,
        max_depth=depth,
    )

    if format_type == "json":
        output_str = report.model_dump_json(indent=2)
    else:
        lines = [
            "\n" + "=" * 60,
            f"💥 Blast Radius Analysis: {report.target} [{report.target_type}]",
            "=" * 60,
            f"• Total Impacted Files: {report.total_impacted_files}",
            f"• Total Impacted Symbols: {report.total_impacted_symbols}",
            f"• Impacted Test Suites: {len(report.affected_tests)}",
            f"• Recommended Surgical Test Command:\n  👉 {report.recommended_test_command}",
            "\n--- Impact Propagation Tree ---",
        ]
        if not report.impacted_nodes:
            lines.append("  (No external callers or importers detected - localized component)")
        else:
            nodes_by_depth: dict[int, list[Any]] = {}
            for n in report.impacted_nodes:
                nodes_by_depth.setdefault(n.depth, []).append(n)

            for d in sorted(nodes_by_depth.keys()):
                tag = "DIRECT IMPACT" if d == 1 else f"TRANSITIVE IMPACT (Depth {d})"
                lines.append(f"\n📂 [{tag}]")
                for n in nodes_by_depth[d]:
                    lines.append(f"  • {n.file_path} :: {n.symbol} ({n.relationship})")

        if report.affected_tests:
            lines.append("\n🧪 [AFFECTED TESTS]")
            for t in report.affected_tests:
                lines.append(f"  ✓ {t}")

        lines.append("=" * 60 + "\n")
        output_str = "\n".join(lines)

    if output_path:
        out_p = Path(output_path).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(output_str, encoding="utf-8")
        print(f"✅ Análise de Blast Radius salva em: {out_p}")
    else:
        print(output_str)

    return 0


def handle_blast_radius(args: argparse.Namespace) -> int:
    return _run_blast_radius_analysis(
        target_val=args.target,
        workspace=args.workspace,
        depth=args.depth,
        format_type=args.format,
        output_path=getattr(args, "output", None),
    )


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
    elif args.command == "pr-link":
        return handle_pr_link(args)
    elif args.command == "eval":
        return handle_eval(args)
    elif args.command == "blast-radius":
        return handle_blast_radius(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
