"""
Test Suite for Modular CLI Architecture (IMP-0023 / ADR-026).
Shift-Left TDD: Verifies decomposition of the CLI monolith into modular domain packages.
"""

from pathlib import Path

import corporate_engineer.cli


def test_cli_package_public_exports():
    """Verify corporate_engineer.cli package re-exports main, build_parser, and all command handlers."""
    expected_exports = [
        "main",
        "build_parser",
        "handle_run",
        "handle_index",
        "handle_audit",
        "handle_dag",
        "handle_mcp",
        "handle_pr_link",
        "handle_eval",
        "handle_blast_radius",
        "handle_telemetry",
        "handle_test_surgical",
        "handle_decide",
        "handle_dataset",
        "handle_fix",
        "handle_clean",
        "handle_benchmark",
        "handle_swarm",
        "handle_prompt",
        "handle_lora",
        "handle_anticipate",
    ]
    for export_name in expected_exports:
        assert hasattr(corporate_engineer.cli, export_name), (
            f"corporate_engineer.cli missing public export: {export_name}"
        )


def test_cli_command_modules_importable():
    """Verify that domain command modules are cleanly organized in corporate_engineer.cli.commands."""
    from corporate_engineer.cli.commands import (
        lora,
        mcp,
        orchestrator,
        pr,
        prompt,
        quality,
        rag,
        system_one,
        telemetry,
    )

    assert hasattr(orchestrator, "register_run_parser")
    assert hasattr(orchestrator, "handle_run")
    assert hasattr(orchestrator, "register_dag_parser")
    assert hasattr(orchestrator, "handle_dag")
    assert hasattr(orchestrator, "register_swarm_parser")
    assert hasattr(orchestrator, "handle_swarm")
    assert hasattr(orchestrator, "register_anticipate_parser")
    assert hasattr(orchestrator, "handle_anticipate")

    assert hasattr(rag, "register_index_parser")
    assert hasattr(rag, "handle_index")
    assert hasattr(rag, "register_blast_radius_parser")
    assert hasattr(rag, "handle_blast_radius")
    assert hasattr(rag, "register_eval_parser")
    assert hasattr(rag, "handle_eval")

    assert hasattr(quality, "register_audit_parser")
    assert hasattr(quality, "handle_audit")
    assert hasattr(quality, "register_test_surgical_parser")
    assert hasattr(quality, "handle_test_surgical")
    assert hasattr(quality, "register_fix_parser")
    assert hasattr(quality, "handle_fix")
    assert hasattr(quality, "register_clean_parser")
    assert hasattr(quality, "handle_clean")

    assert hasattr(system_one, "register_decide_parser")
    assert hasattr(system_one, "handle_decide")
    assert hasattr(system_one, "register_dataset_parser")
    assert hasattr(system_one, "handle_dataset")
    assert hasattr(system_one, "register_benchmark_parser")
    assert hasattr(system_one, "handle_benchmark")

    assert hasattr(mcp, "register_mcp_parser")
    assert hasattr(mcp, "handle_mcp")

    assert hasattr(prompt, "register_prompt_parser")
    assert hasattr(prompt, "handle_prompt")

    assert hasattr(telemetry, "register_telemetry_parser")
    assert hasattr(telemetry, "handle_telemetry")

    assert hasattr(pr, "register_pr_parser")
    assert hasattr(pr, "handle_pr_link")

    assert hasattr(lora, "register_lora_parser")
    assert hasattr(lora, "handle_lora")


def test_cli_file_size_limits():
    """Verify that no file in corporate_engineer/cli exceeds the 800-line ceiling (ADR-026 invariant)."""
    cli_dir = Path(__file__).resolve().parents[1] / "src" / "corporate_engineer" / "cli"
    assert cli_dir.is_dir(), "cli package directory does not exist"

    for py_file in cli_dir.rglob("*.py"):
        line_count = len(py_file.read_text(encoding="utf-8").splitlines())
        assert line_count < 800, (
            f"File {py_file.name} exceeds 800 lines ceiling: {line_count} lines"
        )
