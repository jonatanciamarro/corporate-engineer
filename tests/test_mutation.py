"""
Tests for Native AST Mutation Testing Engine (IMP-0006).
"""

from pathlib import Path

from corporate_engineer.cli import main
from corporate_engineer.models import Mutant, MutationReport
from corporate_engineer.quality.mutation import (
    ASTMutationEngine,
    MutationPoint,
    apply_mutation,
    scan_mutation_points,
)


def test_scan_mutation_points():
    code = """
def is_adult(age: int) -> bool:
    if age >= 18:
        return True
    return False

def calculate(a: int, b: int) -> int:
    return a + b
"""
    points = scan_mutation_points(code)
    assert len(points) >= 3

    # Check for relational mutation point (>=)
    rel_points = [p for p in points if p.original_op == ">="]
    assert len(rel_points) > 0
    assert rel_points[0].mutated_op in (">", "<", "<=", "==")

    # Check for boolean mutation point (True/False)
    bool_points = [p for p in points if p.original_op in ("True", "False")]
    assert len(bool_points) >= 2

    # Check for arithmetic mutation point (+)
    arith_points = [p for p in points if p.original_op == "+"]
    assert len(arith_points) > 0


def test_apply_mutation():
    code = "def check(x: int) -> bool:\n    return x > 10\n"
    point = MutationPoint(
        node_id="0",
        line_number=2,
        original_op=">",
        mutated_op="<=",
        op_type="relational",
    )
    mutated_code = apply_mutation(code, point)
    assert "<=" in mutated_code
    assert "x <= 10" in mutated_code


def test_mutation_report_model():
    mutants = [
        Mutant(
            id="MUT-1",
            file_path="foo.py",
            line_number=10,
            original_op=">",
            mutated_op="<=",
            status="KILLED",
        ),
        Mutant(
            id="MUT-2",
            file_path="foo.py",
            line_number=12,
            original_op="True",
            mutated_op="False",
            status="SURVIVED",
        ),
    ]
    report = MutationReport(
        total_mutants=2,
        killed=1,
        survived=1,
        errors=0,
        mutation_score=50.0,
        mutants=mutants,
    )
    assert report.total_mutants == 2
    assert report.killed == 1
    assert report.survived == 1
    assert report.mutation_score == 50.0


def test_mutation_runner_kills_mutants(tmp_path: Path):
    src_file = tmp_path / "calc.py"
    src_file.write_text(
        "def add(a: int, b: int) -> int:\n    return a + b\n",
        encoding="utf-8",
    )
    test_file = tmp_path / "test_calc.py"
    test_file.write_text(
        "from calc import add\n\ndef test_add():\n    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )

    engine = ASTMutationEngine(workspace_root=tmp_path)
    report = engine.run_mutation_testing(
        target_file=src_file,
        test_file=test_file,
        max_mutants=5,
    )

    assert report.total_mutants >= 1
    assert report.killed >= 1
    assert report.mutation_score > 0.0
    # Original file must remain intact
    assert "return a + b" in src_file.read_text(encoding="utf-8")


def test_cli_audit_mutation(capsys, tmp_path: Path):
    src_file = tmp_path / "logic.py"
    src_file.write_text(
        "def check(x: int) -> bool:\n    return x > 0\n",
        encoding="utf-8",
    )
    test_file = tmp_path / "test_logic.py"
    test_file.write_text(
        "from logic import check\n\ndef test_check():\n    assert check(5) is True\n",
        encoding="utf-8",
    )

    ret = main(
        [
            "audit",
            "--path",
            str(tmp_path),
            "--mutation",
            "--target-file",
            str(src_file),
            "--max-mutants",
            "3",
        ]
    )
    captured = capsys.readouterr()
    assert ret in (0, 1)
    assert "Mutation" in captured.out or "mutation" in captured.out.lower()
