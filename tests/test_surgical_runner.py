"""
Tests for Surgical TDD Runner integrated with Git Diff & Blast Radius (IMP-0010).
Validates change detection, affected test resolution, command construction, dry-run,
and CLI execution.
"""

import subprocess
from pathlib import Path

import pytest

from corporate_engineer.cli import main
from corporate_engineer.models import SurgicalTestReport
from corporate_engineer.quality.surgical_runner import SurgicalTestRunner


def test_models_surgical_test_report() -> None:
    report = SurgicalTestReport(
        base_branch="main",
        changed_files=["src/corporate_engineer/models.py"],
        affected_tests=["tests/test_models.py"],
        command="pytest tests/test_models.py",
        executed=True,
        exit_code=0,
        stdout="1 passed",
        duration_ms=150.0,
        passed=True,
    )
    assert report.base_branch == "main"
    assert report.changed_files == ["src/corporate_engineer/models.py"]
    assert report.affected_tests == ["tests/test_models.py"]
    assert report.passed is True
    assert report.executed is True


def test_surgical_runner_resolve_affected_tests(tmp_path: Path) -> None:
    src_dir = tmp_path / "src" / "sample"
    src_dir.mkdir(parents=True)
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(parents=True)

    # File A
    file_a = src_dir / "service.py"
    file_a.write_text("def process_data(): return 42\n", encoding="utf-8")

    # File B
    file_b = src_dir / "helper.py"
    file_b.write_text("def assist(): return 'ok'\n", encoding="utf-8")

    # Test file importing service
    test_file = tests_dir / "test_service.py"
    test_file.write_text(
        "from sample.service import process_data\ndef test_process(): assert process_data() == 42\n",
        encoding="utf-8",
    )

    runner = SurgicalTestRunner(root_path=tmp_path)

    # 1. Changed source file with mapped test
    affected = runner.resolve_affected_tests(["src/sample/service.py"])
    assert "tests/test_service.py" in affected

    # 2. Changed source file without test
    affected_helper = runner.resolve_affected_tests(["src/sample/helper.py"])
    assert "tests/test_service.py" not in affected_helper

    # 3. Direct change in test file
    affected_direct = runner.resolve_affected_tests(["tests/test_service.py"])
    assert "tests/test_service.py" in affected_direct


def test_surgical_runner_git_diff_detection(tmp_path: Path) -> None:
    # Initialize a temporary git repository
    subprocess.run(["git", "init"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@corp.internal"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )

    file_1 = tmp_path / "file1.py"
    file_1.write_text("a = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "file1.py"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"], cwd=str(tmp_path), check=True, capture_output=True
    )

    # Now create an untracked/modified file
    file_2 = tmp_path / "file2.py"
    file_2.write_text("b = 2\n", encoding="utf-8")

    runner = SurgicalTestRunner(root_path=tmp_path)
    changed = runner.get_changed_files(base_branch="HEAD")
    assert "file2.py" in changed


def test_surgical_runner_dry_run_and_execution(tmp_path: Path) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(parents=True)
    test_pass = tests_dir / "test_simple.py"
    test_pass.write_text("def test_ok(): assert True\n", encoding="utf-8")

    runner = SurgicalTestRunner(root_path=tmp_path)

    # Dry-run
    dry_report = runner.run(
        changed_files=["tests/test_simple.py"],
        dry_run=True,
    )
    assert dry_report.executed is False
    assert "tests/test_simple.py" in dry_report.affected_tests
    assert "pytest" in dry_report.command

    # Real execution
    exec_report = runner.run(
        changed_files=["tests/test_simple.py"],
        dry_run=False,
    )
    assert exec_report.executed is True
    assert exec_report.exit_code == 0
    assert exec_report.passed is True
    assert "1 passed" in exec_report.stdout


def test_cli_test_surgical_dry_run(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["test-surgical", "--dry-run", "--format", "json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "changed_files" in captured.out
    assert "affected_tests" in captured.out
