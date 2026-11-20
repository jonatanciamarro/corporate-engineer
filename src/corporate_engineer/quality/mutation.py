"""
Native AST Mutation Testing Engine for AI-Generated Code (IMP-0006).

Generates syntactic and semantic mutants via AST transformations and
evaluates test suite robustness against subtle logical regressions.
"""

import ast
import copy
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from corporate_engineer.models import Mutant, MutationReport


@dataclass
class MutationPoint:
    node_id: str
    line_number: int
    original_op: str
    mutated_op: str
    op_type: str  # relational | arithmetic | boolean


CMP_OPS_MAP: dict[type[ast.cmpop], tuple[str, str, type[ast.cmpop]]] = {
    ast.Eq: ("==", "!=", ast.NotEq),
    ast.NotEq: ("!=", "==", ast.Eq),
    ast.Lt: ("<", "<=", ast.LtE),
    ast.LtE: ("<=", ">", ast.Gt),
    ast.Gt: (">", "<=", ast.LtE),
    ast.GtE: (">=", "<", ast.Lt),
}

BIN_OPS_MAP: dict[type[ast.operator], tuple[str, str, type[ast.operator]]] = {
    ast.Add: ("+", "-", ast.Sub),
    ast.Sub: ("-", "+", ast.Add),
    ast.Mult: ("*", "//", ast.FloorDiv),
    ast.FloorDiv: ("//", "*", ast.Mult),
}


def scan_mutation_points(source_code: str) -> list[MutationPoint]:
    """Scan Python source code and discover potential AST mutation points."""
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return []

    points: list[MutationPoint] = []
    counter = 0

    for node in ast.walk(tree):
        # 1. Compare operations (e.g. x >= 18)
        if isinstance(node, ast.Compare):
            for op in node.ops:
                cmp_op_cls = type(op)
                if cmp_op_cls in CMP_OPS_MAP:
                    orig_sym, mut_sym, _ = CMP_OPS_MAP[cmp_op_cls]
                    line = getattr(node, "lineno", 1)
                    points.append(
                        MutationPoint(
                            node_id=str(counter),
                            line_number=line,
                            original_op=orig_sym,
                            mutated_op=mut_sym,
                            op_type="relational",
                        )
                    )
                    counter += 1

        # 2. Binary operations (e.g. a + b)
        elif isinstance(node, ast.BinOp):
            bin_op_cls = type(node.op)
            if bin_op_cls in BIN_OPS_MAP:
                orig_sym, mut_sym, _ = BIN_OPS_MAP[bin_op_cls]
                line = getattr(node, "lineno", 1)
                points.append(
                    MutationPoint(
                        node_id=str(counter),
                        line_number=line,
                        original_op=orig_sym,
                        mutated_op=mut_sym,
                        op_type="arithmetic",
                    )
                )
                counter += 1

        # 3. Boolean constants (True / False)
        elif isinstance(node, ast.Constant) and isinstance(node.value, bool):
            orig_val = str(node.value)
            mut_val = "False" if node.value is True else "True"
            line = getattr(node, "lineno", 1)
            points.append(
                MutationPoint(
                    node_id=str(counter),
                    line_number=line,
                    original_op=orig_val,
                    mutated_op=mut_val,
                    op_type="boolean",
                )
            )
            counter += 1

    return points


class _SingleNodeMutator(ast.NodeTransformer):
    def __init__(self, target_id: str):
        super().__init__()
        self.target_id = target_id
        self.current_id = 0
        self.applied = False

    def visit_Compare(self, node: ast.Compare) -> Any:
        new_ops: list[ast.cmpop] = []
        for op in node.ops:
            if str(self.current_id) == self.target_id and not self.applied:
                op_cls = type(op)
                if op_cls in CMP_OPS_MAP:
                    _, _, target_cls = CMP_OPS_MAP[op_cls]
                    new_ops.append(target_cls())
                    self.applied = True
                else:
                    new_ops.append(op)
            else:
                new_ops.append(op)
            self.current_id += 1
        node.ops = new_ops
        return self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        if str(self.current_id) == self.target_id and not self.applied:
            op_cls = type(node.op)
            if op_cls in BIN_OPS_MAP:
                _, _, target_cls = BIN_OPS_MAP[op_cls]
                node.op = target_cls()
                self.applied = True
        self.current_id += 1
        return self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> Any:
        if (
            isinstance(node.value, bool)
            and str(self.current_id) == self.target_id
            and not self.applied
        ):
            node.value = not node.value
            self.applied = True
        if isinstance(node.value, bool):
            self.current_id += 1
        return node


def apply_mutation(source_code: str, point: MutationPoint) -> str:
    """Apply a single mutation point to the AST and return the unparsed mutant code."""
    tree = ast.parse(source_code)
    transformer = _SingleNodeMutator(target_id=point.node_id)
    mutated_tree = transformer.visit(copy.deepcopy(tree))
    ast.fix_missing_locations(mutated_tree)
    return ast.unparse(mutated_tree)


class ASTMutationEngine:
    """Executes mutation testing against Python codebases and evaluates test suite quality."""

    def __init__(self, workspace_root: Path | str = "."):
        self.workspace_root = Path(workspace_root).resolve()

    def run_mutation_testing(
        self,
        target_file: Path | str,
        test_file: Path | str | None = None,
        max_mutants: int = 15,
        timeout_seconds: float = 15.0,
    ) -> MutationReport:
        target_path = Path(target_file).resolve()
        if not target_path.exists():
            return MutationReport(
                total_mutants=0,
                killed=0,
                survived=0,
                errors=1,
                mutation_score=0.0,
                mutants=[],
            )

        original_code = target_path.read_text(encoding="utf-8")
        points = scan_mutation_points(original_code)[:max_mutants]

        if not points:
            return MutationReport(
                total_mutants=0,
                killed=0,
                survived=0,
                errors=0,
                mutation_score=100.0,
                mutants=[],
            )

        test_target_arg: str
        if test_file:
            test_target_arg = str(Path(test_file).resolve())
        else:
            test_target_arg = str(self.workspace_root / "tests")

        mutants: list[Mutant] = []
        killed_count = 0
        survived_count = 0
        error_count = 0

        env = os.environ.copy()
        # Ensure target file directory and workspace root are in PYTHONPATH
        target_dir = str(target_path.parent)
        ws_dir = str(self.workspace_root)
        current_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (
            f"{target_dir}{os.pathsep}{ws_dir}{os.pathsep}{current_pythonpath}".strip(os.pathsep)
        )

        try:
            for idx, pt in enumerate(points):
                mutant_id = f"MUT-{idx + 1}"
                try:
                    mutated_code = apply_mutation(original_code, pt)
                    target_path.write_text(mutated_code, encoding="utf-8")

                    # Run pytest on target
                    cmd = [sys.executable, "-m", "pytest", test_target_arg, "-q"]
                    proc = subprocess.run(
                        cmd,
                        check=False,
                        capture_output=True,
                        text=True,
                        cwd=self.workspace_root,
                        timeout=timeout_seconds,
                        env=env,
                    )

                    if proc.returncode != 0:
                        # Tests failed: Mutant was killed!
                        status = "KILLED"
                        killed_count += 1
                    else:
                        # Tests passed: Mutant survived!
                        status = "SURVIVED"
                        survived_count += 1

                    mutants.append(
                        Mutant(
                            id=mutant_id,
                            file_path=str(target_path),
                            line_number=pt.line_number,
                            original_op=pt.original_op,
                            mutated_op=pt.mutated_op,
                            status=status,
                        )
                    )

                except subprocess.TimeoutExpired:
                    # Timeout usually indicates an infinite loop introduced by the mutant -> KILLED
                    status = "KILLED"
                    killed_count += 1
                    mutants.append(
                        Mutant(
                            id=mutant_id,
                            file_path=str(target_path),
                            line_number=pt.line_number,
                            original_op=pt.original_op,
                            mutated_op=pt.mutated_op,
                            status=status,
                        )
                    )
                except Exception:  # noqa: BLE001
                    status = "ERROR"
                    error_count += 1
                    mutants.append(
                        Mutant(
                            id=mutant_id,
                            file_path=str(target_path),
                            line_number=pt.line_number,
                            original_op=pt.original_op,
                            mutated_op=pt.mutated_op,
                            status=status,
                        )
                    )

        finally:
            # Guarantee source code is restored to original state
            target_path.write_text(original_code, encoding="utf-8")

        total = len(mutants)
        score = (killed_count / total * 100.0) if total > 0 else 100.0

        return MutationReport(
            total_mutants=total,
            killed=killed_count,
            survived=survived_count,
            errors=error_count,
            mutation_score=round(score, 2),
            mutants=mutants,
        )
