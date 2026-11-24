"""
Corporate Engineer CLI Subpackage.
Modular command architecture according to ADR-026 / IMP-0023.
"""

from __future__ import annotations

from corporate_engineer.cli.commands.lora import handle_lora
from corporate_engineer.cli.commands.mcp import handle_mcp
from corporate_engineer.cli.commands.orchestrator import (
    DAG_PHASES,
    DAG_TRANSITIONS,
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
from corporate_engineer.cli.main import main
from corporate_engineer.cli.parser import build_parser

__all__ = [
    "DAG_PHASES",
    "DAG_TRANSITIONS",
    "build_parser",
    "handle_anticipate",
    "handle_audit",
    "handle_benchmark",
    "handle_blast_radius",
    "handle_clean",
    "handle_dag",
    "handle_dataset",
    "handle_decide",
    "handle_eval",
    "handle_fix",
    "handle_index",
    "handle_lora",
    "handle_mcp",
    "handle_pr_link",
    "handle_prompt",
    "handle_run",
    "handle_swarm",
    "handle_telemetry",
    "handle_test_surgical",
    "main",
]
