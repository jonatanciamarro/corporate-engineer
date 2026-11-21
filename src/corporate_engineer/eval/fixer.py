"""
AST Auto-Refactor & Self-Healing Fixer (IMP-0012).
Applies conservative, deterministic AST transformations using ast.NodeTransformer
to automatically resolve structural violations and type-hinting omissions.
"""

from __future__ import annotations

import ast
from pathlib import Path

from corporate_engineer.models import FixDetail, FixReport
from corporate_engineer.system_one.router import SystemOneRouter


class InitReturnAnnotationFixer(ast.NodeTransformer):
    """Adds '-> None' return annotation to __init__ methods lacking explicit return types."""

    def __init__(self, file_path: str = "") -> None:
        super().__init__()
        self.file_path = file_path
        self.fixes: list[FixDetail] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        self.generic_visit(node)
        if node.name == "__init__" and node.returns is None:
            node.returns = ast.Constant(value=None)
            self.fixes.append(
                FixDetail(
                    file_path=self.file_path,
                    rule_name="init_return_none",
                    line_number=node.lineno,
                    description="Adicionada anotação de retorno '-> None' ao método __init__",
                    original_snippet="def __init__(...):",
                    fixed_snippet="def __init__(...) -> None:",
                )
            )
        return node


class MutableDefaultArgumentFixer(ast.NodeTransformer):
    """Replaces mutable default arguments ([], {}) with None and injects body preambles."""

    def __init__(self, file_path: str = "") -> None:
        super().__init__()
        self.file_path = file_path
        self.fixes: list[FixDetail] = []

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        self.generic_visit(node)
        self._transform_function_args(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        self.generic_visit(node)
        self._transform_function_args(node)
        return node

    def _transform_function_args(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        args = node.args.args
        defaults = node.args.defaults
        if not defaults:
            return

        # Align defaults with corresponding positional arguments
        offset = len(args) - len(defaults)
        new_defaults: list[ast.expr] = []
        preamble_stmts: list[ast.stmt] = []

        for i, default in enumerate(defaults):
            arg = args[offset + i]
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                # Replace default with None
                new_defaults.append(ast.Constant(value=None))

                # Create preamble: if arg is None: arg = <default>
                test = ast.Compare(
                    left=ast.Name(id=arg.arg, ctx=ast.Load()),
                    ops=[ast.Is()],
                    comparators=[ast.Constant(value=None)],
                )
                assign = ast.Assign(
                    targets=[ast.Name(id=arg.arg, ctx=ast.Store())],
                    value=default,
                )
                if_stmt = ast.If(test=test, body=[assign], orelse=[])
                preamble_stmts.append(if_stmt)

                self.fixes.append(
                    FixDetail(
                        file_path=self.file_path,
                        rule_name="mutable_default_argument",
                        line_number=node.lineno,
                        description=(
                            f"Substituído argumento padrão mutável '{arg.arg}' por None "
                            "com inicialização defensiva no corpo"
                        ),
                        original_snippet=f"{arg.arg}={ast.unparse(default)}",
                        fixed_snippet=f"{arg.arg}=None",
                    )
                )
            else:
                new_defaults.append(default)

        node.args.defaults = new_defaults

        if preamble_stmts:
            # Preserve docstring as first statement if present
            insert_idx = 0
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                insert_idx = 1

            for stmt in reversed(preamble_stmts):
                node.body.insert(insert_idx, stmt)


class RedundantPassCleaner(ast.NodeTransformer):
    """Removes redundant 'pass' statements when docstrings or other statements are present."""

    def __init__(self, file_path: str = "") -> None:
        super().__init__()
        self.file_path = file_path
        self.fixes: list[FixDetail] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        self.generic_visit(node)
        self._clean_body(node)
        return node

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        self.generic_visit(node)
        self._clean_body(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        self.generic_visit(node)
        self._clean_body(node)
        return node

    def _clean_body(
        self, node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef | ast.Module
    ) -> None:
        if len(node.body) > 1:
            new_body: list[ast.stmt] = []
            for stmt in node.body:
                if isinstance(stmt, ast.Pass):
                    self.fixes.append(
                        FixDetail(
                            file_path=self.file_path,
                            rule_name="redundant_pass",
                            line_number=stmt.lineno,
                            description="Removida instrução 'pass' redundante",
                            original_snippet="pass",
                            fixed_snippet="",
                        )
                    )
                else:
                    new_body.append(stmt)
            node.body = new_body


class ASTSelfHealingFixer:
    """Enterprise self-healing AST auto-refactoring engine with System-One risk guardrails."""

    def __init__(self) -> None:
        self.router = SystemOneRouter()

    def fix_code(self, code: str, file_path: str = "snippet.py") -> tuple[str, list[FixDetail]]:
        """Parses, applies transformations and returns refactored code and fix details."""
        tree = ast.parse(code)
        all_fixes: list[FixDetail] = []

        # 1. __init__ return annotation
        init_fixer = InitReturnAnnotationFixer(file_path=file_path)
        tree = init_fixer.visit(tree)
        all_fixes.extend(init_fixer.fixes)

        # 2. Mutable default arguments
        mutable_fixer = MutableDefaultArgumentFixer(file_path=file_path)
        tree = mutable_fixer.visit(tree)
        all_fixes.extend(mutable_fixer.fixes)

        # 3. Redundant pass cleaner
        pass_cleaner = RedundantPassCleaner(file_path=file_path)
        tree = pass_cleaner.visit(tree)
        all_fixes.extend(pass_cleaner.fixes)

        if not all_fixes:
            return code, []

        ast.fix_missing_locations(tree)
        fixed_code = ast.unparse(tree)

        # Ensure trailing newline
        if not fixed_code.endswith("\n"):
            fixed_code += "\n"

        # Syntactic safety check: ensure result parses cleanly
        ast.parse(fixed_code)

        return fixed_code, all_fixes

    def fix_file(self, file_path: str | Path, dry_run: bool = False) -> FixReport:
        """Applies auto-refactoring to an individual python file."""
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"Arquivo não encontrado: {path}")

        original_code = path.read_text(encoding="utf-8")
        fixed_code, details = self.fix_code(original_code, file_path=str(path))

        is_modified = len(details) > 0 and fixed_code.strip() != original_code.strip()

        # System-One Risk Guardrail
        risk_level = "LOW"
        if details:
            diff_summary = f"Auto-refactor on {path.name}: {len(details)} AST fixes applied."
            risk_decision = self.router.assess_risk(diff_summary)
            risk_level = "HIGH" if risk_decision.decision else "LOW"

        if is_modified and not dry_run:
            path.write_text(fixed_code, encoding="utf-8")

        return FixReport(
            total_files_analyzed=1,
            files_modified=1 if is_modified else 0,
            fixes_applied=details,
            dry_run=dry_run,
            system_one_risk=risk_level,
            success=True,
        )

    def fix_workspace(self, path: str | Path = ".", dry_run: bool = False) -> FixReport:
        """Scans a directory tree, fixing structural violations across python files."""
        root = Path(path).resolve()
        ignored_dirs = {
            ".git",
            ".venv",
            "venv",
            "__pycache__",
            "build",
            "dist",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
        }

        files_to_scan: list[Path] = []
        if root.is_file():
            files_to_scan.append(root)
        else:
            for p in root.rglob("*.py"):
                if any(part in ignored_dirs for part in p.parts):
                    continue
                files_to_scan.append(p)

        all_details: list[FixDetail] = []
        files_modified = 0

        for f in files_to_scan:
            rep = self.fix_file(f, dry_run=dry_run)
            if rep.files_modified > 0:
                files_modified += 1
                all_details.extend(rep.fixes_applied)

        # Global risk
        global_risk = "LOW"
        if all_details:
            risk_decision = self.router.assess_risk(
                f"Workspace auto-refactor: {len(all_details)} fixes across {files_modified} files."
            )
            global_risk = "HIGH" if risk_decision.decision else "LOW"

        return FixReport(
            total_files_analyzed=len(files_to_scan),
            files_modified=files_modified,
            fixes_applied=all_details,
            dry_run=dry_run,
            system_one_risk=global_risk,
            success=True,
        )
