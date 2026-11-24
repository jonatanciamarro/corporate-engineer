"""
CLI Argument Parser Builder.
Constructs the central ArgumentParser by registering domain command parsers.
"""

from __future__ import annotations

import argparse

from corporate_engineer.cli.commands.lora import register_lora_parser
from corporate_engineer.cli.commands.mcp import register_mcp_parser
from corporate_engineer.cli.commands.orchestrator import (
    register_anticipate_parser,
    register_dag_parser,
    register_run_parser,
    register_swarm_parser,
)
from corporate_engineer.cli.commands.pr import register_pr_parser
from corporate_engineer.cli.commands.prompt import register_prompt_parser
from corporate_engineer.cli.commands.quality import (
    register_audit_parser,
    register_clean_parser,
    register_fix_parser,
    register_test_surgical_parser,
)
from corporate_engineer.cli.commands.rag import (
    register_blast_radius_parser,
    register_eval_parser,
    register_index_parser,
)
from corporate_engineer.cli.commands.system_one import (
    register_benchmark_parser,
    register_dataset_parser,
    register_decide_parser,
)
from corporate_engineer.cli.commands.telemetry import register_telemetry_parser


def build_parser() -> argparse.ArgumentParser:
    """Build and return the top-level corporate-engineer argument parser."""
    parser = argparse.ArgumentParser(
        prog="corporate-engineer",
        description="Autonomous Corporate Software Engineer - Open Source Enterprise Framework",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command registrations across domain modules
    register_run_parser(subparsers)
    register_index_parser(subparsers)
    register_audit_parser(subparsers)
    register_dag_parser(subparsers)
    register_mcp_parser(subparsers)
    register_pr_parser(subparsers)
    register_eval_parser(subparsers)
    register_blast_radius_parser(subparsers)
    register_telemetry_parser(subparsers)
    register_test_surgical_parser(subparsers)
    register_decide_parser(subparsers)
    register_dataset_parser(subparsers)
    register_fix_parser(subparsers)
    register_clean_parser(subparsers)
    register_benchmark_parser(subparsers)
    register_swarm_parser(subparsers)
    register_prompt_parser(subparsers)
    register_lora_parser(subparsers)
    register_anticipate_parser(subparsers)

    return parser
