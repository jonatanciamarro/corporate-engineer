"""
Quality Gate Runner executing Secret Audits, Testing verification and static checks.
"""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

from corporate_engineer.quality.secret_scanner import (
    SECRET_PATTERNS,
    CanonicalSecretScanner,
)

__all__ = ["SECRET_PATTERNS", "QualityGateRunner", "resolve_test_timeout"]

logger = logging.getLogger(__name__)
DEFAULT_TEST_TIMEOUT_SECONDS = 120.0


def resolve_test_timeout(
    explicit_timeout: float | None = None,
    default_timeout: float = DEFAULT_TEST_TIMEOUT_SECONDS,
) -> float:
    """Resolve test command timeout from explicit arg, CORP_TEST_TIMEOUT env, or default."""
    if explicit_timeout is not None:
        return explicit_timeout
    raw_env = os.environ.get("CORP_TEST_TIMEOUT", "").strip()
    if raw_env:
        try:
            parsed = float(raw_env)
            if parsed > 0:
                return parsed
            logger.warning("CORP_TEST_TIMEOUT must be positive (got %r); using default.", raw_env)
        except ValueError:
            logger.warning("Invalid CORP_TEST_TIMEOUT=%r; falling back to default.", raw_env)
    return default_timeout


class QualityGateRunner:
    """Pre-flight quality gate runner orchestrating secret scans, tests, and static checks."""

    def __init__(
        self,
        project_root: str | Path,
        secret_scanner: CanonicalSecretScanner | None = None,
    ) -> None:
        self.project_root = Path(project_root).resolve()
        self.secret_scanner = secret_scanner or CanonicalSecretScanner()

    def run_secret_scan(self) -> dict[str, Any]:
        """Run canonical credential detection across project root."""
        findings = self.secret_scanner.scan_directory(self.project_root)
        return {"passed": len(findings) == 0, "findings": findings}

    def run_wiring_audit(self) -> dict[str, Any]:
        """Execute capability auto-wiring audit to ensure no orphaned or unwired modules."""
        from corporate_engineer.quality.wiring_auditor import CapabilityWiringAuditor

        auditor = CapabilityWiringAuditor(workspace_root=self.project_root)
        report = auditor.audit()
        return {
            "passed": report.passed,
            "report": report.model_dump(),
            "unwired_modules": report.unwired_modules,
            "missing_test_modules": report.missing_test_modules,
        }

    def run_tests(
        self,
        command: str | list[str] = "pytest",
        timeout: float = DEFAULT_TEST_TIMEOUT_SECONDS,
    ) -> dict[str, Any]:
        """Run automated test suite with timeout and security boundaries."""
        explicit = None if timeout == DEFAULT_TEST_TIMEOUT_SECONDS else timeout
        effective_timeout = resolve_test_timeout(explicit)
        if isinstance(command, str):
            cmd_list = shlex.split(command, posix=(os.name != "nt"))
        else:
            cmd_list = list(command)

        if cmd_list and cmd_list[0] == "pytest":
            venv_pytest = self.project_root / ".venv" / "Scripts" / "pytest.exe"
            venv_bin_pytest = self.project_root / ".venv" / "bin" / "pytest"
            if os.name == "nt" and venv_pytest.exists():
                cmd_list = [str(venv_pytest), *cmd_list[1:]]
            elif venv_bin_pytest.exists():
                cmd_list = [str(venv_bin_pytest), *cmd_list[1:]]
            else:
                cmd_list = [sys.executable, "-m", "pytest", *cmd_list[1:]]

        cmd_display = " ".join(cmd_list)
        try:
            res = subprocess.run(
                cmd_list,
                check=False,
                shell=False,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=effective_timeout,
            )
            return {
                "command": cmd_display,
                "passed": res.returncode == 0,
                "exit_code": res.returncode,
                "stdout": res.stdout,
                "stderr": res.stderr,
            }
        except subprocess.TimeoutExpired:
            return {
                "command": cmd_display,
                "passed": False,
                "exit_code": -2,
                "stdout": "",
                "stderr": f"Command timed out after {effective_timeout}s",
            }
        except (subprocess.SubprocessError, OSError) as e:
            return {
                "command": cmd_display,
                "passed": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
            }
