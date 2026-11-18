"""
Command Line Interface for Autonomous Corporate Software Engineer.
"""

import argparse
import sys
from pathlib import Path

from corporate_engineer.models import TaskInput
from corporate_engineer.orchestrator.graph import AutonomousEngineeringGraph
from corporate_engineer.quality.gate import QualityGateRunner
from corporate_engineer.rag.ast_indexer import ASTCodebaseIndexer


def main():
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

    # Command: audit
    audit_parser = subparsers.add_parser("audit", help="Run pre-flight security and quality audit")
    audit_parser.add_argument("--path", default=".", help="Path to audit")

    args = parser.parse_args()

    if args.command == "run":
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

    elif args.command == "index":
        target = Path(args.path).resolve()
        indexer = ASTCodebaseIndexer(root_path=target)
        outline = indexer.build_codebase_outline()
        print(outline)

    elif args.command == "audit":
        target = Path(args.path).resolve()
        runner = QualityGateRunner(project_root=target)
        res = runner.run_secret_scan()
        if res["passed"]:
            print("✅ Pre-Flight Secret Scan PASS: Zero segredos detectados.")
        else:
            print("❌ Segredos encontrados:")
            for f in res["findings"]:
                print(f" - {f['file']}:{f['line']} [{f['type']}]")
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
