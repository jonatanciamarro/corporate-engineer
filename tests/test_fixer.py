"""
Tests for AST Auto-Refactor & Self-Healing Fixer (IMP-0012).
Validates ast.NodeTransformer operations:
- Adding '-> None' return annotations to __init__
- Replacing mutable default arguments with None and body preambles
- Removing redundant pass statements
- Dry-run mode vs auto-write
- System-One risk guardrails
- CLI 'corporate-engineer fix' integration
"""

import json
from pathlib import Path

import pytest

from corporate_engineer.cli import main
from corporate_engineer.eval.fixer import ASTSelfHealingFixer


def test_fix_init_return_annotation() -> None:
    code = """class Service:
    def __init__(self, name: str):
        self.name = name

    def execute(self) -> int:
        return 42
"""
    fixer = ASTSelfHealingFixer()
    fixed_code, details = fixer.fix_code(code, file_path="service.py")

    assert "def __init__(self, name: str) -> None:" in fixed_code
    assert len(details) == 1
    assert details[0].rule_name == "init_return_none"
    assert details[0].file_path == "service.py"


def test_init_already_typed_not_modified() -> None:
    code = """class Service:
    def __init__(self, name: str) -> None:
        self.name = name
"""
    fixer = ASTSelfHealingFixer()
    fixed_code, details = fixer.fix_code(code, file_path="service.py")

    assert fixed_code.strip() == code.strip()
    assert len(details) == 0


def test_fix_mutable_default_arguments() -> None:
    code = """def register_items(items=[], config={}):
    \"\"\"Docstring description.\"\"\"
    return len(items)
"""
    fixer = ASTSelfHealingFixer()
    fixed_code, details = fixer.fix_code(code, file_path="registry.py")

    # Arguments converted to None
    assert "def register_items(items=None, config=None):" in fixed_code
    # Preamble injected preserving docstring first
    assert '"""Docstring description."""' in fixed_code
    assert "if items is None:" in fixed_code
    assert "items = []" in fixed_code
    assert "if config is None:" in fixed_code
    assert "config = {}" in fixed_code
    assert len(details) == 2
    assert all(d.rule_name == "mutable_default_argument" for d in details)


def test_fix_redundant_pass() -> None:
    code = """class DataHolder:
    \"\"\"Holds data.\"\"\"
    pass

def compute():
    return 100
    pass
"""
    fixer = ASTSelfHealingFixer()
    fixed_code, details = fixer.fix_code(code, file_path="data.py")

    assert "pass" not in fixed_code
    assert '"""Holds data."""' in fixed_code
    assert "return 100" in fixed_code
    assert len(details) == 2
    assert all(d.rule_name == "redundant_pass" for d in details)


def test_fixer_dry_run_vs_auto(tmp_path: Path) -> None:
    target_file = tmp_path / "sample.py"
    original_code = """class Worker:
    def __init__(self):
        self.ready = True
"""
    target_file.write_text(original_code, encoding="utf-8")

    fixer = ASTSelfHealingFixer()

    # 1. Dry run
    report_dry = fixer.fix_file(target_file, dry_run=True)
    assert report_dry.dry_run is True
    assert report_dry.files_modified == 1
    assert len(report_dry.fixes_applied) == 1
    # File on disk should remain untouched
    assert target_file.read_text(encoding="utf-8") == original_code

    # 2. Auto fix (writes to disk)
    report_auto = fixer.fix_file(target_file, dry_run=False)
    assert report_auto.dry_run is False
    assert report_auto.files_modified == 1
    saved_code = target_file.read_text(encoding="utf-8")
    assert "def __init__(self) -> None:" in saved_code


def test_fixer_workspace_scan(tmp_path: Path) -> None:
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "a.py").write_text("class A:\n    def __init__(self):\n        pass\n", encoding="utf-8")
    (pkg / "b.py").write_text("def fn(lst=[]):\n    return lst\n", encoding="utf-8")
    (pkg / "c.py").write_text("def fn() -> int:\n    return 1\n", encoding="utf-8")

    fixer = ASTSelfHealingFixer()
    report = fixer.fix_workspace(pkg, dry_run=False)

    assert report.total_files_analyzed == 3
    assert report.files_modified == 2
    assert len(report.fixes_applied) >= 2
    assert report.system_one_risk in ["LOW", "MEDIUM", "HIGH"]


def test_cli_fix_dry_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "mod.py"
    target.write_text("class Foo:\n    def __init__(self):\n        pass\n", encoding="utf-8")

    exit_code = main(["fix", "--path", str(target), "--dry-run"])
    assert exit_code == 0
    cap = capsys.readouterr()
    assert "DRY RUN" in cap.out or "FixReport" in cap.out or "mod.py" in cap.out


def test_cli_fix_auto_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "mod2.py"
    target.write_text("def run(args=[]):\n    return len(args)\n", encoding="utf-8")

    exit_code = main(["fix", "--path", str(target), "--auto", "--format", "json"])
    assert exit_code == 0
    cap = capsys.readouterr()
    data = json.loads(cap.out)
    assert data["files_modified"] == 1
    assert data["dry_run"] is False
    assert len(data["fixes_applied"]) == 1
    assert data["fixes_applied"][0]["rule_name"] == "mutable_default_argument"
