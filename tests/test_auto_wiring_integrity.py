"""
tests/test_auto_wiring_integrity.py - Shift-Left TDD Suite for IMP-0029 / ADR-028.
Verifies the Continuous Capability Auto-Wiring Invariant:
1. Every production module in src/corporate_engineer/ is cleanly connected and covered.
2. CapabilityWiringAuditor accurately detects disconnected/orphan code and missing tests.
3. QualityGateRunner integrates run_wiring_audit().
4. CLI audit command exposes --wiring flag.
5. AutonomousEngineeringGraph.run_pipeline attaches wiring audit to execution report.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import patch

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


def test_models_dto_wiring_reports():
    """Verify ModuleWiringStatus and WiringAuditReport exist in corporate_engineer.models."""
    from corporate_engineer.models import ModuleWiringStatus, WiringAuditReport

    status = ModuleWiringStatus(
        module_path="src/corporate_engineer/example.py",
        is_exported=True,
        has_test_coverage=True,
        is_cli_registered=False,
        is_domain_mapped=True,
        exported_symbols=["ExampleClass"],
    )
    assert status.is_exported is True

    report = WiringAuditReport(
        total_modules=1,
        connected_modules=["example"],
        unwired_modules=[],
        missing_test_modules=[],
        orphan_symbols=[],
        passed=True,
        remediation_actions=[],
    )
    assert report.passed is True


def test_capability_wiring_auditor_clean():
    """Verify CapabilityWiringAuditor executes on current workspace and passes."""
    from corporate_engineer.quality.wiring_auditor import CapabilityWiringAuditor

    auditor = CapabilityWiringAuditor(workspace_root=WORKSPACE_ROOT)
    report = auditor.audit()

    assert report.total_modules > 0
    assert report.passed is True
    assert len(report.unwired_modules) == 0
    assert len(report.missing_test_modules) == 0


def test_capability_wiring_auditor_detects_untested_or_orphan_module(tmp_path: Path):
    """Verify CapabilityWiringAuditor detects orphaned modules with missing tests."""
    from corporate_engineer.quality.wiring_auditor import CapabilityWiringAuditor

    # Setup mock workspace
    src_dir = tmp_path / "src" / "corporate_engineer"
    src_dir.mkdir(parents=True)
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(parents=True)

    # Valid connected module
    valid_file = src_dir / "valid_engine.py"
    valid_file.write_text("class ValidEngine:\n    pass\n", encoding="utf-8")
    test_valid = tests_dir / "test_valid_engine.py"
    test_valid.write_text("def test_valid(): pass\n", encoding="utf-8")

    # Orphaned module without tests or export
    orphan_file = src_dir / "orphan_feature.py"
    orphan_file.write_text("class OrphanFeature:\n    pass\n", encoding="utf-8")

    init_file = src_dir / "__init__.py"
    init_file.write_text('__all__ = ["ValidEngine"]\n', encoding="utf-8")

    auditor = CapabilityWiringAuditor(workspace_root=tmp_path)
    report = auditor.audit()

    assert report.passed is False
    assert any("orphan_feature" in m for m in report.unwired_modules)
    assert any("orphan_feature" in m for m in report.missing_test_modules)


def test_quality_gate_runner_run_wiring_audit():
    """Verify QualityGateRunner exposes run_wiring_audit()."""
    from corporate_engineer.quality.gate import QualityGateRunner

    runner = QualityGateRunner(project_root=WORKSPACE_ROOT)
    assert hasattr(runner, "run_wiring_audit")
    res = runner.run_wiring_audit()
    assert "passed" in res
    assert "report" in res
    assert res["passed"] is True


def test_top_level_exports_capability_wiring_auditor():
    """Verify CapabilityWiringAuditor is exported in corporate_engineer top-level."""
    import corporate_engineer

    assert hasattr(corporate_engineer, "CapabilityWiringAuditor")


def test_cli_audit_parser_has_wiring_flag():
    """Verify CLI audit parser supports --wiring flag."""
    from corporate_engineer.cli.commands.quality import register_audit_parser

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()
    audit_parser = register_audit_parser(subparsers)

    actions = [action.dest for action in audit_parser._actions]
    assert "wiring" in actions


def test_autonomous_pipeline_executes_wiring_audit():
    """Verify AutonomousEngineeringGraph.run_pipeline includes wiring audit in details."""
    from corporate_engineer.models import TaskInput
    from corporate_engineer.orchestrator.graph import AutonomousEngineeringGraph

    task = TaskInput(
        ticket_id="TEST-WIRING",
        description="Verify wiring audit integration in pipeline",
        workspace_path=str(WORKSPACE_ROOT),
    )
    graph = AutonomousEngineeringGraph(task=task)

    with (
        patch.object(
            graph.quality_runner,
            "run_tests",
            return_value={"passed": True, "command": "pytest", "stdout": ""},
        ),
        patch.object(
            graph.quality_runner, "run_secret_scan", return_value={"passed": True, "findings": []}
        ),
    ):
        report = graph.run_pipeline(dry_run=True, strict_audit=True)

    assert report.status == "SUCCESS"
    assert "wiring_audit" in report.details
    assert report.details["wiring_audit"]["passed"] is True
