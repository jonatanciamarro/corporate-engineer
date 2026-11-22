"""
AST Codebase Indexer for structured, token-efficient repository representation.
Parses Abstract Syntax Trees to extract top-level classes, methods, docstrings and signatures.
"""

import ast
import os
from pathlib import Path
from typing import Any


class ASTCodebaseIndexer:
    def __init__(self, root_path: Path) -> None:
        self.root_path = root_path.resolve()

    def index_file(self, file_path: Path) -> list[dict[str, Any]]:
        symbols: list[dict[str, Any]] = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content, filename=str(file_path))
        except (OSError, SyntaxError):
            return symbols
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                sync_methods = [m.name for m in node.body if isinstance(m, ast.FunctionDef)]
                async_methods = [m.name for m in node.body if isinstance(m, ast.AsyncFunctionDef)]
                bases = [ast.unparse(b) for b in node.bases]
                decorators = [ast.unparse(d) for d in node.decorator_list]
                symbols.append(
                    {
                        "type": "class",
                        "name": node.name,
                        "line": node.lineno,
                        "bases": bases,
                        "decorators": decorators,
                        "methods": sync_methods,
                        "async_methods": async_methods,
                        "docstring": ast.get_docstring(node),
                    }
                )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                calls: list[str] = []
                for sub in ast.walk(node):
                    if isinstance(sub, ast.Call):
                        call_name: str | None = None
                        if isinstance(sub.func, ast.Name):
                            call_name = sub.func.id
                        elif isinstance(sub.func, ast.Attribute):
                            call_name = sub.func.attr
                        if call_name and call_name not in calls:
                            calls.append(call_name)
                decorators = [ast.unparse(d) for d in node.decorator_list]
                symbols.append(
                    {
                        "type": "function",
                        "name": node.name,
                        "line": node.lineno,
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                        "decorators": decorators,
                        "args": [arg.arg for arg in node.args.args],
                        "calls": calls,
                        "docstring": ast.get_docstring(node),
                    }
                )
        return symbols

    def extract_imports(self, file_path: Path) -> dict[str, Any]:
        """Extract module imports and from-imports from a python file."""
        modules: list[str] = []
        from_imports: list[dict[str, Any]] = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content, filename=str(file_path))
        except (OSError, SyntaxError):
            return {"modules": modules, "from_imports": from_imports}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name
                    if name not in modules:
                        modules.append(name)
            elif isinstance(node, ast.ImportFrom):
                mod_name = node.module or ""
                names = [alias.name for alias in node.names]
                from_imports.append({"module": mod_name, "names": names})
        return {"modules": modules, "from_imports": from_imports}

    def build_hierarchy_map(self) -> dict[str, list[str]]:
        """Map base class names to lists of their direct subclass names across the codebase."""
        hierarchy: dict[str, list[str]] = {}
        for root, dirs, files in os.walk(self.root_path):
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".") and d not in {"venv", ".venv", "__pycache__"}
            ]
            for f in sorted(files):
                if f.endswith(".py"):
                    full_p = Path(root) / f
                    symbols = self.index_file(full_p)
                    for sym in symbols:
                        if sym.get("type") == "class":
                            cls_name = sym["name"]
                            for base in sym.get("bases", []):
                                if base not in hierarchy:
                                    hierarchy[base] = []
                                if cls_name not in hierarchy[base]:
                                    hierarchy[base].append(cls_name)
        return hierarchy

    def build_codebase_outline(self) -> str:
        lines = [f"# Codebase Outline for: {self.root_path.name}\n"]
        for root, dirs, files in os.walk(self.root_path):
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".") and d not in {"venv", ".venv", "__pycache__"}
            ]
            for f in sorted(files):
                if f.endswith(".py"):
                    full_p = Path(root) / f
                    rel_p = full_p.relative_to(self.root_path)
                    symbols = self.index_file(full_p)
                    if symbols:
                        lines.append(f"## File: {rel_p}")
                        for s in symbols:
                            if s["type"] == "class":
                                all_methods = s.get("methods", []) + s.get("async_methods", [])
                                methods_str = ", ".join(all_methods) if all_methods else "none"
                                bases_str = (
                                    f"({', '.join(s.get('bases', []))})" if s.get("bases") else ""
                                )
                                lines.append(
                                    f"  - Class `{s['name']}{bases_str}` (line {s['line']}) [Methods: {methods_str}]"
                                )
                            else:
                                args_str = ", ".join(s.get("args", []))
                                async_prefix = "async " if s.get("is_async") else ""
                                lines.append(
                                    f"  - Function `{async_prefix}{s['name']}({args_str})` (line {s['line']})"
                                )
                        lines.append("")
        return "\n".join(lines)
