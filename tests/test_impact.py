"""
Tests for Code GraphRAG & Blast Radius Impact Analysis (IMP-0008).
Validates reverse caller resolution, transitive dependencies, affected test resolution,
and CLI blast-radius integration.
"""

from pathlib import Path

import pytest

from corporate_engineer.cli import main
from corporate_engineer.models import BlastRadiusReport, ImpactNode
from corporate_engineer.rag.impact import BlastRadiusAnalyzer


def test_models_impact_node_and_report() -> None:
    node1 = ImpactNode(
        symbol="calculate_tax",
        file_path="src/service.py",
        depth=1,
        impact_type="DIRECT",
        relationship="CALLS",
    )
    node2 = ImpactNode(
        symbol="checkout_handler",
        file_path="src/controller.py",
        depth=2,
        impact_type="TRANSITIVE",
        relationship="CALLS",
    )

    report = BlastRadiusReport(
        target="calculate_tax",
        target_type="SYMBOL",
        total_impacted_files=2,
        total_impacted_symbols=2,
        impacted_nodes=[node1, node2],
        affected_tests=["tests/test_service.py"],
        recommended_test_command="pytest tests/test_service.py",
    )

    assert report.target == "calculate_tax"
    assert report.total_impacted_files == 2
    assert len(report.impacted_nodes) == 2
    assert "pytest tests/test_service.py" in report.recommended_test_command


def test_blast_radius_direct_and_transitive_impact(tmp_path: Path) -> None:
    # Setup synthetic codebase
    service_file = tmp_path / "service.py"
    service_file.write_text(
        """
def compute_hash(data: str) -> str:
    return "hash_" + data
""",
        encoding="utf-8",
    )

    controller_file = tmp_path / "controller.py"
    controller_file.write_text(
        """
from service import compute_hash

def handle_request(req: str) -> str:
    return compute_hash(req)
""",
        encoding="utf-8",
    )

    app_file = tmp_path / "app.py"
    app_file.write_text(
        """
from controller import handle_request

def main_entry() -> None:
    handle_request("ping")
""",
        encoding="utf-8",
    )

    test_file = tmp_path / "test_service.py"
    test_file.write_text(
        """
from service import compute_hash

def test_compute_hash() -> None:
    assert compute_hash("abc") == "hash_abc"
""",
        encoding="utf-8",
    )

    analyzer = BlastRadiusAnalyzer(workspace_root=tmp_path)
    report = analyzer.analyze_impact(target_symbol="compute_hash", max_depth=3)

    assert report.target == "compute_hash"
    assert report.total_impacted_symbols >= 1

    # Check direct caller
    direct_symbols = [n.symbol for n in report.impacted_nodes if n.depth == 1]
    assert "handle_request" in direct_symbols or any(
        "controller.py" in n.file_path for n in report.impacted_nodes
    )

    # Check transitive caller
    transitive_symbols = [n.symbol for n in report.impacted_nodes if n.depth >= 2]
    assert "main_entry" in transitive_symbols or any(
        "app.py" in n.file_path for n in report.impacted_nodes
    )

    # Check affected test resolution
    assert any("test_service.py" in t for t in report.affected_tests)
    assert "pytest" in report.recommended_test_command


def test_blast_radius_file_target(tmp_path: Path) -> None:
    mod_a = tmp_path / "module_a.py"
    mod_a.write_text("def helper() -> int:\n    return 42\n", encoding="utf-8")

    mod_b = tmp_path / "module_b.py"
    mod_b.write_text(
        "from module_a import helper\ndef run():\n    return helper()\n", encoding="utf-8"
    )

    test_mod = tmp_path / "test_b.py"
    test_mod.write_text("from module_b import run\ndef test_run():\n    assert run() == 42\n")

    analyzer = BlastRadiusAnalyzer(workspace_root=tmp_path)
    report = analyzer.analyze_impact(target_file="module_a.py", max_depth=2)

    assert report.target_type == "FILE"
    assert any("module_b.py" in n.file_path for n in report.impacted_nodes)
    assert any("test_b.py" in t for t in report.affected_tests)


def test_cli_blast_radius_command(capsys: pytest.CaptureFixture[str]) -> None:
    # Test on real repository
    code = main(["blast-radius", "generate_pr_url", "--format", "json"])
    assert code == 0
    captured = capsys.readouterr()
    assert "generate_pr_url" in captured.out
    assert "recommended_test_command" in captured.out

    text_code = main(["blast-radius", "generate_pr_url", "--format", "text"])
    assert text_code == 0
    captured_text = capsys.readouterr()
    assert "Blast Radius" in captured_text.out
