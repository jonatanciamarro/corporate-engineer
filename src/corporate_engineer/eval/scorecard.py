"""
Semantic Code Evaluator for Evaluation-Driven Development (EDD) Scorecard.
Analyzes Python codebases against 5 enterprise software engineering quality axes.
"""

import ast
from pathlib import Path
from typing import Any

from corporate_engineer.models import EvaluationAxisScore, SemanticEvaluationReport


class FunctionMetricsVisitor(ast.NodeVisitor):
    """Gathers function-level metrics: complexity, parameters, lines, and typing."""

    def __init__(self, source_lines: list[str]) -> None:
        self.source_lines = source_lines
        self.functions: list[dict[str, Any]] = []
        self.global_statements: list[int] = []
        self.has_bare_dict_returns: list[tuple[str, int]] = []

    def visit_Global(self, node: ast.Global) -> None:
        self.global_statements.append(node.lineno)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._analyze_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._analyze_function(node)
        self.generic_visit(node)

    def _analyze_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        # Calculate lines of code
        end_lineno = getattr(node, "end_lineno", node.lineno)
        loc = end_lineno - node.lineno + 1

        # Calculate parameters (excluding self and cls)
        params = [arg.arg for arg in node.args.args if arg.arg not in ("self", "cls")]

        # Count type annotations
        annotated_params = [
            arg.arg
            for arg in node.args.args
            if arg.arg not in ("self", "cls") and arg.annotation is not None
        ]
        has_return_type = node.returns is not None

        # Cyclomatic complexity
        complexity = 1

        for child in ast.walk(node):
            if isinstance(
                child,
                (
                    ast.If,
                    ast.IfExp,
                    ast.For,
                    ast.AsyncFor,
                    ast.While,
                    ast.ExceptHandler,
                    ast.With,
                    ast.AsyncWith,
                    ast.Assert,
                ),
            ):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1

        # Check for bare dictionary return
        for child in ast.walk(node):
            if isinstance(child, ast.Return) and isinstance(child.value, ast.Dict):
                self.has_bare_dict_returns.append((node.name, child.lineno))

        self.functions.append(
            {
                "name": node.name,
                "lineno": node.lineno,
                "loc": loc,
                "params": params,
                "param_count": len(params),
                "annotated_params_count": len(annotated_params),
                "has_return_type": has_return_type,
                "complexity": complexity,
            }
        )


class SemanticCodeEvaluator:
    """Evaluates Python code against 5 Corporate Software Engineering Axes."""

    def __init__(self, workspace_root: str | Path | None = None) -> None:
        self.workspace_root = Path(workspace_root) if workspace_root is not None else None

    def evaluate(
        self,
        target_path: str | Path | None = None,
        min_passing_score: float = 80.0,
    ) -> SemanticEvaluationReport:
        """Scan directory and compute composite corporate scorecard."""
        path = target_path or self.workspace_root or "."
        return self.evaluate_directory(directory_path=path, min_passing_score=min_passing_score)

    def evaluate_source(
        self,
        source_code: str,
        file_path: str = "<memory>",
        min_passing_score: float = 80.0,
    ) -> SemanticEvaluationReport:
        """Evaluate a single Python source code string and produce a report."""
        try:
            tree = ast.parse(source_code, filename=file_path)
        except SyntaxError as e:
            error_axis = EvaluationAxisScore(
                axis_name="Syntax & Parsing",
                score=0.0,
                weight=1.0,
                violations=[f"Syntax error at line {e.lineno}: {e.msg}"],
                passed=False,
            )
            return SemanticEvaluationReport(
                target_path=file_path,
                axes=[error_axis],
                total_files_evaluated=1,
                total_functions_evaluated=0,
                min_passing_score=min_passing_score,
            )

        source_lines = source_code.splitlines()
        visitor = FunctionMetricsVisitor(source_lines)
        visitor.visit(tree)

        return self._build_report(
            visitor=visitor,
            file_count=1,
            target_path=file_path,
            line_count=len(source_lines),
            min_passing_score=min_passing_score,
        )

    def evaluate_directory(
        self,
        directory_path: str | Path,
        min_passing_score: float = 80.0,
    ) -> SemanticEvaluationReport:
        """Scan all Python files in directory and compute composite corporate scorecard."""
        root = Path(directory_path).resolve()
        py_files: list[Path] = []

        if root.is_file() and root.suffix == ".py":
            py_files = [root]
        elif root.is_dir():
            for p in root.rglob("*.py"):
                parts = p.parts
                # Skip virtualenvs, hidden dirs, caches
                if any(
                    part.startswith(".")
                    or part in ("venv", ".venv", "__pycache__", "build", "dist")
                    for part in parts
                ):
                    continue
                py_files.append(p)

        all_functions: list[dict[str, Any]] = []
        all_globals: list[str] = []
        all_bare_dicts: list[str] = []
        total_lines = 0

        for file in py_files:
            try:
                content = file.read_text(encoding="utf-8", errors="ignore")
                total_lines += len(content.splitlines())
                tree = ast.parse(content, filename=str(file))
                visitor = FunctionMetricsVisitor(content.splitlines())
                visitor.visit(tree)

                all_functions.extend(visitor.functions)
                for g_line in visitor.global_statements:
                    all_globals.append(f"{file.name}:{g_line}")
                for fn_name, b_line in visitor.has_bare_dict_returns:
                    all_bare_dicts.append(f"{file.name}:{b_line} (function '{fn_name}')")
            except (SyntaxError, OSError):
                continue

        visitor_summary = FunctionMetricsVisitor([])
        visitor_summary.functions = all_functions

        return self._build_aggregated_report(
            functions=all_functions,
            globals_detected=all_globals,
            bare_dicts=all_bare_dicts,
            file_count=len(py_files),
            total_lines=total_lines,
            target_path=str(directory_path),
            min_passing_score=min_passing_score,
        )

    def _build_report(
        self,
        visitor: FunctionMetricsVisitor,
        file_count: int,
        target_path: str,
        line_count: int,
        min_passing_score: float,
    ) -> SemanticEvaluationReport:
        globals_list = [f"line {line}" for line in visitor.global_statements]
        bare_dicts_list = [
            f"line {line} in '{name}'" for name, line in visitor.has_bare_dict_returns
        ]
        return self._build_aggregated_report(
            functions=visitor.functions,
            globals_detected=globals_list,
            bare_dicts=bare_dicts_list,
            file_count=file_count,
            total_lines=line_count,
            target_path=target_path,
            min_passing_score=min_passing_score,
        )

    def _build_aggregated_report(
        self,
        functions: list[dict[str, Any]],
        globals_detected: list[str],
        bare_dicts: list[str],
        file_count: int,
        total_lines: int,
        target_path: str,
        min_passing_score: float,
    ) -> SemanticEvaluationReport:
        total_fn = max(1, len(functions))

        # Axis 1: Immutability & Pure Functions (weight: 0.20)
        immut_violations: list[str] = []
        for g in globals_detected:
            immut_violations.append(f"Global statement detected at {g}")

        if file_count <= 1:
            immut_score = max(0.0, 100.0 - 15.0 * len(globals_detected))
        else:
            penalty = (len(globals_detected) / max(1, file_count)) * 50.0
            immut_score = max(0.0, round(100.0 - penalty, 1))

        # Axis 2: Strong Typing & Pydantic Contracts (weight: 0.25)
        pydantic_violations: list[str] = []
        for bd in bare_dicts:
            pydantic_violations.append(
                f"Bare dictionary returned at {bd} instead of strongly-typed Pydantic DTO"
            )
        if functions:
            clean_returns = max(0, len(functions) - len(bare_dicts))
            pydantic_score = round((clean_returns / total_fn) * 100.0, 1)
        else:
            pydantic_score = 100.0

        # Axis 3: Cyclomatic Complexity (weight: 0.20)
        complexity_violations: list[str] = []
        simple_funcs_count = 0
        for fn in functions:
            if fn["complexity"] > 8:
                complexity_violations.append(
                    f"Function '{fn['name']}' has high cyclomatic complexity ({fn['complexity']} > 8)"
                )
            else:
                simple_funcs_count += 1
        if functions:
            complexity_score = round((simple_funcs_count / total_fn) * 100.0, 1)
        else:
            complexity_score = 100.0

        # Axis 4: Modularity & Hygiene (weight: 0.15)
        mod_violations: list[str] = []
        compliant_funcs_count = 0
        for fn in functions:
            is_compliant = True
            if fn["param_count"] > 5:
                mod_violations.append(
                    f"Function '{fn['name']}' has {fn['param_count']} parameters (recommended <= 5)"
                )
                is_compliant = False
            if fn["loc"] > 50:
                mod_violations.append(
                    f"Function '{fn['name']}' length ({fn['loc']} lines) exceeds 50 lines limit"
                )
                is_compliant = False
            if is_compliant:
                compliant_funcs_count += 1

        if file_count == 1 and total_lines > 800:
            mod_violations.append(f"File exceeds 800 lines ({total_lines} lines)")

        if functions:
            mod_score = round((compliant_funcs_count / total_fn) * 100.0, 1)
        else:
            mod_score = 100.0

        # Axis 5: Type Hints Coverage (weight: 0.20)
        type_violations: list[str] = []
        total_type_targets = 0
        annotated_type_targets = 0

        for fn in functions:
            targets = fn["param_count"] + 1  # params + return type
            annotated = fn["annotated_params_count"] + (1 if fn["has_return_type"] else 0)
            total_type_targets += targets
            annotated_type_targets += annotated

            if not fn["has_return_type"]:
                type_violations.append(
                    f"Function '{fn['name']}' is missing return type hint annotation"
                )
            if fn["annotated_params_count"] < fn["param_count"]:
                missing = fn["param_count"] - fn["annotated_params_count"]
                type_violations.append(
                    f"Function '{fn['name']}' has {missing} untyped parameter(s)"
                )

        if total_type_targets > 0:
            type_score = round((annotated_type_targets / total_type_targets) * 100.0, 1)
        else:
            type_score = 100.0

        axes = [
            EvaluationAxisScore(
                axis_name="Immutability & Pure Functions",
                score=immut_score,
                weight=0.20,
                violations=immut_violations,
                passed=immut_score >= min_passing_score,
            ),
            EvaluationAxisScore(
                axis_name="Strong Typing & Pydantic Contracts",
                score=pydantic_score,
                weight=0.25,
                violations=pydantic_violations,
                passed=pydantic_score >= min_passing_score,
            ),
            EvaluationAxisScore(
                axis_name="Cyclomatic Complexity",
                score=complexity_score,
                weight=0.20,
                violations=complexity_violations,
                passed=complexity_score >= min_passing_score,
            ),
            EvaluationAxisScore(
                axis_name="Modularity & Hygiene",
                score=mod_score,
                weight=0.15,
                violations=mod_violations,
                passed=mod_score >= min_passing_score,
            ),
            EvaluationAxisScore(
                axis_name="Type Hints Coverage",
                score=type_score,
                weight=0.20,
                violations=type_violations,
                passed=type_score >= min_passing_score,
            ),
        ]

        return SemanticEvaluationReport(
            target_path=target_path,
            axes=axes,
            total_files_evaluated=file_count,
            total_functions_evaluated=len(functions),
            min_passing_score=min_passing_score,
        )
