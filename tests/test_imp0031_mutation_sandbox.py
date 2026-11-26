"""
Shift-Left TDD Suite for IMP-0031: Mutation Sandbox PYTHONPATH & Cache Isolation.

Tests for:
1. Priority injection of sandbox `src/` in PYTHONPATH over pre-existing/editable installs.
2. Deeply nested package root discovery inside `src/` layouts.
3. Backward compatibility with flat module layouts.
4. Exclusion of cache directories (`.ruff_cache`, `.cache`, etc.) and `.bak` cleanup.
5. PEP 420 namespace package stdlib-shadowing prevention inside `src/`.
6. `shutil.copytree` fallback test path resolution (`test_file` provided and `test_file=None`).
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from corporate_engineer.quality.mutation import ASTMutationEngine


def test_temp_sandbox_injects_src_in_pythonpath_and_kills_mutants(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sandbox must inject `<sandbox>/src` ahead of pre-existing PYTHONPATH entries."""
    project_dir = tmp_path / "src_project"
    pkg_dir = project_dir / "src" / "demo_pkg"
    tests_dir = project_dir / "tests"
    pkg_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)

    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    logic_file = pkg_dir / "logic.py"
    original_code = "def is_valid(x: int) -> bool:\n    return x > 10\n"
    logic_file.write_text(original_code, encoding="utf-8")

    (tests_dir / "test_logic.py").write_text(
        "from demo_pkg.logic import is_valid\n\n"
        "def test_is_valid() -> None:\n"
        "    assert is_valid(11) is True\n"
        "    assert is_valid(10) is False\n"
        "    assert is_valid(5) is False\n",
        encoding="utf-8",
    )

    # Simulate an editable install or existing PYTHONPATH pointing at the unmutated original src/
    monkeypatch.setenv("PYTHONPATH", str(project_dir / "src"))

    engine = ASTMutationEngine(workspace_root=project_dir, use_temp_sandbox=True)
    report = engine.run_mutation_testing(
        target_file=logic_file,
        test_file=None,
        max_mutants=3,
    )

    assert report.total_mutants >= 1
    assert report.killed >= 1
    assert report.survived == 0
    assert report.errors == 0
    assert logic_file.read_text(encoding="utf-8") == original_code
    assert list(tmp_path.rglob("*.bak")) == []


def test_temp_sandbox_discovers_package_root_when_nested_in_src(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`<sandbox>/src` must precede pre-existing PYTHONPATH even for deeply nested modules."""
    project_dir = tmp_path / "nested_src_project"
    sub_pkg_dir = project_dir / "src" / "demo_pkg" / "sub"
    tests_dir = project_dir / "tests"
    sub_pkg_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)

    (project_dir / "src" / "demo_pkg" / "__init__.py").write_text("", encoding="utf-8")
    (sub_pkg_dir / "__init__.py").write_text("", encoding="utf-8")

    calc_file = sub_pkg_dir / "calc.py"
    original_code = "def multiply(a: int, b: int) -> int:\n    return a * b\n"
    calc_file.write_text(original_code, encoding="utf-8")

    (tests_dir / "test_calc.py").write_text(
        "from demo_pkg.sub.calc import multiply\n\n"
        "def test_multiply() -> None:\n"
        "    assert multiply(3, 4) == 12\n"
        "    assert multiply(3, 2) == 6\n",
        encoding="utf-8",
    )

    original_src = str(project_dir / "src")
    other_root = str(tmp_path / "other_root")
    monkeypatch.setenv("PYTHONPATH", f"{original_src}{os.pathsep}{other_root}")

    observed_pythonpaths: list[str] = []
    observed_cwds: list[Path] = []
    real_run = subprocess.run

    def spying_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        env = kwargs.get("env") or {}
        cwd = kwargs.get("cwd")
        if "PYTHONPATH" in env:
            observed_pythonpaths.append(env["PYTHONPATH"])
        if cwd is not None:
            observed_cwds.append(Path(cwd).resolve())
        return real_run(*args, **kwargs)

    engine = ASTMutationEngine(workspace_root=project_dir, use_temp_sandbox=True)
    with patch("corporate_engineer.quality.mutation.subprocess.run", side_effect=spying_run):
        report = engine.run_mutation_testing(
            target_file=calc_file,
            test_file=None,
            max_mutants=3,
        )

    assert report.total_mutants >= 1
    assert report.killed >= 1
    assert report.survived == 0
    assert report.errors == 0
    assert calc_file.read_text(encoding="utf-8") == original_code

    assert len(observed_pythonpaths) >= 1
    assert len(observed_cwds) >= 1
    sandbox_ws = observed_cwds[0]
    parts = observed_pythonpaths[0].split(os.pathsep)

    assert parts[0] == str(sandbox_ws / "src")
    assert parts[1] == str(sandbox_ws)
    assert str(sandbox_ws / "src" / "demo_pkg" / "sub") not in parts
    assert parts.index(str(sandbox_ws / "src")) < parts.index(original_src)
    assert parts.index(str(sandbox_ws)) < parts.index(original_src)
    assert parts.index(original_src) < parts.index(other_root)


def test_flat_layout_mutation_backward_compatibility(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Flat layouts (`tmp_path/calc.py` + `tmp_path/test_calc.py`) must continue working."""
    calc_file = tmp_path / "calc.py"
    original_code = "def subtract(a: int, b: int) -> int:\n    return a - b\n"
    calc_file.write_text(original_code, encoding="utf-8")

    test_file = tmp_path / "test_calc.py"
    test_file.write_text(
        "from calc import subtract\n\ndef test_subtract() -> None:\n    assert subtract(10, 3) == 7\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("PYTHONPATH", str(tmp_path))

    engine = ASTMutationEngine(workspace_root=tmp_path, use_temp_sandbox=True)
    report = engine.run_mutation_testing(
        target_file=calc_file,
        test_file=test_file,
        max_mutants=3,
    )

    assert report.total_mutants >= 1
    assert report.killed >= 1
    assert report.survived == 0
    assert report.errors == 0
    assert calc_file.read_text(encoding="utf-8") == original_code


def test_temp_sandbox_ignores_cache_and_bak_artifacts(tmp_path: Path) -> None:
    """Sandbox copytree must skip cache dirs and leave zero `.bak` artifacts in `tmp_path`."""
    project_dir = tmp_path / "cached_project"
    pkg_dir = project_dir / "src" / "pkg"
    tests_dir = project_dir / "tests"
    pkg_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)

    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    ops_file = pkg_dir / "ops.py"
    ops_file.write_text("def add_one(x: int) -> int:\n    return x + 1\n", encoding="utf-8")
    (tests_dir / "test_ops.py").write_text(
        "from pkg.ops import add_one\n\ndef test_add_one() -> None:\n    assert add_one(1) == 2\n",
        encoding="utf-8",
    )

    for cache_dir_name in (
        ".ruff_cache",
        ".mypy_cache",
        ".pytest_cache",
        ".cache",
        ".venv",
    ):
        cache_dir = project_dir / cache_dir_name
        cache_dir.mkdir(parents=True)
        (cache_dir / "dummy.txt").write_text("cached", encoding="utf-8")

    pycache_dir = pkg_dir / "__pycache__"
    pycache_dir.mkdir()
    (pycache_dir / "ops.cpython-311.pyc").write_bytes(b"\x00\x00")

    bak_source = project_dir / "stale.bak"
    bak_source.write_text("stale backup", encoding="utf-8")

    copied_entries_in_sandbox: list[set[str]] = []
    copied_pkg_entries: list[set[str]] = []
    real_run = subprocess.run

    def inspecting_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        cwd = Path(kwargs["cwd"]).resolve()
        if not copied_entries_in_sandbox:
            copied_entries_in_sandbox.append({p.name for p in cwd.iterdir()})
            sandbox_pkg = cwd / "src" / "pkg"
            if sandbox_pkg.exists():
                copied_pkg_entries.append({p.name for p in sandbox_pkg.iterdir()})
        return real_run(*args, **kwargs)

    engine = ASTMutationEngine(workspace_root=project_dir, use_temp_sandbox=True)
    with patch("corporate_engineer.quality.mutation.subprocess.run", side_effect=inspecting_run):
        report = engine.run_mutation_testing(
            target_file=ops_file,
            test_file=None,
            max_mutants=2,
        )

    assert report.total_mutants >= 1
    assert report.killed >= 1
    assert report.errors == 0

    assert len(copied_entries_in_sandbox) == 1
    root_entries = copied_entries_in_sandbox[0]
    for ignored in (".ruff_cache", ".mypy_cache", ".pytest_cache", ".cache", ".venv", "stale.bak"):
        assert ignored not in root_entries

    assert len(copied_pkg_entries) == 1
    assert "__pycache__" not in copied_pkg_entries[0]

    assert [p for p in tmp_path.rglob("*.bak") if p != bak_source] == []
    bak_source.unlink()
    assert list(tmp_path.rglob("*.bak")) == []


def test_pep420_namespace_package_in_src_does_not_shadow_stdlib(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """PEP 420 namespace package inside `src/` must not expose `effective_target.parent`."""
    project_dir = tmp_path / "ns_src_project"
    ns_sub_dir = project_dir / "src" / "ns_pkg" / "sub"
    tests_dir = project_dir / "tests"
    ns_sub_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)

    # Deliberately omit __init__.py to create a PEP 420 namespace package,
    # and name the module `types.py` to verify stdlib `types` is never shadowed.
    types_file = ns_sub_dir / "types.py"
    original_code = "def check_threshold(value: int) -> bool:\n    return value > 5\n"
    types_file.write_text(original_code, encoding="utf-8")

    (tests_dir / "test_ns_types.py").write_text(
        "import types\n"
        "from ns_pkg.sub.types import check_threshold\n\n"
        "def test_check_threshold() -> None:\n"
        "    assert hasattr(types, 'SimpleNamespace')\n"
        "    assert check_threshold(6) is True\n"
        "    assert check_threshold(5) is False\n",
        encoding="utf-8",
    )

    original_src = str(project_dir / "src")
    monkeypatch.setenv("PYTHONPATH", original_src)

    observed_pythonpaths: list[str] = []
    observed_cwds: list[Path] = []
    observed_stdouts: list[str] = []
    real_run = subprocess.run

    def spying_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        env = kwargs.get("env") or {}
        cwd = kwargs.get("cwd")
        if "PYTHONPATH" in env:
            observed_pythonpaths.append(env["PYTHONPATH"])
        if cwd is not None:
            observed_cwds.append(Path(cwd).resolve())
        proc = real_run(*args, **kwargs)
        observed_stdouts.append(proc.stdout)
        return proc

    engine = ASTMutationEngine(workspace_root=project_dir, use_temp_sandbox=True)
    with patch("corporate_engineer.quality.mutation.subprocess.run", side_effect=spying_run):
        report = engine.run_mutation_testing(
            target_file=types_file,
            test_file=None,
            max_mutants=2,
        )

    assert report.total_mutants >= 1
    assert report.killed >= 1
    assert report.survived == 0
    assert report.errors == 0
    assert types_file.read_text(encoding="utf-8") == original_code

    assert len(observed_pythonpaths) >= 1
    assert len(observed_cwds) >= 1
    sandbox_ws = observed_cwds[0]
    parts = observed_pythonpaths[0].split(os.pathsep)

    assert parts[0] == str(sandbox_ws / "src")
    assert parts[1] == str(sandbox_ws)
    assert str(sandbox_ws / "src" / "ns_pkg" / "sub") not in parts
    assert parts.index(str(sandbox_ws / "src")) < parts.index(original_src)
    assert "1 failed" in observed_stdouts[0]


def test_temp_sandbox_copytree_fallback_copies_test_file(tmp_path: Path) -> None:
    """When `copytree` falls back, `test_file` must be copied to `sandbox_dir / test_path.name`."""
    project_dir = tmp_path / "fallback_project"
    nested_dir = project_dir / "nested"
    tests_dir = project_dir / "tests"
    nested_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)

    calc_file = nested_dir / "calc.py"
    original_code = "def add(a: int, b: int) -> int:\n    return a + b\n"
    calc_file.write_text(original_code, encoding="utf-8")

    test_file = tests_dir / "test_calc.py"
    test_file.write_text(
        "from calc import add\n\ndef test_add() -> None:\n    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )

    observed_cmds: list[list[str]] = []
    observed_test_exists_in_sandbox: list[bool] = []
    observed_stdouts: list[str] = []
    real_run = subprocess.run

    def spying_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        cmd = list(args[0])
        cwd = Path(kwargs["cwd"]).resolve()
        observed_cmds.append(cmd)
        observed_test_exists_in_sandbox.append((cwd / "test_calc.py").exists())
        proc = real_run(*args, **kwargs)
        observed_stdouts.append(proc.stdout)
        return proc

    engine = ASTMutationEngine(workspace_root=project_dir, use_temp_sandbox=True)
    with (
        patch(
            "corporate_engineer.quality.mutation.shutil.copytree",
            side_effect=OSError("simulated copytree failure"),
        ),
        patch("corporate_engineer.quality.mutation.subprocess.run", side_effect=spying_run),
    ):
        report = engine.run_mutation_testing(
            target_file=calc_file,
            test_file=test_file,
            max_mutants=2,
        )

    assert report.total_mutants >= 1
    assert report.killed >= 1
    assert report.survived == 0
    assert report.errors == 0
    assert calc_file.read_text(encoding="utf-8") == original_code

    assert len(observed_cmds) >= 1
    assert observed_test_exists_in_sandbox[0] is True
    assert Path(observed_cmds[0][3]).name == "test_calc.py"
    assert Path(observed_cmds[0][3]).parent != tests_dir.resolve()
    assert "1 failed" in observed_stdouts[0]


def test_temp_sandbox_copytree_fallback_without_test_file(tmp_path: Path) -> None:
    """When `copytree` partially fails with `test_file=None`, fall back to workspace `tests/`."""
    project_dir = tmp_path / "fallback_no_test_file"
    nested_dir = project_dir / "nested"
    tests_dir = project_dir / "tests"
    nested_dir.mkdir(parents=True)
    tests_dir.mkdir(parents=True)

    calc_file = nested_dir / "calc.py"
    original_code = "def add(a: int, b: int) -> int:\n    return a + b\n"
    calc_file.write_text(original_code, encoding="utf-8")

    (tests_dir / "test_calc.py").write_text(
        "from calc import add\n\ndef test_add() -> None:\n    assert add(2, 3) == 5\n",
        encoding="utf-8",
    )

    def partial_failing_copytree(
        _src: Any,
        dst: Any,
        **_kwargs: Any,
    ) -> None:
        # Simulate partial copy creating an empty `tests/` directory before raising shutil.Error
        (Path(dst) / "tests").mkdir(parents=True, exist_ok=True)
        raise shutil.Error("simulated partial copytree failure")

    observed_cmds: list[list[str]] = []
    observed_stdouts: list[str] = []
    real_run = subprocess.run

    def spying_run(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        observed_cmds.append(list(args[0]))
        proc = real_run(*args, **kwargs)
        observed_stdouts.append(proc.stdout)
        return proc

    engine = ASTMutationEngine(workspace_root=project_dir, use_temp_sandbox=True)
    with (
        patch(
            "corporate_engineer.quality.mutation.shutil.copytree",
            side_effect=partial_failing_copytree,
        ),
        patch("corporate_engineer.quality.mutation.subprocess.run", side_effect=spying_run),
    ):
        report = engine.run_mutation_testing(
            target_file=calc_file,
            test_file=None,
            max_mutants=2,
        )

    assert report.total_mutants >= 1
    assert report.killed >= 1
    assert report.survived == 0
    assert report.errors == 0
    assert calc_file.read_text(encoding="utf-8") == original_code

    assert len(observed_cmds) >= 1
    assert Path(observed_cmds[0][3]).resolve() == tests_dir.resolve()
    assert "1 failed" in observed_stdouts[0]
