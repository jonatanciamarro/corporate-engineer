"""
Quality Gate Runner executing Secret Audits, Testing verification and static checks.
"""

import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

SECRET_PATTERNS = [
    ("Private Key", re.compile("-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
    (
        "AWS Access Key ID",
        re.compile("(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}"),
    ),
    ("GitHub Personal Access Token", re.compile("gh[pousr]_[A-Za-z0-9_]{36,}")),
    ("OpenAI API Key", re.compile("sk-(?:proj-|live-)?[a-zA-Z0-9]{32,}")),
    ("Anthropic API Key", re.compile("sk-ant-[a-zA-Z0-9]{32,}")),
    ("Google Gemini Key", re.compile("AIzaSy[A-Za-z0-9_\\-]{33}")),
]


class QualityGateRunner:
    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root).resolve()

    def run_secret_scan(self) -> dict[str, Any]:
        findings = []
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".")
                and d
                not in {".git", ".venv", "venv", "__pycache__", "node_modules", "build", "dist"}
            ]
            rel_root = Path(root).relative_to(self.project_root)
            if any(
                part.startswith(".") or part in {".git", ".venv", "venv", "__pycache__"}
                for part in rel_root.parts
            ):
                continue

            for f in files:
                if f.endswith((".py", ".json", ".yaml", ".yml", ".env", ".ts", ".js")):
                    p = Path(root) / f
                    try:
                        text = p.read_text(encoding="utf-8", errors="ignore")
                    except OSError:
                        continue
                    for line_idx, line in enumerate(text.splitlines(), start=1):
                        for name, pat in SECRET_PATTERNS:
                            if pat.search(line):
                                findings.append(
                                    {
                                        "file": str(p.relative_to(self.project_root)),
                                        "line": line_idx,
                                        "type": name,
                                    }
                                )
        return {"passed": len(findings) == 0, "findings": findings}

    def run_tests(
        self,
        command: str | list[str] = "pytest",
        timeout: float = 120.0,
    ) -> dict[str, Any]:
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
