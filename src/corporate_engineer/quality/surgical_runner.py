"""
Surgical TDD Runner integrated with Git Diff & Blast Radius (IMP-0010).
Computes blast radius of modified code and runs only affected test suites.
"""

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

from corporate_engineer.models import NoulDecision, SurgicalTestReport
from corporate_engineer.rag.impact import BlastRadiusAnalyzer

logger = logging.getLogger(__name__)


class SurgicalTestRunner:
    """Intelligent TDD runner executing only tests affected by Git changes."""

    def __init__(self, root_path: Path | str = ".") -> None:
        self.root = Path(root_path).resolve()
        self.analyzer = BlastRadiusAnalyzer(root_path=self.root)

    def collect_changed_files(
        self,
        base_branch: str = "main",
        include_uncommitted: bool = True,
        timeout: float = 15.0,
    ) -> list[str]:
        """Detect files changed on the current branch or uncommitted in the working tree."""
        changed: set[str] = set()

        # 1. Uncommitted changes (staged, unstaged, untracked)
        if include_uncommitted:
            cmd = ["git", "status", "--porcelain"]
            try:
                proc = subprocess.run(
                    cmd,
                    check=False,
                    capture_output=True,
                    text=True,
                    cwd=str(self.root),
                    timeout=timeout,
                )
                if proc.returncode == 0:
                    for line in proc.stdout.splitlines():
                        if len(line) > 3:
                            rel_file = line[3:].strip()
                            if " -> " in rel_file:
                                rel_file = rel_file.split(" -> ")[1].strip()
                            rel_norm = rel_file.replace("\\", "/").strip('"')
                            changed.add(rel_norm)
                else:
                    logger.warning(
                        "Git command %s returned non-zero exit code %d: %s",
                        cmd,
                        proc.returncode,
                        proc.stderr.strip(),
                    )
            except subprocess.TimeoutExpired as exc:
                logger.warning("Git subprocess error in %s: %s", cmd, exc)
            except (subprocess.SubprocessError, OSError) as exc:
                logger.warning("Git subprocess error in %s: %s", cmd, exc)

        # 2. Committed changes compared to base branch
        if base_branch:
            for diff_args in (
                ["git", "diff", "--name-only", f"{base_branch}...HEAD"],
                ["git", "diff", "--name-only", base_branch],
            ):
                try:
                    proc = subprocess.run(
                        diff_args,
                        check=False,
                        capture_output=True,
                        text=True,
                        cwd=str(self.root),
                        timeout=timeout,
                    )
                    if proc.returncode == 0:
                        for line in proc.stdout.splitlines():
                            clean_line = line.strip().replace("\\", "/").strip('"')
                            if clean_line:
                                changed.add(clean_line)
                        break
                    else:
                        logger.warning(
                            "Git command %s returned non-zero exit code %d: %s",
                            diff_args,
                            proc.returncode,
                            proc.stderr.strip(),
                        )
                except subprocess.TimeoutExpired as exc:
                    logger.warning("Git subprocess error in %s: %s", diff_args, exc)
                except (subprocess.SubprocessError, OSError) as exc:
                    logger.warning("Git subprocess error in %s: %s", diff_args, exc)

        return sorted(changed)

    get_changed_files = collect_changed_files

    def collect_affected_tests(
        self,
        changed_files: list[str],
        max_depth: int = 3,
    ) -> list[str]:
        """Compute all pytest test files directly modified or affected via blast radius."""
        affected_tests: set[str] = set()
        src_files_to_analyze: list[str] = []

        for file_str in changed_files:
            norm_str = file_str.replace("\\", "/")

            # Direct test file modification
            if (
                norm_str.startswith("tests/")
                or "/tests/" in norm_str
                or Path(norm_str).name.startswith("test_")
                or Path(norm_str).name.endswith("_test.py")
            ) and norm_str.endswith(".py"):
                affected_tests.add(norm_str)
                continue

            # Python source file modification: collect for batch analysis
            if norm_str.endswith(".py"):
                full_path = self.root / norm_str
                if full_path.exists():
                    src_files_to_analyze.append(norm_str)

        if src_files_to_analyze:
            if hasattr(self.analyzer, "analyze_files"):
                batch_report = self.analyzer.analyze_files(
                    src_files_to_analyze, max_depth=max_depth
                )
                for test_path in batch_report.affected_tests:
                    affected_tests.add(test_path.replace("\\", "/"))
            else:
                for norm_str in src_files_to_analyze:
                    report = self.analyzer.analyze_file(norm_str, max_depth=max_depth)
                    for test_path in report.affected_tests:
                        affected_tests.add(test_path.replace("\\", "/"))

        return sorted(affected_tests)

    resolve_affected_tests = collect_affected_tests

    def build_command(
        self,
        affected_tests: list[str],
        extra_args: list[str] | None = None,
    ) -> list[str]:
        """Determine appropriate pytest executable and assemble CLI arguments."""
        venv_scripts_pytest = self.root / ".venv" / "Scripts" / "pytest.exe"
        venv_bin_pytest = self.root / ".venv" / "bin" / "pytest"

        if os.name == "nt" and venv_scripts_pytest.exists():
            cmd = [str(venv_scripts_pytest), *affected_tests]
        elif venv_bin_pytest.exists():
            cmd = [str(venv_bin_pytest), *affected_tests]
        else:
            cmd = [sys.executable, "-m", "pytest", *affected_tests]

        if extra_args:
            cmd.extend(extra_args)
        return cmd

    def run(
        self,
        base_branch: str = "main",
        max_depth: int = 3,
        dry_run: bool = False,
        changed_files: list[str] | None = None,
        extra_args: list[str] | None = None,
        fallback_all: bool = False,
    ) -> SurgicalTestReport:
        """Run surgical testing on affected test files and produce a structured report."""
        files = (
            self.get_changed_files(base_branch=base_branch)
            if changed_files is None
            else list(changed_files)
        )
        tests = self.collect_affected_tests(files, max_depth=max_depth)

        if not tests and files and fallback_all:
            tests_dir = self.root / "tests"
            if tests_dir.exists():
                tests = [
                    str(p.relative_to(self.root)).replace("\\", "/")
                    for p in sorted(tests_dir.glob("test_*.py"))
                ]

        if not tests:
            return SurgicalTestReport(
                base_branch=base_branch,
                changed_files=files,
                affected_tests=[],
                command="",
                executed=False,
                exit_code=0,
                passed=True,
            )

        cmd_list = self.build_command(tests, extra_args=extra_args)
        cmd_str = " ".join(cmd_list)

        if dry_run:
            return SurgicalTestReport(
                base_branch=base_branch,
                changed_files=files,
                affected_tests=tests,
                command=cmd_str,
                executed=False,
                exit_code=0,
                passed=True,
            )

        start_time = time.monotonic()
        proc = subprocess.run(
            cmd_list,
            check=False,
            capture_output=True,
            text=True,
            cwd=str(self.root),
        )
        duration_ms = round((time.monotonic() - start_time) * 1000.0, 2)

        return SurgicalTestReport(
            base_branch=base_branch,
            changed_files=files,
            affected_tests=tests,
            command=cmd_str,
            executed=True,
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
            duration_ms=duration_ms,
            passed=(proc.returncode == 0),
        )

    def evaluate_scope_expansion(
        self,
        git_diff: str,
        direct_tests: list[str],
    ) -> NoulDecision:
        """Avalia via Sistema 1 se as mudanças exigem expansão para a suíte completa de testes."""
        from corporate_engineer.system_one.router import SystemOneRouter

        router = SystemOneRouter()
        lowered = git_diff.lower()
        if any(k in lowered for k in ["models.py", "contract", "auth", "security", "base.py"]):
            return NoulDecision(
                decision=True,
                probability=0.94,
                rationale="Mudança toca contratos centrais ou modelos de dados; expansão de suíte recomendada.",
            )
        if any(k in lowered for k in ["readme", "docs/", "test_", "cosmetic"]):
            return NoulDecision(
                decision=False,
                probability=0.06,
                rationale="Mudança puramente documental ou local; suíte cirúrgica direta é suficiente.",
            )
        return router.assess_risk(git_diff)
