"""
Native AST Mutation Testing Engine for AI-Generated Code (IMP-0006, IMP-0021).

Generates syntactic and semantic mutants via AST transformations and
evaluates test suite robustness against subtle logical regressions.
Guarantees atomic file restoration and safe sandboxed execution.
"""

import ast
import atexit
import contextlib
import copy
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from types import TracebackType
from typing import Any

try:
    from typing_extensions import Self  # noqa: UP035
except ImportError:
    from typing import Self  # type: ignore[attr-defined]

from corporate_engineer.models import Mutant, MutationReport


@dataclass
class MutationPoint:
    node_id: str
    line_number: int
    original_op: str
    mutated_op: str
    op_type: str


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


class _MutationScannerVisitor(ast.NodeVisitor):
    """AST visitor that discovers mutation points with traversal strictly matching _SingleNodeMutator."""

    def __init__(self) -> None:
        super().__init__()
        self.points: list[MutationPoint] = []
        self.current_id = 0

    def visit_Compare(self, node: ast.Compare) -> None:
        self.visit(node.left)
        for op in node.ops:
            op_cls = type(op)
            if op_cls in CMP_OPS_MAP:
                orig_sym, mut_sym, _ = CMP_OPS_MAP[op_cls]
                line = getattr(node, "lineno", 1)
                self.points.append(
                    MutationPoint(
                        node_id=str(self.current_id),
                        line_number=line,
                        original_op=orig_sym,
                        mutated_op=mut_sym,
                        op_type="relational",
                    )
                )
                self.current_id += 1
        for comp in node.comparators:
            self.visit(comp)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        self.visit(node.left)
        op_cls = type(node.op)
        if op_cls in BIN_OPS_MAP:
            orig_sym, mut_sym, _ = BIN_OPS_MAP[op_cls]
            line = getattr(node, "lineno", 1)
            self.points.append(
                MutationPoint(
                    node_id=str(self.current_id),
                    line_number=line,
                    original_op=orig_sym,
                    mutated_op=mut_sym,
                    op_type="arithmetic",
                )
            )
            self.current_id += 1
        self.visit(node.right)

    def visit_Constant(self, node: ast.Constant) -> None:
        if isinstance(node.value, bool):
            orig_val = str(node.value)
            mut_val = "False" if node.value is True else "True"
            line = getattr(node, "lineno", 1)
            self.points.append(
                MutationPoint(
                    node_id=str(self.current_id),
                    line_number=line,
                    original_op=orig_val,
                    mutated_op=mut_val,
                    op_type="boolean",
                )
            )
            self.current_id += 1
        self.generic_visit(node)


def scan_mutation_points(source_code: str) -> list[MutationPoint]:
    """Scan Python source code and discover potential AST mutation points."""
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return []
    scanner = _MutationScannerVisitor()
    scanner.visit(tree)
    return scanner.points


class _SingleNodeMutator(ast.NodeTransformer):
    """AST transformer that mutates a single targeted mutation point by contiguous node_id."""

    def __init__(self, target_id: str) -> None:
        super().__init__()
        self.target_id = target_id
        self.current_id = 0
        self.applied = False

    def visit_Compare(self, node: ast.Compare) -> Any:
        node.left = self.visit(node.left)
        new_ops: list[ast.cmpop] = []
        for op in node.ops:
            op_cls = type(op)
            if op_cls in CMP_OPS_MAP:
                if str(self.current_id) == self.target_id and not self.applied:
                    _, _, target_cls = CMP_OPS_MAP[op_cls]
                    new_ops.append(target_cls())
                    self.applied = True
                else:
                    new_ops.append(op)
                self.current_id += 1
            else:
                new_ops.append(op)
        node.ops = new_ops
        node.comparators = [self.visit(comp) for comp in node.comparators]
        return node

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        node.left = self.visit(node.left)
        op_cls = type(node.op)
        if op_cls in BIN_OPS_MAP:
            if str(self.current_id) == self.target_id and not self.applied:
                _, _, target_cls = BIN_OPS_MAP[op_cls]
                node.op = target_cls()
                self.applied = True
            self.current_id += 1
        node.right = self.visit(node.right)
        return node

    def visit_Constant(self, node: ast.Constant) -> Any:
        if isinstance(node.value, bool):
            if str(self.current_id) == self.target_id and not self.applied:
                node.value = not node.value
                self.applied = True
            self.current_id += 1
        return node


def apply_mutation(source_code: str, point: MutationPoint) -> str:
    """Apply a single mutation point to the AST and return the unparsed mutant code."""
    tree = ast.parse(source_code)
    transformer = _SingleNodeMutator(target_id=point.node_id)
    mutated_tree = transformer.visit(copy.deepcopy(tree))
    ast.fix_missing_locations(mutated_tree)
    return ast.unparse(mutated_tree)


class AtomicFileSandbox:
    """Guarantees atomic file restoration and safe cleanup via backups and signal/atexit handlers."""

    def __init__(self, target_path: Path | str) -> None:
        self.target_path = Path(target_path).resolve()
        self.backup_path = Path(f"{self.target_path}.bak")
        self.original_content: str | None = None
        self._old_sigint: Any = None
        self._old_sigterm: Any = None
        self._restored: bool = False

    def __enter__(self) -> Self:
        self._restored = False
        if self.target_path.exists():
            self.original_content = self.target_path.read_text(encoding="utf-8")
            self.backup_path.write_text(self.original_content, encoding="utf-8")

        atexit.register(self.restore)
        try:
            self._old_sigint = signal.signal(signal.SIGINT, self._handle_signal)
        except (ValueError, AttributeError):
            self._old_sigint = None
        try:
            self._old_sigterm = signal.signal(signal.SIGTERM, self._handle_signal)
        except (ValueError, AttributeError):
            self._old_sigterm = None
        return self

    def restore(self) -> None:
        """Restore target file from original content or backup, and delete backup file."""
        try:
            if self.original_content is not None and self.target_path.exists():
                self.target_path.write_text(self.original_content, encoding="utf-8")
            elif self.backup_path.exists():
                backup_content = self.backup_path.read_text(encoding="utf-8")
                self.target_path.write_text(backup_content, encoding="utf-8")
        finally:
            if self.backup_path.exists():
                try:
                    self.backup_path.unlink()
                except OSError:
                    pass
            self._restored = True

    def _handle_signal(self, signum: int, frame: Any = None) -> None:
        """Handle termination signals by restoring target file and invoking previous handler."""
        self.restore()
        self._reset_signals()
        old_handler = self._old_sigint if signum == signal.SIGINT else self._old_sigterm
        if callable(old_handler) and old_handler not in (signal.SIG_DFL, signal.SIG_IGN):
            old_handler(signum, frame)
        elif signum == signal.SIGINT:
            raise KeyboardInterrupt
        else:
            sys.exit(128 + signum)

    _signal_handler = _handle_signal

    def _reset_signals(self) -> None:
        with contextlib.suppress(TypeError, ValueError, AttributeError):
            atexit.unregister(self.restore)
        try:
            if self._old_sigint is not None:
                signal.signal(signal.SIGINT, self._old_sigint)
                self._old_sigint = None
        except (ValueError, AttributeError):
            pass
        try:
            if self._old_sigterm is not None:
                signal.signal(signal.SIGTERM, self._old_sigterm)
                self._old_sigterm = None
        except (ValueError, AttributeError):
            pass

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        try:
            self.restore()
        finally:
            self._reset_signals()


class ASTMutationEngine:
    """Executes mutation testing against Python codebases and evaluates test suite quality."""

    def __init__(
        self,
        workspace_root: Path | str = ".",
        use_temp_sandbox: bool = False,
    ) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.use_temp_sandbox = use_temp_sandbox

    def run_mutation_testing(
        self,
        target_file: Path | str,
        test_file: Path | str | None = None,
        max_mutants: int = 15,
        timeout_seconds: float = 15.0,
        use_temp_sandbox: bool | None = None,
    ) -> MutationReport:
        effective_temp_sandbox = (
            self.use_temp_sandbox if use_temp_sandbox is None else use_temp_sandbox
        )
        target_path = Path(target_file).resolve()
        if not target_path.exists():
            return MutationReport(
                total_mutants=0, killed=0, survived=0, errors=1, mutation_score=0.0, mutants=[]
            )
        original_code = target_path.read_text(encoding="utf-8")
        points = scan_mutation_points(original_code)[:max_mutants]
        if not points:
            return MutationReport(
                total_mutants=0, killed=0, survived=0, errors=0, mutation_score=100.0, mutants=[]
            )

        if effective_temp_sandbox:
            with tempfile.TemporaryDirectory(prefix="corp_mutation_") as tmp_dir:
                return self._run_in_environment(
                    target_path=target_path,
                    original_code=original_code,
                    points=points,
                    test_file=test_file,
                    timeout_seconds=timeout_seconds,
                    sandbox_dir=Path(tmp_dir).resolve(),
                )

        return self._run_in_environment(
            target_path=target_path,
            original_code=original_code,
            points=points,
            test_file=test_file,
            timeout_seconds=timeout_seconds,
            sandbox_dir=None,
        )

    def _run_in_environment(
        self,
        target_path: Path,
        original_code: str,
        points: list[MutationPoint],
        test_file: Path | str | None,
        timeout_seconds: float,
        sandbox_dir: Path | None,
    ) -> MutationReport:
        ignore_fn = shutil.ignore_patterns(
            "__pycache__",
            ".venv",
            "venv",
            ".git",
            ".tox",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            ".cache",
            "*.pyc",
            "*.bak",
        )
        if sandbox_dir is not None:
            effective_ws = sandbox_dir
            copytree_succeeded = False
            if target_path.is_relative_to(self.workspace_root):
                try:
                    shutil.copytree(
                        self.workspace_root,
                        sandbox_dir,
                        dirs_exist_ok=True,
                        ignore=ignore_fn,
                    )
                    effective_target = sandbox_dir / target_path.relative_to(self.workspace_root)
                    copytree_succeeded = True
                except (OSError, shutil.Error):
                    effective_target = sandbox_dir / target_path.name
                    shutil.copy2(target_path, effective_target)
            else:
                effective_target = sandbox_dir / target_path.name
                shutil.copy2(target_path, effective_target)

            if test_file:
                test_path = Path(test_file).resolve()
                if copytree_succeeded and test_path.is_relative_to(self.workspace_root):
                    effective_test_arg = str(
                        sandbox_dir / test_path.relative_to(self.workspace_root)
                    )
                else:
                    target_in_sandbox = sandbox_dir / test_path.name
                    shutil.copy2(test_path, target_in_sandbox)
                    effective_test_arg = str(target_in_sandbox)
            else:
                if copytree_succeeded and (sandbox_dir / "tests").exists():
                    effective_test_arg = str(sandbox_dir / "tests")
                else:
                    effective_test_arg = str(self.workspace_root / "tests")
        else:
            effective_ws = self.workspace_root
            effective_target = target_path
            if test_file:
                effective_test_arg = str(Path(test_file).resolve())
            else:
                effective_test_arg = str(self.workspace_root / "tests")

        mutants: list[Mutant] = []
        killed_count = 0
        survived_count = 0
        error_count = 0

        env = os.environ.copy()
        candidate_paths: list[str] = []
        src_dir = effective_ws / "src"
        if src_dir.is_dir():
            candidate_paths.append(str(src_dir))
        candidate_paths.append(str(effective_ws))
        in_src_layout = src_dir.is_dir() and effective_target.is_relative_to(src_dir)
        if not in_src_layout and not (effective_target.parent / "__init__.py").exists():
            candidate_paths.append(str(effective_target.parent))
        candidate_paths.extend(env.get("PYTHONPATH", "").split(os.pathsep))

        pythonpath_parts: list[str] = []
        seen_paths: set[str] = set()
        for entry in candidate_paths:
            if entry and entry not in seen_paths:
                seen_paths.add(entry)
                pythonpath_parts.append(entry)

        env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)

        for idx, pt in enumerate(points):
            mutant_id = f"MUT-{idx + 1}"
            try:
                with AtomicFileSandbox(effective_target):
                    mutated_code = apply_mutation(original_code, pt)
                    effective_target.write_text(mutated_code, encoding="utf-8")
                    cmd = [sys.executable, "-m", "pytest", effective_test_arg, "-q"]
                    proc = subprocess.run(
                        cmd,
                        check=False,
                        capture_output=True,
                        text=True,
                        cwd=effective_ws,
                        timeout=timeout_seconds,
                        env=env,
                    )
                    if proc.returncode != 0:
                        status = "KILLED"
                        killed_count += 1
                    else:
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
                        killed_by_test="TimeoutExpired",
                    )
                )
            except Exception as exc:  # noqa: BLE001
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
                        error_message=str(exc),
                    )
                )

        total = len(mutants)
        score = killed_count / total * 100.0 if total > 0 else 100.0
        return MutationReport(
            total_mutants=total,
            killed=killed_count,
            survived=survived_count,
            errors=error_count,
            mutation_score=round(score, 2),
            mutants=mutants,
        )


__all__ = [
    "BIN_OPS_MAP",
    "CMP_OPS_MAP",
    "ASTMutationEngine",
    "AtomicFileSandbox",
    "MutationPoint",
    "_MutationScannerVisitor",
    "_SingleNodeMutator",
    "apply_mutation",
    "scan_mutation_points",
]
