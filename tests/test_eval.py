"""
Tests for Evaluation-Driven Development (EDD) & Semantic Scorecard Engine (IMP-0007).
Validates 5 corporate quality axes, DTO models, scoring calculation, and CLI eval command.
"""

from pathlib import Path

import pytest

from corporate_engineer.cli import main
from corporate_engineer.eval.scorecard import SemanticCodeEvaluator
from corporate_engineer.models import EvaluationAxisScore, SemanticEvaluationReport


def test_models_evaluation_axis_and_report() -> None:
    axis1 = EvaluationAxisScore(
        axis_name="Immutability & Pure Functions",
        score=95.0,
        weight=0.20,
        violations=[],
        passed=True,
    )
    axis2 = EvaluationAxisScore(
        axis_name="Strong Typing & Pydantic Contracts",
        score=85.0,
        weight=0.25,
        violations=["Function returns bare dict"],
        passed=True,
    )
    axis3 = EvaluationAxisScore(
        axis_name="Cyclomatic Complexity",
        score=90.0,
        weight=0.20,
        violations=[],
        passed=True,
    )
    axis4 = EvaluationAxisScore(
        axis_name="Modularity & Hygiene",
        score=92.0,
        weight=0.15,
        violations=[],
        passed=True,
    )
    axis5 = EvaluationAxisScore(
        axis_name="Type Hints Coverage",
        score=100.0,
        weight=0.20,
        violations=[],
        passed=True,
    )

    axes = [axis1, axis2, axis3, axis4, axis5]
    expected_composite = (
        95.0 * 0.20 + 85.0 * 0.25 + 90.0 * 0.20 + 92.0 * 0.15 + 100.0 * 0.20
    )  # 19.0 + 21.25 + 18.0 + 13.8 + 20.0 = 92.05

    report = SemanticEvaluationReport(
        target_path="src/corporate_engineer",
        axes=axes,
        total_files_evaluated=10,
        total_functions_evaluated=45,
        min_passing_score=80.0,
    )

    assert abs(report.composite_score - expected_composite) < 0.1
    assert report.letter_grade == "A"
    assert report.passed_gate is True
    assert report.total_violations == 1


def test_evaluator_axis_scores_clean_code() -> None:
    clean_code = """
from pydantic import BaseModel

class UserDTO(BaseModel):
    name: str
    age: int

def get_user_greeting(user: UserDTO) -> str:
    if user.age >= 18:
        return f"Welcome adult {user.name}"
    return f"Welcome young {user.name}"
"""
    evaluator = SemanticCodeEvaluator()
    report = evaluator.evaluate_source(clean_code, file_path="clean_example.py")

    assert report.composite_score >= 85.0
    assert report.passed_gate is True
    assert report.letter_grade in ("A", "B")


def test_evaluator_axis_penalties_on_bad_smells() -> None:
    bad_code = """
global_counter = 0

def bad_function(a, b, c, d, e, f):
    global global_counter
    global_counter += 1
    # Deep nesting and complexity
    if a:
        if b:
            if c:
                if d:
                    for i in range(10):
                        while e:
                            return {"untyped": "dict"}
    return None
"""
    evaluator = SemanticCodeEvaluator()
    report = evaluator.evaluate_source(bad_code, file_path="bad_example.py")

    assert report.composite_score < 75.0
    assert len(report.axes) == 5

    # Check violations recorded
    all_violations = [v for ax in report.axes for v in ax.violations]
    assert any("global" in v.lower() for v in all_violations)
    assert any("parameter" in v.lower() or "argument" in v.lower() for v in all_violations)
    assert any("type hint" in v.lower() or "untyped" in v.lower() for v in all_violations)


def test_evaluator_evaluate_directory(tmp_path: Path) -> None:
    p1 = tmp_path / "module_a.py"
    p1.write_text(
        """
def add(x: int, y: int) -> int:
    return x + y
""",
        encoding="utf-8",
    )

    evaluator = SemanticCodeEvaluator()
    report = evaluator.evaluate_directory(tmp_path)

    assert report.total_files_evaluated == 1
    assert report.total_functions_evaluated == 1
    assert report.composite_score >= 80.0


def test_cli_eval_command(capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["eval", "src/corporate_engineer", "--format", "json", "--min-score", "70"])
    assert code == 0
    captured = capsys.readouterr()
    assert "composite_score" in captured.out
    assert "letter_grade" in captured.out

    text_code = main(["eval", "src/corporate_engineer", "--format", "text", "--min-score", "70"])
    assert text_code == 0
    captured_text = capsys.readouterr()
    assert "Corporate Scorecard" in captured_text.out
    assert "Grade:" in captured_text.out
