"""
Quality Gate Runner executing Secret Audits, Testing verification and static checks.
"""

from __future__ import annotations

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

__all__ = ["SECRET_PATTERNS", "QualityGateRunner"]


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

    def run_tests(
        self,
        command: str | list[str] = "pytest",
        timeout: float = 120.0,
    ) -> dict[str, Any]:
        """Run automated test suite with timeout and security boundaries."""
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
                timeout=timeout,
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
                "stderr": f"Command timed out after {timeout}s",
            }
        except (subprocess.SubprocessError, OSError) as e:
            return {
                "command": cmd_display,
                "passed": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
            }
