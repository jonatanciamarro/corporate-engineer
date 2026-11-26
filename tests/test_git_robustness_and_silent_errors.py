"""
Tests for IMP-0022: Git Robustness, Timeout Handling, and Silent Error Elimination.

Validates:
1. Git timeout handling, logging, and configurability (is_branch_pushed, push_branch_to_remote).
2. Remote slug extraction and remote URL resolution error warnings.
3. SurgicalTestRunner error and timeout logging without silent pass.
4. QualityGateRunner execution with shell=False, custom timeout, and TimeoutExpired diagnostics.
5. QualityGateRunner secret scanning directory exclusion hygiene.
"""

from __future__ import annotations

import inspect
import logging
import subprocess
from pathlib import Path

import pytest

from corporate_engineer.git_utils import (
    extract_github_repo_slug,
    get_remote_url,
    is_branch_pushed,
    push_branch_to_remote,
)
from corporate_engineer.quality.gate import QualityGateRunner, resolve_test_timeout
from corporate_engineer.quality.surgical_runner import SurgicalTestRunner


def test_git_utils_timeout_handling_and_logging(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify is_branch_pushed and push_branch_to_remote handle timeouts and log warnings."""
    caplog.set_level(logging.WARNING)

    # Signature verification for configurable timeout parameter
    sig_pushed = inspect.signature(is_branch_pushed)
    assert "timeout" in sig_pushed.parameters, "is_branch_pushed must accept timeout parameter"
    assert sig_pushed.parameters["timeout"].default == 15.0

    sig_push = inspect.signature(push_branch_to_remote)
    assert "timeout" in sig_push.parameters, "push_branch_to_remote must accept timeout parameter"
    assert sig_push.parameters["timeout"].default == 15.0

    # 1. is_branch_pushed timeout handling
    def mock_timeout_pushed(*args, **kwargs):
        cmd = args[0] if args else kwargs.get("args", [])
        timeout = kwargs.get("timeout", 15.0)
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)

    monkeypatch.setattr(subprocess, "run", mock_timeout_pushed)

    result = is_branch_pushed(repo_path=".", branch="feat/timeout-test", timeout=8.0)
    assert result is False
    assert any(
        rec.levelno >= logging.WARNING
        and ("timeout" in rec.message.lower() or "git" in rec.message.lower())
        for rec in caplog.records
    ), "Expected warning log on git timeout during is_branch_pushed"

    caplog.clear()

    # 2. push_branch_to_remote timeout handling
    push_res = push_branch_to_remote(repo_path=".", branch="feat/timeout-test", timeout=5.0)
    assert push_res is False
    assert any(
        rec.levelno >= logging.WARNING
        and ("timeout" in rec.message.lower() or "git" in rec.message.lower())
        for rec in caplog.records
    ), "Expected warning log on git timeout during push_branch_to_remote"

    # 3. Environment variable fallback CORP_GIT_TIMEOUT
    recorded_timeouts: list[float | None] = []

    def mock_capture_timeouts(*args, **kwargs):
        recorded_timeouts.append(kwargs.get("timeout"))
        return subprocess.CompletedProcess(
            args=args[0] if args else kwargs.get("args"),
            returncode=0,
            stdout="origin\n",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", mock_capture_timeouts)
    monkeypatch.setenv("CORP_GIT_TIMEOUT", "22.5")

    # Call without explicit timeout argument; should resolve to CORP_GIT_TIMEOUT value
    is_branch_pushed(repo_path=".", branch="main")
    assert any(t == 22.5 for t in recorded_timeouts), (
        "Expected timeout from CORP_GIT_TIMEOUT env var"
    )


def test_git_utils_remote_slug_resolution(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify extract_github_repo_slug and get_remote_url log warnings when resolution fails."""
    caplog.set_level(logging.WARNING)

    # 1. extract_github_repo_slug fallback with warning
    invalid_url = "https://custom-git-server.internal/org/project.git"
    slug = extract_github_repo_slug(invalid_url)
    assert slug == "jonatanciamarro/corporate-engineer"
    assert any(
        rec.levelno >= logging.WARNING
        and ("slug" in rec.message.lower() or "remote" in rec.message.lower())
        for rec in caplog.records
    ), "Expected warning log when extract_github_repo_slug fails to match pattern"

    caplog.clear()

    # 2. get_remote_url failure logging
    def mock_run_error(*args, **kwargs):
        raise subprocess.SubprocessError("Failed to communicate with git executable")

    monkeypatch.setattr(subprocess, "run", mock_run_error)

    url = get_remote_url(repo_path=".", remote_name="origin")
    assert url == "https://github.com/jonatanciamarro/corporate-engineer.git"
    assert any(
        rec.levelno >= logging.WARNING
        and ("remote" in rec.message.lower() or "git" in rec.message.lower())
        for rec in caplog.records
    ), "Expected warning log when get_remote_url subprocess fails"


def test_surgical_runner_git_failure_logging(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify SurgicalTestRunner logs explicit warnings on git failure instead of silent pass."""
    caplog.set_level(logging.WARNING)
    runner = SurgicalTestRunner(root_path=tmp_path)

    # Target collecting method: collect_changed_files or get_changed_files
    collect_func = getattr(runner, "collect_changed_files", runner.get_changed_files)

    # 1. SubprocessError in git command
    def mock_subprocess_error(*args, **kwargs):
        raise subprocess.SubprocessError("Fatal error during git execution")

    monkeypatch.setattr(subprocess, "run", mock_subprocess_error)

    changed = collect_func(base_branch="main", include_uncommitted=True)
    assert changed == []
    assert any(
        rec.levelno >= logging.WARNING
        and ("git" in rec.message.lower() or "subprocess" in rec.message.lower())
        for rec in caplog.records
    ), "Expected warning log when git command fails in collect_changed_files"

    caplog.clear()

    # 2. TimeoutExpired in git status / diff
    def mock_timeout_expired(*args, **kwargs):
        cmd = args[0] if args else kwargs.get("args", [])
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=15.0)

    monkeypatch.setattr(subprocess, "run", mock_timeout_expired)

    changed_timeout = collect_func(base_branch="main", include_uncommitted=True)
    assert changed_timeout == []
    assert any(
        rec.levelno >= logging.WARNING
        and ("timeout" in rec.message.lower() or "git" in rec.message.lower())
        for rec in caplog.records
    ), "Expected warning log on git TimeoutExpired in collect_changed_files"


def test_quality_gate_shell_false_and_custom_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify QualityGateRunner.run_tests uses shell=False, custom timeout, and handles TimeoutExpired."""
    runner = QualityGateRunner(project_root=tmp_path)

    # Signature verification for custom timeout
    sig = inspect.signature(runner.run_tests)
    assert "timeout" in sig.parameters, "run_tests must accept timeout parameter"
    assert sig.parameters["timeout"].default == 120.0

    call_records: list[dict] = []

    def mock_run_success(*args, **kwargs):
        call_records.append({"args": args, "kwargs": kwargs})
        return subprocess.CompletedProcess(
            args=args[0] if args else kwargs.get("args"),
            returncode=0,
            stdout="pytest ran successfully",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", mock_run_success)

    # 1. Test shell=False and argument list representation
    res = runner.run_tests(command="pytest -v --color=no", timeout=60.0)
    assert res["passed"] is True
    assert len(call_records) == 1
    assert call_records[0]["kwargs"].get("shell") is False, (
        "QualityGateRunner must execute with shell=False"
    )
    assert call_records[0]["kwargs"].get("timeout") == 60.0

    cmd_passed = (
        call_records[0]["args"][0]
        if call_records[0]["args"]
        else call_records[0]["kwargs"].get("args")
    )
    assert isinstance(cmd_passed, list), (
        f"Expected command arguments as list, got {type(cmd_passed)}"
    )

    # 2. Test TimeoutExpired handling returning exit_code=-2 and informative stderr
    def mock_run_timeout(*args, **kwargs):
        timeout = kwargs.get("timeout", 45.0)
        cmd = args[0] if args else kwargs.get("args")
        raise subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)

    monkeypatch.setattr(subprocess, "run", mock_run_timeout)

    timeout_res = runner.run_tests(command="pytest", timeout=45.0)
    assert timeout_res["passed"] is False
    assert timeout_res["exit_code"] == -2, (
        f"Expected exit_code=-2 on TimeoutExpired, got {timeout_res['exit_code']}"
    )
    assert (
        "timed out after 45" in timeout_res["stderr"].lower()
        or "timed out" in timeout_res["stderr"].lower()
    )


def test_surgical_runner_build_command_os_portability(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify build_command only targets .venv/Scripts/pytest.exe when on Windows (os.name == 'nt')."""
    runner = SurgicalTestRunner(root_path=tmp_path)
    venv_scripts = tmp_path / ".venv" / "Scripts"
    venv_scripts.mkdir(parents=True)
    fake_exe = venv_scripts / "pytest.exe"
    fake_exe.write_text("#!fake", encoding="utf-8")

    # Simulate POSIX / Linux environment in surgical_runner module
    monkeypatch.setattr("corporate_engineer.quality.surgical_runner.os.name", "posix")
    cmd = runner.build_command(["tests/test_sample.py"])

    # On POSIX, it should not pick .venv/Scripts/pytest.exe even if the file exists
    assert not any("Scripts" in str(arg) and "pytest.exe" in str(arg) for arg in cmd)


def test_quality_gate_secret_scan_ignores_hidden_and_venv_dirs(tmp_path: Path) -> None:
    """Verify QualityGateRunner secret scanner ignores .git, .venv, and __pycache__ directories."""
    # Create a synthetic secret in .git folder
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "secret.py").write_text("ghp_" + "A" * 36, encoding="utf-8")

    # Create a synthetic secret in .venv folder
    venv_dir = tmp_path / ".venv"
    venv_dir.mkdir()
    (venv_dir / "secret.py").write_text("ghp_" + "B" * 36, encoding="utf-8")

    runner = QualityGateRunner(project_root=tmp_path)
    res = runner.run_secret_scan()
    assert res["passed"] is True
    assert len(res["findings"]) == 0


def test_quality_gate_runner_default_and_env_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Verify QualityGateRunner.run_tests preserves 120s default and honors CORP_TEST_TIMEOUT."""
    runner = QualityGateRunner(project_root=tmp_path)
    recorded_timeouts: list[float | None] = []

    def mock_run(*args, **kwargs):
        recorded_timeouts.append(kwargs.get("timeout"))
        return subprocess.CompletedProcess(
            args=args[0] if args else kwargs.get("args"),
            returncode=0,
            stdout="ok",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", mock_run)
    monkeypatch.delenv("CORP_TEST_TIMEOUT", raising=False)

    runner.run_tests(command="pytest -q")
    assert recorded_timeouts[-1] == 120.0
    assert resolve_test_timeout(default_timeout=300.0) == 300.0

    monkeypatch.setenv("CORP_TEST_TIMEOUT", "450.0")
    runner.run_tests(command="pytest -q")
    assert recorded_timeouts[-1] == 450.0
    assert resolve_test_timeout(default_timeout=300.0) == 450.0

    monkeypatch.setenv("CORP_TEST_TIMEOUT", "not-a-number")
    runner.run_tests(command="pytest -q")
    assert recorded_timeouts[-1] == 120.0
