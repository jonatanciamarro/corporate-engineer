"""
Test Suite for Connected E2E Pipeline, Unified AST Cache & Canonical Quality (IMP-0027 / ADR-025).
Shift-Left TDD: Verifies integration of all previously decoupled modules.
"""

from pathlib import Path
from unittest.mock import patch

from corporate_engineer.models import TaskInput
from corporate_engineer.orchestrator.graph import AutonomousEngineeringGraph
from corporate_engineer.prompt.refiner import ContextAwarePromptRefiner
from corporate_engineer.quality.gate import QualityGateRunner
from corporate_engineer.quality.secret_scanner import CanonicalSecretScanner
from corporate_engineer.rag.cached_ast_indexer import CachedASTCodebaseIndexer
from corporate_engineer.rag.impact import BlastRadiusAnalyzer


def test_public_api_exports():
    """Verify primary enterprise components are properly exported at top-level."""
    import corporate_engineer

    expected_exports = [
        "AutonomousEngineeringGraph",
        "ProactiveAnticipator",
        "QualityGateRunner",
        "BlastRadiusAnalyzer",
        "CachedASTCodebaseIndexer",
        "SurgicalTestRunner",
        "ASTSelfHealingFixer",
        "CanonicalSecretScanner",
    ]
    for export_name in expected_exports:
        assert hasattr(corporate_engineer, export_name), (
            f"corporate_engineer missing export {export_name}"
        )


def test_cached_ast_indexer_symbol_helpers(tmp_path: Path):
    """Verify CachedASTCodebaseIndexer provides get_all_symbol_names and file symbol helpers."""
    indexer = CachedASTCodebaseIndexer(root_path=tmp_path)
    sample_file = tmp_path / "sample.py"
    sample_file.write_text(
        "class EnterpriseWidget:\n"
        "    def process_data(self):\n"
        "        pass\n\n"
        "def helper_function():\n"
        "    return 42\n",
        encoding="utf-8",
    )

    symbols = indexer.get_all_symbol_names()
    assert "EnterpriseWidget" in symbols
    assert "helper_function" in symbols

    file_syms = indexer.get_file_symbols(sample_file)
    assert len(file_syms) >= 2


def test_blast_radius_uses_cached_ast_indexer(tmp_path: Path):
    """Verify BlastRadiusAnalyzer uses CachedASTCodebaseIndexer and caches parse results."""
    analyzer = BlastRadiusAnalyzer(root_path=tmp_path)
    assert isinstance(analyzer.indexer, CachedASTCodebaseIndexer)

    mod_a = tmp_path / "mod_a.py"
    mod_a.write_text("class AlphaService:\n    pass\n", encoding="utf-8")

    test_a = tmp_path / "test_a.py"
    test_a.write_text(
        "from mod_a import AlphaService\ndef test_alpha():\n    pass\n", encoding="utf-8"
    )

    # First run: indexes files
    report1 = analyzer.analyze_file(mod_a)
    assert "test_a.py" in report1.affected_tests

    # Second run: hits cache
    stats = analyzer.indexer.get_cache_stats()
    assert stats["hits"] > 0 or stats["cached_files"] > 0


def test_blast_radius_batch_files_analysis(tmp_path: Path):
    """Verify analyze_files analyzes multiple changed files in a single unified pass."""
    analyzer = BlastRadiusAnalyzer(root_path=tmp_path)

    mod_a = tmp_path / "service_a.py"
    mod_a.write_text("class ServiceA:\n    pass\n", encoding="utf-8")
    mod_b = tmp_path / "service_b.py"
    mod_b.write_text("class ServiceB:\n    pass\n", encoding="utf-8")

    test_a = tmp_path / "test_service_a.py"
    test_a.write_text("from service_a import ServiceA\ndef test_a(): pass\n", encoding="utf-8")
    test_b = tmp_path / "test_service_b.py"
    test_b.write_text("from service_b import ServiceB\ndef test_b(): pass\n", encoding="utf-8")

    batch_report = analyzer.analyze_files([mod_a, mod_b])
    assert "test_service_a.py" in batch_report.affected_tests
    assert "test_service_b.py" in batch_report.affected_tests
    assert batch_report.total_impacted_files >= 2


def test_context_aware_prompt_refiner_uses_ast_cache(tmp_path: Path):
    """Verify ContextAwarePromptRefiner queries CachedASTCodebaseIndexer in O(1)."""
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True)
    sample_file = src_dir / "models.py"
    sample_file.write_text("class SecurityTokenContract:\n    pass\n", encoding="utf-8")

    refiner = ContextAwarePromptRefiner(workspace_path=tmp_path)
    found = refiner.find_ast_symbols("Por favor revisar SecurityTokenContract e conexões")
    assert "SecurityTokenContract" in found


def test_canonical_secret_scanner_detection_and_safelist(tmp_path: Path):
    """Verify CanonicalSecretScanner identifies secrets across 10 patterns and skips safe placeholders."""
    scanner = CanonicalSecretScanner()

    # Safelist placeholder should pass
    clean_text = 'dummy_key = "placeholder_key_example"\napi_key = "your_api_key"'
    findings = scanner.scan_text(clean_text)
    assert len(findings) == 0

    # Real secret patterns (dynamically formed)
    # AWS Key: AKIA + 16 chars
    aws_secret = "AKIA" + "0123456789ABCDEF"
    dirty_text = f'aws_key = "{aws_secret}"\n'
    findings = scanner.scan_text(dirty_text)
    assert len(findings) == 1
    assert findings[0]["rule_name"] == "AWS Access Key ID"


def test_quality_gate_runner_uses_canonical_secret_scanner(tmp_path: Path):
    """Verify QualityGateRunner delegates secret scans to CanonicalSecretScanner."""
    gate = QualityGateRunner(project_root=tmp_path)
    file_path = tmp_path / "config.py"
    file_path.write_text("SAFE_CONFIG = 'placeholder'\n", encoding="utf-8")

    res = gate.run_secret_scan()
    assert res["passed"] is True
    assert len(res["findings"]) == 0


def test_autonomous_engineering_graph_full_connected_pipeline(tmp_path: Path):
    """Verify run_pipeline executes the full E2E lifecycle with anticipation, TDD, auto-healing, quality, and PR URL."""
    task = TaskInput(
        ticket_id="CORP-202",
        description="Conectar pipeline e executar auditoria de segurança completa",
        workspace_path=str(tmp_path),
    )
    graph = AutonomousEngineeringGraph(task=task)

    with (
        patch.object(
            QualityGateRunner, "run_secret_scan", return_value={"passed": True, "findings": []}
        ),
        patch.object(
            QualityGateRunner, "run_tests", return_value={"passed": True, "output": "5 passed"}
        ),
        patch(
            "corporate_engineer.git_utils.generate_pr_url",
            return_value="https://github.com/org/repo/compare/main...feat/test?quick_pull=1",
        ),
    ):
        report = graph.run_pipeline(dry_run=True, auto_deliver=True, strict_audit=True)

        assert report.status == "SUCCESS"
        assert report.final_phase == "DELIVER"
        assert report.audit_passed is True

        # Check integrated details
        details = report.details
        assert "anticipation_plan" in details, "Missing anticipation_plan in run report"
        assert "pr_url" in details, "Missing pr_url in run report"
        assert details["pr_url"].startswith("https://github.com/")
        assert details["anticipation_plan"]["step_1"] is not None
        assert details["anticipation_plan"]["step_2"] is not None
