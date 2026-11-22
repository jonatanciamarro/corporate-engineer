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
        "--trace",
        action="store_true",
        help="Emit OpenTelemetry execution trace for DAG",
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
    pr_parser.add_argument(
        "--no-push",
        dest="push",
        action="store_false",
        default=True,
        help="Skip pushing branch to origin remote before generating URL (default: push is always-on)",
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

    # Command: telemetry (IMP-0009)
    tel_parser = subparsers.add_parser(
        "telemetry", help="Inspect and visualize OpenTelemetry agent traces"
    )
    tel_parser.add_argument("--file", default=None, help="Path to JSON trace file")
    tel_parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format (default: text)"
    )
    tel_parser.add_argument("--output", default=None, help="Optional file path to export report")

    # Command: test-surgical (IMP-0010)
    surgical_parser = subparsers.add_parser(
        "test-surgical",
        help="Run surgical testing by detecting Git diff and computing affected tests via blast radius",
    )
    surgical_parser.add_argument(
        "--base-branch", default="main", help="Base Git branch for comparison (default: main)"
    )
    surgical_parser.add_argument(
        "--depth",
        type=int,
        default=3,
        help="Max transitive blast radius propagation depth (default: 3)",
    )
    surgical_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print affected tests and test command without executing",
    )
    surgical_parser.add_argument(
        "--fallback-all",
        action="store_true",
        help="Fallback to running all tests if changes exist but no tests match",
    )
    surgical_parser.add_argument("--workspace", default=".", help="Workspace path (default: .)")
    surgical_parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format (default: text)"
    )
    surgical_parser.add_argument(
        "--output", default=None, help="Optional file path to write output"
    )
    surgical_parser.add_argument(
        "pytest_extra_args", nargs="*", help="Optional extra arguments passed directly to pytest"
    )

    # Command: decide (IMP-0013 / IMP-0014)
    decide_parser = subparsers.add_parser(
        "decide",
        help="Fast System-One probabilistic decisions, agent routing, and triage",
    )
    decide_parser.add_argument(
        "prompt",
        nargs="?",
        default="",
        help="Prompt, requirement, or state to evaluate",
    )
    decide_parser.add_argument(
        "--mode",
        choices=["route", "risk", "triage", "commit", "skip"],
        default="route",
        help="Decision mode: route agent, assess risk, full triage, commit type, or skip node (default: route)",
    )
    decide_parser.add_argument(
        "--diff",
        default="",
        help="Optional git diff content or file path for risk analysis",
    )
    decide_parser.add_argument(
        "--engine",
        choices=["heuristic", "outlines", "nli", "onnx", "auto"],
        default="auto",
        help="Decision engine backend (default: auto)",
    )
    decide_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    decide_parser.add_argument("--output", default=None, help="Optional file path to write output")

    # Command: dataset (IMP-0014)
    dataset_parser = subparsers.add_parser(
        "dataset",
        help="Synthetic dataset generation and Colab recipe for System-One SLM fine-tuning (IMP-0014)",
    )
    dataset_parser.add_argument(
        "action",
        choices=["generate", "recipe"],
        default="generate",
        nargs="?",
        help="Action: generate synthetic dataset or generate Colab training recipe (default: generate)",
    )
    dataset_parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Target output file path (default: data/system_one_dataset.jsonl or scripts/train_colab_recipe.py)",
    )
    dataset_parser.add_argument(
        "--samples",
        type=int,
        default=10,
        help="Samples per category for synthetic generation (default: 10)",
    )
    dataset_parser.add_argument(
        "--model",
        default="Qwen/Qwen2.5-0.5B-Instruct",
        help="Target SLM base model for Colab training recipe (default: Qwen/Qwen2.5-0.5B-Instruct)",
    )
    dataset_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    # Command: fix (IMP-0012)
    fix_parser = subparsers.add_parser(
        "fix",
        help="AST auto-refactor and self-healing code remediation engine (IMP-0012)",
    )
    fix_parser.add_argument(
        "--path",
        default=".",
        help="Target file or directory to auto-refactor (default: .)",
    )
    fix_parser.add_argument(
        "--auto",
        action="store_true",
        help="Automatically apply and write fixes to source files",
    )
    fix_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate fixes and display diff without writing to disk",
    )
    fix_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    fix_parser.add_argument(
        "--output",
        default=None,
        help="Optional file path to write fix report",
    )

    # Command: clean (ADR-014)
    clean_parser = subparsers.add_parser(
        "clean",
        help="Safe storage optimizer and disk hygiene engine (ADR-014)",
    )
    clean_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate cleanup and display space to be freed without deleting",
    )
    clean_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    # Command: benchmark (IMP-0015)
    bench_parser = subparsers.add_parser(
        "benchmark",
        help="Autonomous Benchmark & Eval Harness for System-One decision engines (IMP-0015)",
    )
    bench_parser.add_argument(
        "--dataset",
        default="data/system_one_dataset.jsonl",
        help="Path to JSONL dataset (default: data/system_one_dataset.jsonl)",
    )
    bench_parser.add_argument(
        "--engines",
        nargs="+",
        default=["heuristic", "onnx"],
        help="Engines to benchmark: heuristic, onnx, outlines (default: heuristic onnx)",
    )
    bench_parser.add_argument(
        "--iterations",
        type=int,
        default=1,
        help="Number of iterations over the dataset (default: 1)",
    )
    bench_parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="Limit number of dataset samples to evaluate (default: all)",
    )
    bench_parser.add_argument(
        "--warmup",
        type=int,
        default=1,
        help="Warmup iterations before recording latencies (default: 1)",
    )
    bench_parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format: text, json, or markdown (default: text)",
    )
    bench_parser.add_argument(
        "--output",
        default=None,
        help="Optional file path to export benchmark report",
    )

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
    if getattr(args, "trace", False):
        ws = Path(getattr(args, "workspace", ".")).resolve()
        task = TaskInput(
            ticket_id="TRACE-DAG",
            description="Simulated DAG trace execution",
            workspace_path=str(ws),
            max_iterations=1,
        )
        graph = AutonomousEngineeringGraph(task=task)
        graph.execute_step()
        report = graph.get_trace_report()
        _print_trace_report(
            report, format_type=args.format, output_path=getattr(args, "output", None)
        )
        return 0

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

    return 0


def handle_pr_link(args: argparse.Namespace) -> int:
    info = generate_pr_url(
        repo_path=".",
        branch=args.branch,
        base=args.base,
        pr_doc_path=args.doc,
        ensure_pushed=args.push,
    )
    if args.format == "json":
        print(json.dumps(info, indent=2))
    else:
        print(f"🔗 Pre-Filled GitHub PR Link [{info['branch']} -> {info['base']}]:")
        print(f"  - Ticket: {info['ticket_id']}")
        print(f"  - Título: {info['title']}")
        push_label = "✅ Sincronizado no origin" if info.get("pushed") else "⚠️  Local apenas"
        print(f"  - Push Status: {push_label}")
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


def _print_trace_report(
    report: Any, format_type: str = "text", output_path: str | None = None
) -> None:
    if format_type == "json":
        output_str = report.model_dump_json(indent=2)
    else:
        lines = [
            "\n" + "=" * 60,
            f"🛰️  OpenTelemetry Trace Report: {report.trace_id}",
            "=" * 60,
            f"• Root Operation: {report.root_span_name}",
            f"• Total Spans: {report.total_spans}",
            f"• Total Duration: {report.total_duration_ms:.2f} ms",
            f"• Total Tokens: {report.total_tokens}",
            f"• Global Status: {'✅ OK' if report.status == 'OK' else '❌ ERROR'}",
            "\n--- Spans Waterfall ---",
        ]
        for s in report.spans:
            status_icon = "✓" if s.status == "OK" else "✗"
            parent_info = f" (parent: {s.parent_span_id})" if s.parent_span_id else " (ROOT)"
            lines.append(f"  [{status_icon}] {s.name:<32} {s.duration_ms:8.2f} ms {parent_info}")
            if s.attributes:
                for k, v in list(s.attributes.items())[:3]:
                    lines.append(f"      • {k} = {v}")
            if s.error_message:
                lines.append(f"      ⚠️ Error: {s.error_message}")
        lines.append("=" * 60 + "\n")
        output_str = "\n".join(lines)

    if output_path:
        out_p = Path(output_path).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(output_str, encoding="utf-8")
        print(f"✅ Relatório de telemetria salvo em: {out_p}")
    else:
        print(output_str)


def handle_telemetry(args: argparse.Namespace) -> int:
    from corporate_engineer.models import TraceReport
    from corporate_engineer.telemetry.tracer import AgentTracer

    if args.file:
        p = Path(args.file).resolve()
        if not p.exists():
            print(f"❌ Arquivo de trace não encontrado: {p}")
            return 1
        content = p.read_text(encoding="utf-8")
        report = TraceReport.model_validate_json(content)
    else:
        tracer = AgentTracer()
        with tracer.span("telemetry.sample", attributes={"sample": True}):
            pass
        report = tracer.export_trace()

    _print_trace_report(report, format_type=args.format, output_path=args.output)
    return 0


def handle_test_surgical(args: argparse.Namespace) -> int:
    from corporate_engineer.quality.surgical_runner import SurgicalTestRunner

    runner = SurgicalTestRunner(root_path=Path(args.workspace).resolve())
    extra_args = args.pytest_extra_args if getattr(args, "pytest_extra_args", None) else None
    report = runner.run(
        base_branch=args.base_branch,
        max_depth=args.depth,
        dry_run=args.dry_run,
        fallback_all=args.fallback_all,
        extra_args=extra_args,
    )

    if args.format == "json":
        output_str = report.model_dump_json(indent=2)
    else:
        lines = [
            "\n" + "=" * 60,
            "🔬 CORPORATE SURGICAL TDD RUNNER (IMP-0010)",
            "=" * 60,
            f"📌 Base Branch: {report.base_branch}",
            f"📂 Changed Files ({len(report.changed_files)}):",
        ]
        if report.changed_files:
            for f in report.changed_files:
                lines.append(f"   • {f}")
        else:
            lines.append("   (nenhum arquivo alterado detectado no Git diff / working tree)")

        lines.append(f"\n🎯 Affected Tests via Blast Radius ({len(report.affected_tests)}):")
        if report.affected_tests:
            for t in report.affected_tests:
                lines.append(f"   ⚡ {t}")
        else:
            lines.append("   (nenhum teste afetado detectado)")

        if report.command:
            lines.append(f"\n⚙️  Command: {report.command}")

        if report.executed:
            status_symbol = "✅ PASS" if report.passed else "❌ FAIL"
            lines.append(f"⏱️  Duration: {report.duration_ms:.2f} ms")
            lines.append(f"📊 Result: {status_symbol} (exit code: {report.exit_code})")
            if report.stdout:
                lines.append("\n--- Pytest Output ---")
                lines.append(report.stdout.strip())
            if report.stderr:
                lines.append("\n--- Pytest Stderr ---")
                lines.append(report.stderr.strip())
        elif report.affected_tests:
            lines.append("ℹ️  Dry-run mode: testes não executados.")

        lines.append("=" * 60 + "\n")
        output_str = "\n".join(lines)

    if args.output:
        out_p = Path(args.output).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(output_str, encoding="utf-8")
        print(f"✅ Relatório de teste cirúrgico salvo em: {out_p}")
    else:
        print(output_str)

    return report.exit_code if report.executed else 0


def handle_decide(args: argparse.Namespace) -> int:
    from corporate_engineer.system_one.base import SystemOneEngine
    from corporate_engineer.system_one.heuristic_engine import HeuristicDecisionEngine
    from corporate_engineer.system_one.nli_engine import ONNXNLIDecisionEngine
    from corporate_engineer.system_one.outlines_engine import OutlinesDecisionEngine
    from corporate_engineer.system_one.router import SystemOneRouter

    engine: SystemOneEngine
    if args.engine == "outlines":
        engine = OutlinesDecisionEngine(fallback_to_heuristic=True)
    elif args.engine in ("nli", "onnx"):
        engine = ONNXNLIDecisionEngine(fallback_to_heuristic=True)
    else:
        engine = HeuristicDecisionEngine()

    router = SystemOneRouter(engine=engine)
    prompt = args.prompt or ""

    diff_content = args.diff or ""
    if diff_content and os.path.exists(diff_content) and os.path.isfile(diff_content):
        try:
            diff_content = Path(diff_content).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            pass

    if args.mode == "route":
        decision = router.route_agent(prompt)
        if args.format == "json":
            output_str = decision.model_dump_json(indent=2)
        else:
            output_str = (
                f"\n{'=' * 60}\n"
                f"⚡ SYSTEM-ONE AGENT ROUTING (IMP-0013)\n"
                f"{'=' * 60}\n"
                f"🎯 Target Agent  : {decision.choice}\n"
                f"📊 Confidence    : {decision.confidence:.2%}\n"
                f"💡 Rationale     : {decision.rationale}\n"
                f"⚙️  Engine        : {args.engine}\n"
            )
            if decision.probabilities:
                output_str += "📈 Distribution  :\n"
                for opt, prob in sorted(
                    decision.probabilities.items(), key=lambda x: x[1], reverse=True
                )[:5]:
                    output_str += f"   • {opt:<22}: {prob:.2%}\n"
            output_str += f"{'=' * 60}\n"

    elif args.mode == "risk":
        noul = router.assess_risk(diff_content or prompt)
        if args.format == "json":
            output_str = noul.model_dump_json(indent=2)
        else:
            risk_label = "🚨 HIGH RISK / CRITICAL" if noul.decision else "✅ LOW / MODERATE"
            output_str = (
                f"\n{'=' * 60}\n"
                f"🛡️  SYSTEM-ONE RISK ASSESSMENT (IMP-0013)\n"
                f"{'=' * 60}\n"
                f"⚖️  High Risk      : {noul.decision} ({risk_label})\n"
                f"📊 Probability    : {noul.probability:.2%}\n"
                f"💡 Rationale      : {noul.rationale}\n"
                f"{'=' * 60}\n"
            )

    elif args.mode == "commit":
        decision = router.classify_commit(diff_content or prompt)
        if args.format == "json":
            output_str = decision.model_dump_json(indent=2)
        else:
            output_str = (
                f"\n{'=' * 60}\n"
                f"🏷️  SYSTEM-ONE COMMIT CLASSIFICATION (IMP-0014)\n"
                f"{'=' * 60}\n"
                f"🎯 Commit Type   : {decision.choice}\n"
                f"📊 Confidence    : {decision.confidence:.2%}\n"
                f"💡 Rationale     : {decision.rationale}\n"
                f"{'=' * 60}\n"
            )

    elif args.mode == "skip":
        node_name = prompt or "security_scan"
        noul = router.should_skip_node(node_name=node_name, context=diff_content or prompt)
        if args.format == "json":
            output_str = noul.model_dump_json(indent=2)
        else:
            status_label = "⏭️  SKIP (DISPENSÁVEL)" if noul.decision else "▶️  EXECUTE (MANDATÓRIO)"
            output_str = (
                f"\n{'=' * 60}\n"
                f"⚡ SYSTEM-ONE DAG NODE SKIP EVALUATION (IMP-0014)\n"
                f"{'=' * 60}\n"
                f"📌 Target Node   : {node_name}\n"
                f"⚖️  Should Skip   : {noul.decision} ({status_label})\n"
                f"📊 Probability   : {noul.probability:.2%}\n"
                f"💡 Rationale     : {noul.rationale}\n"
                f"{'=' * 60}\n"
            )

    else:  # triage
        report = router.triage_quality_gate(prompt=prompt, diff=diff_content)
        if args.format == "json":
            output_str = report.model_dump_json(indent=2)
        else:
            output_str = (
                f"\n{'=' * 60}\n"
                f"🔬 SYSTEM-ONE QUALITY GATE TRIAGE (IMP-0013 / IMP-0014)\n"
                f"{'=' * 60}\n"
                f"🎯 Suggested Agent       : {report.suggested_agent or 'N/A'}\n"
                f"🚨 Risk Level             : {report.risk_level}\n"
                f"🛑 Requires Human Approval: {report.requires_human_approval}\n"
                f"⏱️  Duration               : {report.duration_ms:.2f} ms\n"
                f"⚙️  Engine                 : {report.engine_name}\n"
                f"{'=' * 60}\n"
            )

    if args.output:
        out_p = Path(args.output).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(output_str, encoding="utf-8")
        print(f"✅ Relatório salvo em: {out_p}")
    else:
        print(output_str)

    return 0


def handle_dataset(args: argparse.Namespace) -> int:
    from corporate_engineer.system_one.dataset import SystemOneDatasetGenerator
    from corporate_engineer.system_one.trainer import SystemOneTrainer

    if args.action == "recipe":
        trainer = SystemOneTrainer(model_id=args.model)
        out_path = Path(args.output or "scripts/train_system_one_colab.py").resolve()
        trainer.save_recipe(out_path)
        print(
            f"\n{'=' * 60}\n"
            f"🚀 SYSTEM-ONE COLAB 1-CLICK RECIPE GERADA (IMP-0014)\n"
            f"{'=' * 60}\n"
            f"📄 Arquivo Salvo : {out_path}\n"
            f"🤖 Modelo Alvo   : {args.model}\n"
            f"💡 Instruções    : Abra no Google Colab (GPU T4 grátis), faça upload do dataset JSONL e execute!\n"
            f"{'=' * 60}\n"
        )
        return 0

    generator = SystemOneDatasetGenerator()
    out_file = Path(args.output or "data/system_one_dataset.jsonl").resolve()
    report = generator.export_dataset(
        output_path=out_file,
        agent_samples=args.samples,
        risk_samples=args.samples,
        commit_samples=args.samples,
        skip_samples=args.samples,
    )

    if args.format == "json":
        print(report.model_dump_json(indent=2))
    else:
        print(
            f"\n{'=' * 60}\n"
            f"📦 SYSTEM-ONE SYNTHETIC DATASET GERADO (IMP-0014)\n"
            f"{'=' * 60}\n"
            f"📊 Total de Amostras : {report.total_samples}\n"
            f"📁 Arquivo de Saída  : {report.export_path}\n"
            f"🔒 Checksum SHA-256  : {report.hash_sha256[:16]}...\n"
            f"📈 Distribuição      :\n"
        )
        for cat, count in report.task_distribution.items():
            print(f"   • {cat:<22}: {count} amostras")
        print(f"{'=' * 60}\n")

    return 0


def handle_fix(args: argparse.Namespace) -> int:
    from corporate_engineer.eval.fixer import ASTSelfHealingFixer

    fixer = ASTSelfHealingFixer()
    target_path = Path(args.path).resolve()

    dry_run = not args.auto or args.dry_run

    if target_path.is_file():
        report = fixer.fix_file(target_path, dry_run=dry_run)
    else:
        report = fixer.fix_workspace(target_path, dry_run=dry_run)

    if args.format == "json":
        output_str = json.dumps(report.model_dump(), indent=2, ensure_ascii=False)
    else:
        status_mode = (
            "[DRY RUN - SEM ESCRITA]" if report.dry_run else "[AUTO FIX - MODIFICAÇÕES GRAVADAS]"
        )
        lines = [
            f"\n{'=' * 60}",
            "🛠️  AST Auto-Refactor & Self-Healing Fixer (IMP-0012)",
            f"{'=' * 60}",
            f"📁 Alvo               : {target_path}",
            f"⚙️  Modo               : {status_mode}",
            f"📊 Arquivos Analisados: {report.total_files_analyzed}",
            f"✏️  Arquivos Modificados: {report.files_modified}",
            f"🔧 Correções Aplicadas: {len(report.fixes_applied)}",
            f"🛡️  Risco Sistema 1    : {report.system_one_risk}",
            f"{'-' * 60}",
        ]
        if report.fixes_applied:
            lines.append("📋 Detalhes das Correções:")
            for fix in report.fixes_applied:
                lines.append(
                    f"   • [{fix.rule_name}] {fix.file_path}:{fix.line_number} - {fix.description}"
                )
        else:
            lines.append("✨ Nenhuma inconformidade estrutural detectada.")
        lines.append(f"{'=' * 60}\n")
        output_str = "\n".join(lines)

    if args.output:
        Path(args.output).write_text(output_str, encoding="utf-8")
        print(f"Relatório de correções salvo em: {args.output}")
    else:
        print(output_str)

    return 0


def handle_clean(args: argparse.Namespace) -> int:
    from corporate_engineer.quality.storage_cleaner import SafeStorageCleaner

    cleaner = SafeStorageCleaner()
    report = cleaner.clean_all(dry_run=args.dry_run)

    if args.format == "json":
        output_str = json.dumps(report.model_dump(), indent=2, ensure_ascii=False)
    else:
        status_mode = "[SIMULAÇÃO / DRY RUN]" if report.dry_run else "[LIMPEZA EXECUTADA]"
        lines = [
            f"\n{'=' * 60}",
            "🧹  Safe Storage Optimizer & Disk Hygiene Engine (ADR-014)",
            f"{'=' * 60}",
            f"⚙️  Modo               : {status_mode}",
            f"📊 Total Liberado     : {report.total_freed_gb} GB ({report.total_freed_bytes:,} bytes)",
            f"🎯 Alvos Processados  : {len(report.results)}",
            f"{'-' * 60}",
        ]
        for res in report.results:
            status_symbol = "✅" if res.success else "❌"
            error_msg = f" ({res.error})" if res.error else ""
            mb = round(res.freed_bytes / (1024**2), 2)
            lines.append(f"   {status_symbol} [{res.target_name}] {res.path} -> {mb} MB{error_msg}")
        lines.append(f"{'=' * 60}\n")
        output_str = "\n".join(lines)

    print(output_str)
    return 0


def handle_benchmark(args: argparse.Namespace) -> int:
    from corporate_engineer.system_one.benchmark import SystemOneBenchmark

    bench = SystemOneBenchmark(dataset_path=args.dataset)
    report = bench.run(
        engines=args.engines,
        dataset_path=args.dataset,
        max_samples=args.max_samples,
        iterations=args.iterations,
        warmup=args.warmup,
    )

    if args.format == "json":
        output_str = report.model_dump_json(indent=2)
    elif args.format == "markdown":
        lines = [
            f"# System-One Benchmark Report ({report.timestamp})",
            f"- **Dataset**: `{report.dataset_path}` ({report.sample_count} samples)",
            f"- **Iterations**: {report.iterations}",
            f"- **Winner Latência**: 🏆 `{report.winner_latency}`",
            f"- **Winner Acurácia**: 🎯 `{report.winner_accuracy}`",
            "",
            "| Motor | Acurácia (%) | P50 (ms) | P95 (ms) | P99 (ms) | Média (ms) | Throughput (RPS) |",
            "|---|---|---|---|---|---|---|",
        ]
        for name, res in report.engines.items():
            lines.append(
                f"| `{name}` | {res.accuracy_percent}% | {res.latency.p50_ms} | "
                f"{res.latency.p95_ms} | {res.latency.p99_ms} | {res.latency.mean_ms} | "
                f"{res.throughput_rps} |"
            )
        lines.append("")
        lines.append("### Recomendações:")
        for rec in report.recommendations:
            lines.append(f"- {rec}")
        output_str = "\n".join(lines)
    else:
        lines = [
            f"\n{'=' * 75}",
            "⚡  SYSTEM-ONE AUTONOMOUS BENCHMARK & EVAL HARNESS (IMP-0015)",
            f"{'=' * 75}",
            f"📁 Dataset           : {report.dataset_path} ({report.sample_count} amostras)",
            f"🔄 Iterações         : {report.iterations}",
            f"🏆 Vencedor Latência : {report.winner_latency}",
            f"🎯 Vencedor Acurácia : {report.winner_accuracy}",
            f"{'-' * 75}",
            f"{'MOTOR':<12} {'ACURÁCIA':<12} {'P50 (ms)':<10} {'P95 (ms)':<10} {'P99 (ms)':<10} {'THROUGHPUT':<12}",
            f"{'-' * 75}",
        ]
        for name, res in report.engines.items():
            acc_str = f"{res.accuracy_percent}%"
            p50_str = f"{res.latency.p50_ms:.3f}"
            p95_str = f"{res.latency.p95_ms:.3f}"
            p99_str = f"{res.latency.p99_ms:.3f}"
            rps_str = f"{res.throughput_rps:.1f} rps"
            lines.append(
                f"{name:<12} {acc_str:<12} {p50_str:<10} {p95_str:<10} {p99_str:<10} {rps_str:<12}"
            )
        lines.append(f"{'-' * 75}")
        lines.append("💡 Recomendações:")
        for rec in report.recommendations:
            lines.append(f"   • {rec}")
        lines.append(f"{'=' * 75}\n")
        output_str = "\n".join(lines)

    if args.output:
        out_p = Path(args.output)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(output_str, encoding="utf-8")
        print(f"[✓] Benchmark report exported to {args.output}")

    print(output_str)
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
    elif args.command == "pr-link":
        return handle_pr_link(args)
    elif args.command == "eval":
        return handle_eval(args)
    elif args.command == "blast-radius":
        return handle_blast_radius(args)
    elif args.command == "telemetry":
        return handle_telemetry(args)
    elif args.command == "test-surgical":
        return handle_test_surgical(args)
    elif args.command == "decide":
        return handle_decide(args)
    elif args.command == "dataset":
        return handle_dataset(args)
    elif args.command == "fix":
        return handle_fix(args)
    elif args.command == "clean":
        return handle_clean(args)
    elif args.command == "benchmark":
        return handle_benchmark(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
