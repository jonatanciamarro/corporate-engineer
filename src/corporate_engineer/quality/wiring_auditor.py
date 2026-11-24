"""
Capability Wiring Auditor (IMP-0029 / ADR-028).
Enforces continuous auto-wiring and maximum capability power across the entire repository.
Verifies that no orphaned or disconnected modules exist without exports, tests, and integration.
"""

from __future__ import annotations

import ast
from pathlib import Path

from corporate_engineer.models import WiringAuditReport


class CapabilityWiringAuditor:
    """Static AST-based auditor verifying end-to-end connectivity of every framework module."""

    def __init__(self, workspace_root: str | Path = ".") -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.src_dir = self.workspace_root / "src" / "corporate_engineer"
        self.tests_dir = self.workspace_root / "tests"

    def _get_top_level_exports(self) -> set[str]:
        """Collect all symbols exported in __all__ across all __init__.py files in src/."""
        exports: set[str] = set()
        if not self.src_dir.exists():
            return exports

        for init_file in self.src_dir.rglob("__init__.py"):
            try:
                tree = ast.parse(init_file.read_text(encoding="utf-8", errors="ignore"))
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if (
                                isinstance(target, ast.Name)
                                and target.id == "__all__"
                                and isinstance(node.value, (ast.List, ast.Tuple, ast.Set))
                            ):
                                for elt in node.value.elts:
                                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                        exports.add(elt.value)
            except Exception:  # noqa: BLE001, S112
                continue
        return exports

    def _get_test_contents(self) -> dict[str, str]:
        """Pre-load test file contents for fast reference checks."""
        test_files: dict[str, str] = {}
        if not self.tests_dir.exists():
            return test_files

        for t_file in self.tests_dir.glob("test_*.py"):
            try:
                test_files[t_file.stem] = t_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:  # noqa: BLE001, S112
                continue
        return test_files

    def _extract_module_symbols(self, file_path: Path) -> list[str]:
        """Extract public classes and functions defined in a module."""
        symbols: list[str] = []
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8", errors="ignore"))
            for node in tree.body:
                if isinstance(
                    node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
                ) and not node.name.startswith("_"):
                    symbols.append(node.name)
        except Exception:  # noqa: BLE001, S110
            pass
        return symbols

    def audit(self) -> WiringAuditReport:
        """Execute full capability wiring audit across src/corporate_engineer/."""
        if not self.src_dir.exists():
            return WiringAuditReport(
                total_modules=0,
                connected_modules=[],
                unwired_modules=[],
                missing_test_modules=[],
                orphan_symbols=[],
                passed=True,
                remediation_actions=["src/corporate_engineer not found in workspace."],
            )

        known_exports = self._get_top_level_exports()
        test_contents = self._get_test_contents()

        all_modules: list[Path] = [
            f
            for f in self.src_dir.rglob("*.py")
            if f.name not in ("__init__.py", "__main__.py") and "__pycache__" not in f.parts
        ]

        connected_modules: list[str] = []
        unwired_modules: list[str] = []
        missing_test_modules: list[str] = []
        orphan_symbols: list[str] = []
        remediation_actions: list[str] = []

        for mod_path in all_modules:
            mod_stem = mod_path.stem
            rel_path = str(mod_path.relative_to(self.workspace_root)).replace("\\", "/")
            symbols = self._extract_module_symbols(mod_path)

            # 1. Test coverage check
            direct_test_name = f"test_{mod_stem}"
            has_direct_test = direct_test_name in test_contents
            has_indirect_test = False

            if not has_direct_test:
                # Check if symbols or module name are tested elsewhere
                for t_content in test_contents.values():
                    if mod_stem in t_content or any(s in t_content for s in symbols):
                        has_indirect_test = True
                        break

            has_test = has_direct_test or has_indirect_test
            if not has_test:
                missing_test_modules.append(rel_path)

            # 2. Export check
            is_cli_cmd = "cli/commands" in rel_path or "cli\\commands" in rel_path
            is_exported = (
                is_cli_cmd
                or any(s in known_exports for s in symbols)
                or (mod_stem in known_exports)
            )

            # 3. Connection status
            if has_test and is_exported:
                connected_modules.append(rel_path)
            else:
                unwired_modules.append(rel_path)
                if not is_exported:
                    remediation_actions.append(
                        f"Export primary symbols of '{rel_path}' in appropriate __all__ or parent __init__.py."
                    )
                if not has_test:
                    remediation_actions.append(
                        f"Create dedicated test suite tests/test_{mod_stem}.py for '{rel_path}'."
                    )

        passed = len(unwired_modules) == 0 and len(missing_test_modules) == 0

        return WiringAuditReport(
            total_modules=len(all_modules),
            connected_modules=connected_modules,
            unwired_modules=unwired_modules,
            missing_test_modules=missing_test_modules,
            orphan_symbols=orphan_symbols,
            passed=passed,
            remediation_actions=remediation_actions,
        )
