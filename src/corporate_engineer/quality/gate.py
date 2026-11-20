"""
Quality Gate Runner executing Secret Audits, Testing verification and static checks.
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SECRET_PATTERNS = [
    ("Private Key", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----")),
    (
        "AWS Access Key ID",
        re.compile(r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}"),
    ),
    ("GitHub Personal Access Token", re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,}")),
    ("OpenAI API Key", re.compile(r"sk-(?:proj-|live-)?[a-zA-Z0-9]{32,}")),
    ("Anthropic API Key", re.compile(r"sk-ant-[a-zA-Z0-9]{32,}")),
    ("Google Gemini Key", re.compile(r"AIzaSy[A-Za-z0-9_\-]{33}")),
]


class QualityGateRunner:
    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()

    def run_secret_scan(self) -> dict[str, Any]:
        findings = []
        for root, dirs, files in os.walk(self.project_root):
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".") and d not in {"venv", ".venv", "__pycache__"}
            ]
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
        return {
            "passed": len(findings) == 0,
            "findings": findings,
        }

    def run_tests(self, command: str = "pytest") -> dict[str, Any]:
        actual_cmd = command
        if command == "pytest":
            venv_pytest = self.project_root / ".venv" / "Scripts" / "pytest.exe"
            if venv_pytest.exists():
                actual_cmd = str(venv_pytest)
            else:
                actual_cmd = f'"{sys.executable}" -m pytest'

        try:
            res = subprocess.run(
                actual_cmd,
                check=False,
                shell=True,
                cwd=str(self.project_root),
                capture_output=True,
                text=True,
                timeout=120,
            )
            return {
                "command": actual_cmd,
                "passed": res.returncode == 0,
                "exit_code": res.returncode,
                "stdout": res.stdout,
                "stderr": res.stderr,
            }
        except (subprocess.SubprocessError, OSError) as e:
            return {
                "command": command,
                "passed": False,
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
            }
