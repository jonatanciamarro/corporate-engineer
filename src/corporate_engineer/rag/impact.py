"""
Blast Radius Analyzer for Code GraphRAG (IMP-0008).
Computes reverse dependency trees, direct and transitive callers, and affected test suites.
"""

import ast
from collections import deque
from pathlib import Path

from corporate_engineer.models import BlastRadiusReport, ImpactNode
from corporate_engineer.rag.ast_indexer import ASTCodebaseIndexer


class BlastRadiusAnalyzer:
    """Analyzes the blast radius and transitive impacts of modifying code elements."""

    def __init__(
        self,
        workspace_root: str | Path = ".",
        root_path: str | Path | None = None,
    ) -> None:
        self.root = Path(root_path if root_path is not None else workspace_root).resolve()
        self.indexer = ASTCodebaseIndexer(root_path=self.root)

    def _discover_python_files(self) -> list[Path]:
        """Find all Python source and test files, ignoring virtual environments."""
        files: list[Path] = []
        for p in self.root.rglob("*.py"):
            parts = p.parts
            if any(
                part.startswith(".")
                or part in ("venv", ".venv", "__pycache__", "build", "dist", ".git")
                for part in parts
            ):
                continue
            files.append(p)
        return files

    def _parse_file(self, file_path: Path) -> ast.AST | None:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            return ast.parse(content, filename=str(file_path))
        except (SyntaxError, OSError):
            return None

    def analyze_symbol(self, symbol: str, max_depth: int = 3) -> BlastRadiusReport:
        """Calculate blast radius and affected tests for a specific symbol."""
        return self.analyze_impact(target_symbol=symbol, max_depth=max_depth)

    def analyze_file(self, file_path: str | Path, max_depth: int = 3) -> BlastRadiusReport:
        """Calculate blast radius and affected tests for a given file."""
        return self.analyze_impact(target_file=str(file_path), max_depth=max_depth)

    def analyze_impact(
        self,
        target_symbol: str | None = None,
        target_file: str | None = None,
        max_depth: int = 3,
    ) -> BlastRadiusReport:
        """Calculate blast radius and affected tests for a given symbol or file."""
        if not target_symbol and not target_file:
            raise ValueError("Must provide either target_symbol or target_file")

        target_name = target_symbol or Path(target_file).name  # type: ignore[arg-type]
        target_type = "SYMBOL" if target_symbol else "FILE"

        py_files = self._discover_python_files()

        # Graphs:
        # reverse_calls: callee_name -> list of {"caller_symbol": str, "file_path": str}
        # reverse_imports: imported_name/module -> list of {"file_path": str}
        # file_exports: file_path -> list of defined symbols
        reverse_calls: dict[str, list[dict[str, str]]] = {}
        reverse_imports: dict[str, list[str]] = {}
        file_to_symbols: dict[str, list[str]] = {}

        for f in py_files:
            rel_path = str(f.relative_to(self.root)).replace("\\", "/")
            tree = self._parse_file(f)
            if not tree:
                continue

            # Extract defined functions and classes
            defined_symbols: list[str] = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    defined_symbols.append(node.name)
            file_to_symbols[rel_path] = defined_symbols

            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        mod = alias.name.split(".")[-1]
                        reverse_imports.setdefault(mod, []).append(rel_path)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        mod = node.module.split(".")[-1]
                        reverse_imports.setdefault(mod, []).append(rel_path)
                    for alias in node.names:
                        reverse_imports.setdefault(alias.name, []).append(rel_path)

            # Extract function call relationships
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    caller_name = node.name
                    for child in ast.walk(node):
                        if isinstance(child, ast.Call):
                            callee_name: str | None = None
                            if isinstance(child.func, ast.Name):
                                callee_name = child.func.id
                            elif isinstance(child.func, ast.Attribute):
                                callee_name = child.func.attr

                            if callee_name and callee_name != caller_name:
                                reverse_calls.setdefault(callee_name, []).append(
                                    {"caller_symbol": caller_name, "file_path": rel_path}
                                )

        # Perform BFS traversal
        impacted_nodes: list[ImpactNode] = []
        visited_symbols: set[tuple[str, str]] = set()
        queue: deque[tuple[str, str, int]] = deque()  # (symbol, file_path, current_depth)

        # Initialize queue
        if target_type == "SYMBOL":
            queue.append((target_name, "", 1))
        else:
            # File target: enqueue all its exported symbols and the file itself
            target_rel = Path(target_file).name  # type: ignore[arg-type]
            for rel_file, symbols in file_to_symbols.items():
                if target_rel in rel_file:
                    for sym in symbols:
                        queue.append((sym, rel_file, 1))

        # Also check direct file importers
        stem = Path(target_name).stem
        if stem in reverse_imports:
            for imp_file in reverse_imports[stem]:
                visited_symbols.add((stem, imp_file))
                impacted_nodes.append(
                    ImpactNode(
                        symbol=stem,
                        file_path=imp_file,
                        depth=1,
                        impact_type="DIRECT",
                        relationship="IMPORTS",
                    )
                )

        while queue:
            current_sym, _current_file, depth = queue.popleft()
            if depth > max_depth:
                continue

            # Check reverse calls for current_sym
            for caller_info in reverse_calls.get(current_sym, []):
                caller_sym = caller_info["caller_symbol"]
                caller_file = caller_info["file_path"]

                key = (caller_sym, caller_file)
                if key not in visited_symbols:
                    visited_symbols.add(key)
                    impact_type = "DIRECT" if depth == 1 else "TRANSITIVE"
                    impacted_nodes.append(
                        ImpactNode(
                            symbol=caller_sym,
                            file_path=caller_file,
                            depth=depth,
                            impact_type=impact_type,
                            relationship="CALLS",
                        )
                    )
                    queue.append((caller_sym, caller_file, depth + 1))

            # Check reverse imports for current_sym
            for imp_file in reverse_imports.get(current_sym, []):
                key = (current_sym, imp_file)
                if key not in visited_symbols:
                    visited_symbols.add(key)
                    impact_type = "DIRECT" if depth == 1 else "TRANSITIVE"
                    impacted_nodes.append(
                        ImpactNode(
                            symbol=current_sym,
                            file_path=imp_file,
                            depth=depth,
                            impact_type=impact_type,
                            relationship="IMPORTS",
                        )
                    )

        # Identify affected tests
        affected_tests_set: set[str] = set()
        impacted_files = {node.file_path for node in impacted_nodes}
        if target_file:
            impacted_files.add(target_file)

        impacted_symbol_names = {node.symbol for node in impacted_nodes}
        if target_symbol:
            impacted_symbol_names.add(target_symbol)

        for f in py_files:
            rel = str(f.relative_to(self.root)).replace("\\", "/")
            if "test" in rel.lower():
                # Check if test file is in impacted files directly
                if rel in impacted_files:
                    affected_tests_set.add(rel)
                    continue

                # Check if test file imports any impacted symbol or module
                tree = self._parse_file(f)
                if not tree:
                    continue

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for a in node.names:
                            if any(sym in a.name for sym in impacted_symbol_names):
                                affected_tests_set.add(rel)
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and any(sym in node.module for sym in impacted_symbol_names):
                            affected_tests_set.add(rel)
                        for a in node.names:
                            if a.name in impacted_symbol_names:
                                affected_tests_set.add(rel)
                    elif isinstance(node, ast.Call):
                        callee = ""
                        if isinstance(node.func, ast.Name):
                            callee = node.func.id
                        elif isinstance(node.func, ast.Attribute):
                            callee = node.func.attr
                        if callee in impacted_symbol_names:
                            affected_tests_set.add(rel)

        sorted_tests = sorted(affected_tests_set)
        test_cmd = (
            f".venv\\Scripts\\pytest {' '.join(sorted_tests)}"
            if sorted_tests
            else ".venv\\Scripts\\pytest"
        )

        distinct_files = {node.file_path for node in impacted_nodes}
        distinct_symbols = {node.symbol for node in impacted_nodes}

        return BlastRadiusReport(
            target=target_name,
            target_type=target_type,
            total_impacted_files=len(distinct_files),
            total_impacted_symbols=len(distinct_symbols),
            impacted_nodes=impacted_nodes,
            affected_tests=sorted_tests,
            recommended_test_command=test_cmd,
        )
