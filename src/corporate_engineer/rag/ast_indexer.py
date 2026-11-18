"""
AST Codebase Indexer for structured, token-efficient repository representation.
Parses Abstract Syntax Trees to extract top-level classes, methods, docstrings and signatures.
"""

import ast
import os
from pathlib import Path
from typing import Any


class ASTCodebaseIndexer:
    def __init__(self, root_path: Path):
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
                methods = [
                    m.name
                    for m in node.body
                    if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                symbols.append(
                    {
                        "type": "class",
                        "name": node.name,
                        "line": node.lineno,
                        "methods": methods,
                        "docstring": ast.get_docstring(node),
                    }
                )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                symbols.append(
                    {
                        "type": "function",
                        "name": node.name,
                        "line": node.lineno,
                        "args": [arg.arg for arg in node.args.args],
                        "docstring": ast.get_docstring(node),
                    }
                )

        return symbols

    def build_codebase_outline(self) -> str:
        lines = [f"# Codebase Outline for: {self.root_path.name}\n"]
        for root, dirs, files in os.walk(self.root_path):
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".") and d not in {"venv", ".venv", "__pycache__"}
            ]
            for f in files:
                if f.endswith(".py"):
                    full_p = Path(root) / f
                    rel_p = full_p.relative_to(self.root_path)
                    symbols = self.index_file(full_p)
                    if symbols:
                        lines.append(f"## File: {rel_p}")
                        for s in symbols:
                            if s["type"] == "class":
                                methods_str = ", ".join(s["methods"]) if s["methods"] else "none"
                                lines.append(
                                    f"  - Class `{s['name']}` (line {s['line']}) [Methods: {methods_str}]"
                                )
                            else:
                                args_str = ", ".join(s.get("args", []))
                                lines.append(
                                    f"  - Function `{s['name']}({args_str})` (line {s['line']})"
                                )
                        lines.append("")
        return "\n".join(lines)
