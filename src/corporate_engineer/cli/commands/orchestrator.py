"""
Orchestrator CLI Commands (run, dag, swarm, anticipate).
Modular domain command package decomposed according to ADR-026 / IMP-0023.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from corporate_engineer.models import TaskInput
from corporate_engineer.orchestrator.graph import AutonomousEngineeringGraph

DAG_PHASES = ["PLANNING", "TDD", "IMPLEMENT", "AUDIT", "DELIVER"]
DAG_TRANSITIONS = [
    {"from": "PLANNING", "to": "TDD", "trigger": "step_plan"},
    {"from": "TDD", "to": "IMPLEMENT", "trigger": "step_tdd"},
    {"from": "IMPLEMENT", "to": "AUDIT", "trigger": "step_implement"},
    {"from": "AUDIT", "to": "DELIVER", "trigger": "step_audit(passed=True)"},
    {"from": "AUDIT", "to": "IMPLEMENT", "trigger": "step_audit(passed=False)"},
]


def register_run_parser(subparsers: Any) -> argparse.ArgumentParser:
    """Register parser for `run` command."""
    run_parser = subparsers.add_parser("run", help="Run an autonomous engineering task")
    run_parser.add_argument("--ticket", required=True, help="Ticket ID (e.g. JIRA-101)")
    run_parser.add_argument("--task", required=True, help="Task description")
    run_parser.add_argument("--workspace", default=".", help="Workspace path")
    run_parser.add_argument("--max-turns", type=int, default=20, help="Max iteration turns")
    run_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in safe simulation mode without mutating repository source files",
    )
    run_parser.add_argument(
        "--strict-audit",
        action="store_true",
        help="Run strict test suite verification in audit gate",
    )
    run_parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output report format (default: text)",
    )
    run_parser.add_argument(
        "--output",
        default=None,
        help="Optional file path to export execution report",
    )
    return run_parser


def register_dag_parser(subparsers: Any) -> argparse.ArgumentParser:
    """Register parser for `dag` command."""
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
    return dag_parser


def register_swarm_parser(subparsers: Any) -> argparse.ArgumentParser:
    """Register parser for `swarm` command."""
    swarm_parser = subparsers.add_parser(
        "swarm",
        help="Multi-Agent Swarm Coordinator via MCP Hub (IMP-0016)",
    )
    swarm_parser.add_argument(
        "--goal",
        default="Revisão Tripartite de Arquitetura e Qualidade",
        help="Main goal or directive for the agent swarm",
    )
    swarm_parser.add_argument(
        "--roles",
        nargs="+",
        default=["architect", "security-reviewer", "code-reviewer"],
        help="Specialized agent roles to deploy in the swarm",
    )
    swarm_parser.add_argument(
        "--mode",
        choices=["fanout", "consensus"],
        default="fanout",
        help="Swarm execution mode: fanout (concurrent tasks) or consensus (multi-perspective review)",
    )
    swarm_parser.add_argument(
        "--target",
        default="",
        help="Target artifact, module or description for consensus review",
    )
    swarm_parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Max concurrent worker threads (default: 4)",
    )
    swarm_parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format: text, json, or markdown (default: text)",
    )
    swarm_parser.add_argument(
        "--output",
        default=None,
        help="Optional file path to export swarm goal report",
    )
    return swarm_parser


def register_anticipate_parser(subparsers: Any) -> argparse.ArgumentParser:
    """Register parser for `anticipate` command."""
    anticipate_parser = subparsers.add_parser(
        "anticipate",
        help="Proactive Anticipation Engine (2 passos à frente) (IMP-0025)",
    )
    anticipate_parser.add_argument("prompt", help="Prompt or task to anticipate")
    anticipate_parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="markdown",
        help="Output format: text, json, or markdown (default: markdown)",
    )
    anticipate_parser.add_argument(
        "--workspace",
        "-w",
        default=".",
        help="Workspace path for AST and code context (default: .)",
    )
    anticipate_parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Optional file path to write anticipation plan",
    )
    return anticipate_parser


def handle_run(args: argparse.Namespace) -> int:
    task = TaskInput(
        ticket_id=args.ticket,
        description=args.task,
        workspace_path=str(Path(args.workspace).resolve()),
        max_iterations=args.max_turns,
    )
    graph = AutonomousEngineeringGraph(task=task)
    dry_run = getattr(args, "dry_run", False)
    strict_audit = getattr(args, "strict_audit", False)
    fmt = getattr(args, "format", "text")
    output_path = getattr(args, "output", None)

    # Executa o ciclo de vida completo autônomo
    report = graph.run_pipeline(
        dry_run=dry_run,
        auto_deliver=True,
        strict_audit=strict_audit,
    )

    if fmt == "json":
        output_str = report.model_dump_json(indent=2)
    elif fmt == "markdown":
        output_str = (
            f"# Relatório de Execução de Engenharia Autônoma: {report.ticket_id}\n\n"
            f"- **Ticket**: `{report.ticket_id}`\n"
            f"- **Status**: `{report.status}`\n"
            f"- **Fase Final**: `{report.final_phase}`\n"
            f"- **Iterações**: {report.iterations}\n"
            f"- **Modo**: {'Simulação (Dry-Run)' if report.dry_run else 'Produção (Live)'}\n"
            f"- **Auditoria de Qualidade**: {'APROVADA' if report.audit_passed else 'REPROVADA'}\n"
            f"- **Duração**: {report.duration_seconds}s\n\n"
            f"## Checkpoints Salvos\n"
            + "\n".join(f"- `{cp}`" for cp in report.checkpoints_created)
            + f"\n\n## Plano Refinado\n```text\n{report.refined_plan}\n```\n"
        )
    else:
        lines = [
            f"🚀 Iniciando Engenheiro Autônomo para o ticket: {task.ticket_id}",
            f"📝 Descrição: {task.description}",
            "🔄 Fase Inicial: PLANNING",
            "✅ Grafo inicializado com sucesso.",
            f"⚡ Executando ciclo de vida: PLANNING -> TDD -> IMPLEMENT -> AUDIT -> {report.final_phase}",
            f"📊 Status Final: {report.status} (Fase: {report.final_phase})",
            f"⏱️ Duração: {report.duration_seconds}s | Iterações: {report.iterations}",
            f"💾 Checkpoints Gerados ({len(report.checkpoints_created)}): {', '.join(report.checkpoints_created)}",
        ]
        if report.audit_passed:
            lines.append("🛡️ Portão de Auditoria & Pre-Flight: PASS")
        else:
            lines.append("⚠️ Portão de Auditoria: FAILED")
        output_str = "\n".join(lines)

    if output_path:
        out_p = Path(output_path).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(output_str, encoding="utf-8")
        if fmt != "json":
            print(f"✅ Relatório de execução salvo com sucesso em: {out_p}")
    else:
        print(output_str)

    return 0 if report.status == "SUCCESS" else 1


def handle_dag(args: argparse.Namespace) -> int:
    from corporate_engineer.cli.commands.telemetry import _print_trace_report

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


def handle_swarm(args: argparse.Namespace) -> int:
    from corporate_engineer.orchestrator.swarm import SwarmCoordinator

    coordinator = SwarmCoordinator()

    if args.mode == "consensus":
        target = args.target or args.goal
        report = coordinator.run_consensus(
            target_description=target,
            reviewer_roles=args.roles,
            max_workers=args.workers,
        )
    else:
        subtasks = [{"role": role, "task": f"{args.goal} - foco em {role}"} for role in args.roles]
        report = coordinator.run_fan_out(
            goal=args.goal,
            subtasks=subtasks,
            max_workers=args.workers,
        )

    if args.format == "json":
        output_str = report.model_dump_json(indent=2)
    elif args.format == "markdown":
        lines = [
            f"# Swarm Goal Report: {report.goal}",
            f"- **Swarm**: `{report.swarm_name}`",
            f"- **Agentes**: {report.total_agents} ({report.successful_tasks} sucessos, {report.failed_tasks} falhas)",
            f"- **Tempo Total**: {report.execution_time_ms} ms",
            f"- **Consenso**: {report.aggregated_consensus}",
            "",
            "## Pareceres dos Especialistas",
            "| Agente | Papel | Status | Latência (ms) | Parecer |",
            "|---|---|---|---|---|",
        ]
        for res in report.results:
            status_symbol = "✅" if res.success else "❌"
            lines.append(
                f"| `{res.agent_id}` | `{res.role}` | {status_symbol} | {res.execution_time_ms} | {res.output} |"
            )
        lines.append("")
        lines.append("## Recomendações:")
        for rec in report.recommendations:
            lines.append(f"- {rec}")
        output_str = "\n".join(lines)
    else:
        lines = [
            f"\n{'=' * 75}",
            "🐝  MULTI-AGENT SWARM COORDINATOR VIA MCP HUB (IMP-0016)",
            f"{'=' * 75}",
            f"🎯 Meta Geral      : {report.goal}",
            f"👥 Agentes Ativos  : {report.total_agents} ({report.successful_tasks} concluídas, {report.failed_tasks} falhas)",
            f"⏱️  Tempo Total     : {report.execution_time_ms} ms",
            f"⚖️  Consenso        : {report.aggregated_consensus}",
            f"{'-' * 75}",
            f"{'AGENTE':<10} {'PAPEL':<20} {'STATUS':<8} {'TEMPO (ms)':<12} {'PARECER RESUMIDO'}",
            f"{'-' * 75}",
        ]
        for res in report.results:
            status_text = "OK" if res.success else "ERRO"
            short_out = (res.output[:45] + "...") if len(res.output) > 45 else res.output
            lines.append(
                f"{res.agent_id:<10} {res.role:<20} {status_text:<8} {res.execution_time_ms:<12.3f} {short_out}"
            )
        lines.append(f"{'-' * 75}")
        lines.append("💡 Recomendações do Enxame:")
        for rec in report.recommendations:
            lines.append(f"   • {rec}")
        lines.append(f"{'=' * 75}\n")
        output_str = "\n".join(lines)

    if args.output:
        out_p = Path(args.output)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(output_str, encoding="utf-8")
        print(f"[✓] Swarm report exported to {args.output}")

    print(output_str)
    return 0


def handle_anticipate(args: argparse.Namespace) -> int:
    from corporate_engineer.orchestrator.anticipator import ProactiveAnticipator

    workspace = Path(args.workspace).resolve()
    anticipator = ProactiveAnticipator(workspace_path=workspace)
    plan = anticipator.anticipate(args.prompt)

    fmt = getattr(args, "format", "markdown")
    if fmt == "json":
        output_text = plan.model_dump_json(indent=2)
    elif fmt == "markdown":
        output_text = anticipator.format_markdown(plan)
    else:
        output_text = (
            f"Domínio: {plan.target_domain} | Risco: {plan.risk_level}\n"
            f"Passo 1 ({plan.step_immediate_1.phase}): {plan.step_immediate_1.action}\n"
            f"Passo 2 ({plan.step_subsequent_2.phase}): {plan.step_subsequent_2.action}\n"
        )

    out_file = getattr(args, "output", None)
    if out_file:
        Path(out_file).write_text(output_text, encoding="utf-8")
        print(f"Plano antecipatório exportado para: {out_file}")
    else:
        print(output_text)

    return 0
