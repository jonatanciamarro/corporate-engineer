"""
Capability Wiring Auditor (IMP-0029 / ADR-028, IMP-0039 / ADR-034).
Enforces continuous auto-wiring and maximum capability power across the entire repository.
Verifies that no orphaned or disconnected modules exist without exports, tests, and integration.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from corporate_engineer.models import WiringAuditReport


@dataclass(frozen=True)
class TestASTReferences:
    """AST-extracted imports, identifier references, and test definition flag for a test file."""

    imported_names: frozenset[str]
    referenced_names: frozenset[str]
    has_test_defs: bool


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

    @staticmethod
    def _collect_import_aliases(aliases: list[ast.alias], imported_names: set[str]) -> None:
        """Collect imported names, trailing dotted segments, and aliases from AST import nodes."""
        for alias in aliases:
            if alias.name != "*":
                imported_names.add(alias.name)
                imported_names.add(alias.name.split(".")[-1])
            if alias.asname:
                imported_names.add(alias.asname)

    def _extract_test_references(self, file_path: Path) -> TestASTReferences:
        """Parse a test file via AST to extract imports, identifier references, and test defs."""
        imported_names: set[str] = set()
        referenced_names: set[str] = set()
        has_test_defs = False

        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:  # noqa: BLE001
            return TestASTReferences(
                imported_names=frozenset(),
                referenced_names=frozenset(),
                has_test_defs=False,
            )

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self._collect_import_aliases(node.names, imported_names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imported_names.add(node.module)
                    imported_names.add(node.module.split(".")[-1])
                self._collect_import_aliases(node.names, imported_names)
            elif isinstance(node, ast.Name):
                referenced_names.add(node.id)
            elif isinstance(node, ast.Attribute):
                referenced_names.add(node.attr)
            elif (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name.startswith("test_")
            ) or (isinstance(node, ast.ClassDef) and node.name.startswith("Test")):
                has_test_defs = True

        return TestASTReferences(
            imported_names=frozenset(imported_names),
            referenced_names=frozenset(referenced_names),
            has_test_defs=has_test_defs,
        )

    def _get_test_ast_index(self) -> dict[str, TestASTReferences]:
        """Pre-parse all test_*.py files into an AST reference index."""
        test_index: dict[str, TestASTReferences] = {}
        if not self.tests_dir.exists():
            return test_index

        for t_file in self.tests_dir.glob("test_*.py"):
            test_index[t_file.stem] = self._extract_test_references(t_file)
        return test_index

    @staticmethod
    def _references_module(
        test_refs: TestASTReferences,
        mod_stem: str,
        symbols: list[str],
    ) -> bool:
        """Return True when the parsed test AST imports mod_stem or references a module symbol."""
        if mod_stem in test_refs.imported_names:
            return True
        return any(
            sym in test_refs.imported_names or sym in test_refs.referenced_names for sym in symbols
        )

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

    @staticmethod
    def _collect_parser_calls(parser_path: Path) -> set[str]:
        """Extract called function names inside cli/parser.py via AST."""
        called: set[str] = set()
        if not parser_path.exists():
            return called
        try:
            tree = ast.parse(parser_path.read_text(encoding="utf-8", errors="ignore"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        called.add(node.func.id)
                    elif isinstance(node.func, ast.Attribute):
                        called.add(node.func.attr)
        except Exception:  # noqa: BLE001, S110
            pass
        return called

    @staticmethod
    def _collect_main_references(main_path: Path) -> set[str]:
        """Extract referenced handler identifiers inside cli/main.py via AST."""
        referenced: set[str] = set()
        if not main_path.exists():
            return referenced
        try:
            tree = ast.parse(main_path.read_text(encoding="utf-8", errors="ignore"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    referenced.add(node.id)
                elif isinstance(node, ast.Attribute):
                    referenced.add(node.attr)
        except Exception:  # noqa: BLE001, S110
            pass
        return referenced

    def _audit_cli_command_wiring(self) -> tuple[set[str], list[str]]:
        """Verify every cli/commands/*.py register_*_parser & handle_* is wired in parser & main."""
        cli_commands_dir = self.src_dir / "cli" / "commands"
        if not cli_commands_dir.exists():
            return set(), []

        parser_path = self.src_dir / "cli" / "parser.py"
        main_path = self.src_dir / "cli" / "main.py"
        called_in_parser = self._collect_parser_calls(parser_path)
        used_in_main = self._collect_main_references(main_path)

        unwired_cli_paths: set[str] = set()
        actions: list[str] = []

        for cmd_file in sorted(cli_commands_dir.glob("*.py")):
            if cmd_file.name == "__init__.py":
                continue
            rel_cmd = str(cmd_file.relative_to(self.workspace_root)).replace("\\", "/")
            try:
                tree = ast.parse(cmd_file.read_text(encoding="utf-8", errors="ignore"))
            except Exception:  # noqa: BLE001
                unwired_cli_paths.add(rel_cmd)
                actions.append(f"Fix syntax errors in CLI command module '{rel_cmd}'.")
                continue

            reg_funcs = [
                n.name
                for n in tree.body
                if isinstance(n, ast.FunctionDef)
                and n.name.startswith("register_")
                and n.name.endswith("_parser")
            ]
            handle_funcs = [
                n.name
                for n in tree.body
                if isinstance(n, ast.FunctionDef) and n.name.startswith("handle_")
            ]

            missing_reg = [fn for fn in reg_funcs if fn not in called_in_parser]
            missing_handle = [fn for fn in handle_funcs if fn not in used_in_main]

            if not parser_path.exists() or not reg_funcs or missing_reg:
                unwired_cli_paths.add(rel_cmd)
                detail = ", ".join(missing_reg) if missing_reg else "register_*_parser"
                actions.append(
                    f"Call {detail} from '{rel_cmd}' inside src/corporate_engineer/cli/parser.py."
                )
            if not main_path.exists() or missing_handle:
                unwired_cli_paths.add(rel_cmd)
                detail = ", ".join(missing_handle) if missing_handle else "handle_*"
                actions.append(
                    f"Dispatch {detail} from '{rel_cmd}' inside src/corporate_engineer/cli/main.py."
                )

        return unwired_cli_paths, actions

    def _audit_refiner_domain_keywords(self) -> tuple[list[str], list[str]]:
        """Verify all module paths declared in ContextAwarePromptRefiner.DOMAIN_KEYWORDS exist."""
        refiner_path = self.src_dir / "prompt" / "refiner.py"
        if not refiner_path.exists():
            return [], []

        broken_paths: list[str] = []
        actions: list[str] = []
        try:
            tree = ast.parse(refiner_path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:  # noqa: BLE001
            return ["src/corporate_engineer/prompt/refiner.py"], [
                "Fix syntax errors in 'src/corporate_engineer/prompt/refiner.py'."
            ]

        domain_keywords_node: ast.expr | None = None
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == "ContextAwarePromptRefiner":
                for item in node.body:
                    if (
                        isinstance(item, ast.AnnAssign)
                        and isinstance(item.target, ast.Name)
                        and item.target.id == "DOMAIN_KEYWORDS"
                    ) or (
                        isinstance(item, ast.Assign)
                        and any(
                            isinstance(t, ast.Name) and t.id == "DOMAIN_KEYWORDS"
                            for t in item.targets
                        )
                    ):
                        domain_keywords_node = item.value

        if domain_keywords_node is None:
            return [], []

        try:
            domain_keywords = ast.literal_eval(domain_keywords_node)
        except Exception:  # noqa: BLE001
            return [], []

        if not isinstance(domain_keywords, dict):
            return [], []

        for domain_name, meta in domain_keywords.items():
            if not isinstance(meta, dict):
                continue
            modules = meta.get("modules", [])
            if not isinstance(modules, list):
                continue
            for mod_rel in modules:
                if not isinstance(mod_rel, str):
                    continue
                candidate = (self.workspace_root / mod_rel).resolve()
                try:
                    candidate.relative_to(self.workspace_root)
                    in_workspace = True
                except ValueError:
                    in_workspace = False
                if not in_workspace or not candidate.exists():
                    if mod_rel not in broken_paths:
                        broken_paths.append(mod_rel)
                    actions.append(
                        f"Fix missing ContextAwarePromptRefiner.DOMAIN_KEYWORDS['{domain_name}'] "
                        f"module path '{mod_rel}' on disk."
                    )

        return broken_paths, actions

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
        test_ast_index = self._get_test_ast_index()
        unwired_cli_paths, cli_actions = self._audit_cli_command_wiring()
        broken_refiner_paths, refiner_actions = self._audit_refiner_domain_keywords()

        all_modules: list[Path] = [
            f
            for f in self.src_dir.rglob("*.py")
            if f.name not in ("__init__.py", "__main__.py") and "__pycache__" not in f.parts
        ]

        connected_modules: list[str] = []
        unwired_modules: list[str] = []
        missing_test_modules: list[str] = []
        orphan_symbols: list[str] = []
        remediation_actions: list[str] = [*cli_actions, *refiner_actions]

        for mod_path in all_modules:
            mod_stem = mod_path.stem
            rel_path = str(mod_path.relative_to(self.workspace_root)).replace("\\", "/")
            symbols = self._extract_module_symbols(mod_path)

            # 1. Test coverage check via genuine AST import/reference analysis
            direct_test_name = f"test_{mod_stem}"
            direct_refs = test_ast_index.get(direct_test_name)
            has_direct_test = direct_refs is not None and (
                direct_refs.has_test_defs or self._references_module(direct_refs, mod_stem, symbols)
            )
            has_indirect_test = False

            if not has_direct_test:
                has_indirect_test = any(
                    self._references_module(t_refs, mod_stem, symbols)
                    for t_refs in test_ast_index.values()
                )

            has_test = has_direct_test or has_indirect_test
            if not has_test:
                missing_test_modules.append(rel_path)

            # 2. Export & CLI wiring check
            is_cli_cmd = "cli/commands" in rel_path or "cli\\commands" in rel_path
            is_cli_wired = (not is_cli_cmd) or (rel_path not in unwired_cli_paths)
            is_exported = (
                (is_cli_cmd and is_cli_wired)
                or any(s in known_exports for s in symbols)
                or (mod_stem in known_exports)
            )

            # 3. Connection status
            if has_test and is_exported and is_cli_wired:
                connected_modules.append(rel_path)
            else:
                unwired_modules.append(rel_path)
                if not is_exported and not is_cli_cmd:
                    remediation_actions.append(
                        f"Export primary symbols of '{rel_path}' in appropriate __all__ or parent __init__.py."
                    )
                if not has_test:
                    remediation_actions.append(
                        f"Create dedicated test suite tests/test_{mod_stem}.py for '{rel_path}'."
                    )

        for broken_path in broken_refiner_paths:
            if broken_path not in unwired_modules:
                unwired_modules.append(broken_path)

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
