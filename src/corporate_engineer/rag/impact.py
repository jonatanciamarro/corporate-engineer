"""
Blast Radius Analyzer for Code GraphRAG (IMP-0008 / ADR-025).
Computes reverse dependency trees, direct and transitive callers, and affected test suites.
"""

import ast
from collections import deque
from collections.abc import Sequence
from pathlib import Path

from corporate_engineer.models import BlastRadiusReport, ImpactNode
from corporate_engineer.rag.cached_ast_indexer import CachedASTCodebaseIndexer


class BlastRadiusAnalyzer:
    """Analyzes the blast radius and transitive impacts of modifying code elements."""

    def __init__(
        self,
        workspace_root: str | Path = ".",
        root_path: str | Path | None = None,
    ) -> None:
        self.root = Path(root_path if root_path is not None else workspace_root).resolve()
        self.indexer = CachedASTCodebaseIndexer(root_path=self.root)

    def _discover_python_files(self) -> list[Path]:
        """Find all Python source and test files, ignoring virtual environments."""
        files: list[Path] = []
        for p in self.root.rglob("*.py"):
            parts = p.parts
            if any(
                part.startswith(".")
                or part
                in (
                    "venv",
                    ".venv",
                    "__pycache__",
                    "build",
                    "dist",
                    ".git",
                    "node_modules",
                )
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

    def _build_dependency_graphs(
        self, py_files: list[Path]
    ) -> tuple[
        dict[str, list[dict[str, str]]],
        dict[str, list[str]],
        dict[str, list[str]],
    ]:
        """
        Build reverse call graph, reverse import graph, and file-to-symbols mapping
        using the cached AST indexer.
        """
        reverse_calls: dict[str, list[dict[str, str]]] = {}
        reverse_imports: dict[str, list[str]] = {}
        file_to_symbols: dict[str, list[str]] = {}

        for f in py_files:
            rel_path = str(f.relative_to(self.root)).replace("\\", "/")
            symbols = self.indexer.index_file(f)
            imports_data = self.indexer.extract_imports(f)

            defined_symbols: list[str] = []
            for s in symbols:
                if "name" in s:
                    defined_symbols.append(s["name"])
                if "methods" in s:
                    defined_symbols.extend(s["methods"])
                if "async_methods" in s:
                    defined_symbols.extend(s["async_methods"])
            file_to_symbols[rel_path] = defined_symbols

            for mod_name in imports_data.get("modules", []):
                mod = mod_name.split(".")[-1]
                reverse_imports.setdefault(mod, []).append(rel_path)

            for fi in imports_data.get("from_imports", []):
                if fi.get("module"):
                    mod = fi["module"].split(".")[-1]
                    reverse_imports.setdefault(mod, []).append(rel_path)
                for alias in fi.get("names", []):
                    reverse_imports.setdefault(alias, []).append(rel_path)

            for s in symbols:
                caller_name = s.get("name", "")
                for callee_name in s.get("calls", []):
                    if callee_name and callee_name != caller_name:
                        reverse_calls.setdefault(callee_name, []).append(
                            {"caller_symbol": caller_name, "file_path": rel_path}
                        )

        return reverse_calls, reverse_imports, file_to_symbols

    def _identify_affected_tests(
        self,
        py_files: list[Path],
        impacted_files: set[str],
        impacted_symbol_names: set[str],
    ) -> list[str]:
        """Identify test files impacted directly or transitively by modified files/symbols."""
        affected_tests_set: set[str] = set()
        for f in py_files:
            rel = str(f.relative_to(self.root)).replace("\\", "/")
            if "test" in rel.lower():
                if rel in impacted_files:
                    affected_tests_set.add(rel)
                    continue

                imports_info = self.indexer.extract_imports(f)
                if any(
                    any(sym in m for sym in impacted_symbol_names)
                    for m in imports_info.get("modules", [])
                ):
                    affected_tests_set.add(rel)
                    continue

                matched = False
                for fi in imports_info.get("from_imports", []):
                    if fi.get("module") and any(
                        sym in fi["module"] for sym in impacted_symbol_names
                    ):
                        affected_tests_set.add(rel)
                        matched = True
                        break
                    for a in fi.get("names", []):
                        if a in impacted_symbol_names:
                            affected_tests_set.add(rel)
                            matched = True
                            break
                if matched:
                    continue

                symbols = self.indexer.index_file(f)
                for s in symbols:
                    for callee in s.get("calls", []):
                        if callee in impacted_symbol_names:
                            affected_tests_set.add(rel)
                            break
        return sorted(affected_tests_set)

    def analyze_symbol(self, symbol: str, max_depth: int = 3) -> BlastRadiusReport:
        """Calculate blast radius and affected tests for a specific symbol."""
        return self.analyze_impact(target_symbol=symbol, max_depth=max_depth)

    def analyze_file(self, file_path: str | Path, max_depth: int = 3) -> BlastRadiusReport:
        """Calculate blast radius and affected tests for a given file."""
        return self.analyze_impact(target_file=str(file_path), max_depth=max_depth)

    def analyze_files(
        self,
        file_paths: Sequence[str | Path],
        max_depth: int = 3,
    ) -> BlastRadiusReport:
        """
        Analyze the combined blast radius and affected tests for multiple files
        in a single unified pass without repeatedly rescanning the filesystem.
        """
        if not file_paths:
            return BlastRadiusReport(
                target="none",
                target_type="FILES",
                total_impacted_files=0,
                total_impacted_symbols=0,
                impacted_nodes=[],
                affected_tests=[],
                recommended_test_command=".venv\\Scripts\\pytest",
            )

        py_files = self._discover_python_files()
        reverse_calls, reverse_imports, file_to_symbols = self._build_dependency_graphs(py_files)

        target_paths = [Path(p) for p in file_paths]
        target_names = {p.name for p in target_paths}
        target_stems = {p.stem for p in target_paths}

        impacted_nodes: list[ImpactNode] = []
        visited_symbols: set[tuple[str, str]] = set()
        queue: deque[tuple[str, str, int]] = deque()

        for rel_file, symbols in file_to_symbols.items():
            if any(t_name in rel_file for t_name in target_names):
                for sym in symbols:
                    queue.append((sym, rel_file, 1))

        for stem in target_stems:
            if stem in reverse_imports:
                for imp_file in reverse_imports[stem]:
                    if (stem, imp_file) not in visited_symbols:
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

        impacted_files = {node.file_path for node in impacted_nodes}
        for p in target_paths:
            try:
                rel = str(p.resolve().relative_to(self.root)).replace("\\", "/")
                impacted_files.add(rel)
            except (ValueError, OSError):
                impacted_files.add(str(p).replace("\\", "/"))

        impacted_symbol_names = {node.symbol for node in impacted_nodes}
        impacted_symbol_names.update(target_stems)

        affected_tests = self._identify_affected_tests(
            py_files, impacted_files, impacted_symbol_names
        )

        test_cmd = (
            f".venv\\Scripts\\pytest {' '.join(affected_tests)}"
            if affected_tests
            else ".venv\\Scripts\\pytest"
        )

        distinct_files = {node.file_path for node in impacted_nodes}
        distinct_symbols = {node.symbol for node in impacted_nodes}
        target_summary = ", ".join(p.name for p in target_paths)

        return BlastRadiusReport(
            target=target_summary,
            target_type="FILES",
            total_impacted_files=len(distinct_files),
            total_impacted_symbols=len(distinct_symbols),
            impacted_nodes=impacted_nodes,
            affected_tests=affected_tests,
            recommended_test_command=test_cmd,
        )

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
        reverse_calls, reverse_imports, file_to_symbols = self._build_dependency_graphs(py_files)

        impacted_nodes: list[ImpactNode] = []
        visited_symbols: set[tuple[str, str]] = set()
        queue: deque[tuple[str, str, int]] = deque()

        if target_type == "SYMBOL":
            queue.append((target_name, "", 1))
        else:
            target_rel = Path(target_file).name  # type: ignore[arg-type]
            for rel_file, symbols in file_to_symbols.items():
                if target_rel in rel_file:
                    for sym in symbols:
                        queue.append((sym, rel_file, 1))

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

        impacted_files = {node.file_path for node in impacted_nodes}
        if target_file:
            impacted_files.add(str(target_file).replace("\\", "/"))

        impacted_symbol_names = {node.symbol for node in impacted_nodes}
        if target_symbol:
            impacted_symbol_names.add(target_symbol)

        affected_tests = self._identify_affected_tests(
            py_files, impacted_files, impacted_symbol_names
        )

        test_cmd = (
            f".venv\\Scripts\\pytest {' '.join(affected_tests)}"
            if affected_tests
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
            affected_tests=affected_tests,
            recommended_test_command=test_cmd,
        )
