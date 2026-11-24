"""
CLI Main Entry Point and Command Dispatcher.
Executes CLI commands by routing parsed arguments to modular domain handlers.
"""

from __future__ import annotations

import sys

from corporate_engineer.cli.commands.lora import handle_lora
from corporate_engineer.cli.commands.mcp import handle_mcp
from corporate_engineer.cli.commands.orchestrator import (
    handle_anticipate,
    handle_dag,
    handle_run,
    handle_swarm,
)
from corporate_engineer.cli.commands.pr import handle_pr_link
from corporate_engineer.cli.commands.prompt import handle_prompt
from corporate_engineer.cli.commands.quality import (
    handle_audit,
    handle_clean,
    handle_fix,
    handle_test_surgical,
)
from corporate_engineer.cli.commands.rag import (
    handle_blast_radius,
    handle_eval,
    handle_index,
)
from corporate_engineer.cli.commands.system_one import (
    handle_benchmark,
    handle_dataset,
    handle_decide,
)
from corporate_engineer.cli.commands.telemetry import handle_telemetry
from corporate_engineer.cli.parser import build_parser

_DISPATCH_MAP = {
    "run": handle_run,
    "index": handle_index,
    "audit": handle_audit,
    "dag": handle_dag,
    "mcp": handle_mcp,
    "pr-link": handle_pr_link,
    "eval": handle_eval,
    "blast-radius": handle_blast_radius,
    "telemetry": handle_telemetry,
    "test-surgical": handle_test_surgical,
    "decide": handle_decide,
    "dataset": handle_dataset,
    "fix": handle_fix,
    "clean": handle_clean,
    "benchmark": handle_benchmark,
    "swarm": handle_swarm,
    "prompt": handle_prompt,
    "lora": handle_lora,
    "anticipate": handle_anticipate,
}


def main(argv: list[str] | None = None) -> int:
    """Main CLI entry point for corporate-engineer."""
    parser = build_parser()
    args = parser.parse_args(argv)

    handler = _DISPATCH_MAP.get(args.command)
    if handler is not None:
        return handler(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
