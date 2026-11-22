"""
Shift-Left TDD Suite for IMP-0021: Atomic Mutation Testing Sandbox.

Tests for:
1. AtomicFileSandbox restoration on exception and signal interruption.
2. Order consistency between AST mutation scanner visitor and node transformer.
3. Mutant model and engine error message capturing.
4. ASTMutationEngine isolated temp sandbox operation.
"""

import ast
import signal
from pathlib import Path
from unittest.mock import patch

import pytest

from corporate_engineer.models import Mutant
from corporate_engineer.quality.mutation import (
    ASTMutationEngine,
    AtomicFileSandbox,
    _MutationScannerVisitor,
    _SingleNodeMutator,
    apply_mutation,
    scan_mutation_points,
)

# ============================================================================
# 1. AtomicFileSandbox Tests: Exception & Normal Flow Restoration
# ============================================================================


def test_atomic_sandbox_restores_on_exception(tmp_path: Path):
    """Test that AtomicFileSandbox restores with 100% fidelity the original file

    on disk if an exception (even abrupt) occurs inside the block.
    """
    target = tmp_path / "critical_module.py"
    original_code = (
        "def compute_discount(price: float) -> float:\n"
        "    if price > 100.0:\n"
        "        return price * 0.9\n"
        "    return price\n"
    )
    target.write_text(original_code, encoding="utf-8")
    bak_path = Path(f"{target}.bak")

    sandbox = AtomicFileSandbox(target)

    with pytest.raises(RuntimeError, match="Sudden execution interruption"), sandbox:
        # Verify backup file was created
        assert bak_path.exists(), "Backup file (.bak) should exist during sandbox execution"
        assert bak_path.read_text(encoding="utf-8") == original_code

        # Mutate target file in place
        target.write_text("CORRUPTED_MUTATED_SYNTAX = None\n", encoding="utf-8")
        assert "CORRUPTED" in target.read_text(encoding="utf-8")

        # Simulate sudden error
        raise RuntimeError("Sudden execution interruption")

    # Invariants after exception:
    # 1. Original file content restored with 100% fidelity
    assert target.exists(), "Target file must exist after exception"
    assert target.read_text(encoding="utf-8") == original_code, (
        "Target file must be restored to original content after exception"
    )
    # 2. Backup file is completely cleaned up
    assert not bak_path.exists(), "Backup file (.bak) must be deleted after exception"


def test_atomic_sandbox_restores_on_normal_exit(tmp_path: Path):
    """Test that AtomicFileSandbox restores original content and cleans up backup

    even on clean, normal exit from the with-block.
    """
    target = tmp_path / "normal_module.py"
    original_code = "VALUE = 42\n"
    target.write_text(original_code, encoding="utf-8")
    bak_path = Path(f"{target}.bak")

    with AtomicFileSandbox(target):
        target.write_text("VALUE = 999\n", encoding="utf-8")
        assert target.read_text(encoding="utf-8") == "VALUE = 999\n"
        assert bak_path.exists()

    assert target.read_text(encoding="utf-8") == original_code
    assert not bak_path.exists()


# ============================================================================
# 2. AtomicFileSandbox Tests: Signal Handling & Interruption Restoration
# ============================================================================


def test_atomic_sandbox_signal_restoration(tmp_path: Path):
    """Test that the signal handler in AtomicFileSandbox restores the original file

    and cleans temporary backups upon receiving termination/interruption signals.
    """
    target = tmp_path / "service_worker.py"
    original_code = "def run_worker():\n    return True\n"
    target.write_text(original_code, encoding="utf-8")
    bak_path = Path(f"{target}.bak")

    sandbox = AtomicFileSandbox(target)

    # Save original signal handlers to verify clean restoration
    prev_sigint = signal.getsignal(signal.SIGINT)
    prev_sigterm = signal.getsignal(signal.SIGTERM)

    try:
        with sandbox:
            # Target file gets mutated
            target.write_text("def run_worker():\n    return False\n", encoding="utf-8")
            assert bak_path.exists()

            # Active signal handler should be registered by sandbox
            current_sigint = signal.getsignal(signal.SIGINT)
            assert current_sigint != prev_sigint, "Sandbox must register custom SIGINT handler"

            # Simulate signal trigger directly on the sandbox handler
            # Calling the registered handler should restore original file and remove .bak
            if hasattr(sandbox, "_handle_signal"):
                try:
                    sandbox._handle_signal(signal.SIGINT, None)
                except (KeyboardInterrupt, SystemExit):
                    pass
            elif callable(current_sigint):
                try:
                    current_sigint(signal.SIGINT, None)
                except (KeyboardInterrupt, SystemExit):
                    pass

            assert target.read_text(encoding="utf-8") == original_code
            assert not bak_path.exists(), "Backup file must be cleaned after signal handling"

    finally:
        # Guarantee signals are not corrupted for test runner
        signal.signal(signal.SIGINT, prev_sigint)
        signal.signal(signal.SIGTERM, prev_sigterm)

    # Invariants after exiting sandbox:
    # Original file restored and signal handlers restored to pre-sandbox state
    assert target.read_text(encoding="utf-8") == original_code
    assert not bak_path.exists()
    assert signal.getsignal(signal.SIGINT) == prev_sigint
    assert signal.getsignal(signal.SIGTERM) == prev_sigterm


# ============================================================================
# 3. Mutation Scanner Visitor & Transformer Order Consistency
# ============================================================================


def test_mutation_scanner_visitor_order_consistency():
    """Test that the mutation points scan follows the exact same traversal order

    as _SingleNodeMutator (using NodeVisitor instead of ast.walk), guaranteeing
    an exact 1:1 mapping of node_id even in deeply nested expressions, list
    comprehensions, and generator expressions.
    """
    code = (
        "def nested_pipeline(items: list[int], flag: bool) -> list[int]:\n"
        "    # Nested list comprehension with arithmetic & relational expressions\n"
        "    filtered = [\n"
        "        (x + 10) * 2\n"
        "        for x in items\n"
        "        if x > 0 and (x <= 100 or x != 50)\n"
        "    ]\n"
        "    # Generator expression with comparisons\n"
        "    gen = (\n"
        "        y // 2\n"
        "        for y in filtered\n"
        "        if y >= 20 and y < 500\n"
        "    )\n"
        "    if flag is True:\n"
        "        return [item - 1 for item in gen if item == 42]\n"
        "    return [0 + 0]\n"
    )

    points = scan_mutation_points(code)
    assert len(points) >= 10, f"Expected at least 10 mutation points, got {len(points)}"

    # Ensure node_ids are strictly contiguous integers "0", "1", "2", ...
    expected_ids = [str(i) for i in range(len(points))]
    actual_ids = [p.node_id for p in points]
    assert actual_ids == expected_ids, (
        f"Node IDs must follow strict contiguous ordering: {actual_ids}"
    )

    # For each detected mutation point, verify that _SingleNodeMutator visits and
    # applies the mutation to the EXACT intended node_id without misalignment.
    for pt in points:
        tree = ast.parse(code)
        mutator = _SingleNodeMutator(target_id=pt.node_id)
        mutated_tree = mutator.visit(tree)
        ast.fix_missing_locations(mutated_tree)

        # 1. Mutator must have successfully applied the mutation
        assert mutator.applied is True, (
            f"Mutator failed to apply mutation for point node_id={pt.node_id} "
            f"({pt.original_op} -> {pt.mutated_op} on line {pt.line_number})"
        )

        # 2. Mutated AST unparses to valid Python code
        mutated_code = ast.unparse(mutated_tree)
        reparsed = ast.parse(mutated_code)
        assert reparsed is not None, f"Mutant for node_id={pt.node_id} produced invalid syntax"

        # 3. apply_mutation wrapper produces identical code
        wrapped_code = apply_mutation(code, pt)
        assert wrapped_code == mutated_code


def test_mutation_scanner_visitor_explicit_class():
    """Verify that _MutationScannerVisitor is implemented as an ast.NodeVisitor

    mirroring the traversal structure of _SingleNodeMutator.
    """
    assert issubclass(_MutationScannerVisitor, ast.NodeVisitor), (
        "_MutationScannerVisitor must inherit from ast.NodeVisitor for deterministic order"
    )

    source = "def calc(a, b): return (a + b) > 10\n"
    tree = ast.parse(source)
    scanner = _MutationScannerVisitor()
    scanner.visit(tree)

    assert hasattr(scanner, "points"), "_MutationScannerVisitor must collect points attribute"
    assert len(scanner.points) == 2  # (+) and (>)


# ============================================================================
# 4. Mutant Error Message Capturing
# ============================================================================


def test_mutant_captures_error_message():
    """Test that the Mutant model and ASTMutationEngine record detailed error_message

    in case of mutation/subprocess error instead of silently swallowing the exception.
    """
    # 1. Verify model contract
    mutant = Mutant(
        id="MUT-99",
        file_path="src/calc.py",
        line_number=42,
        original_op="+",
        mutated_op="-",
        status="ERROR",
        error_message="Subprocess crashed: MemoryError: unable to allocate array",
    )
    assert mutant.error_message == "Subprocess crashed: MemoryError: unable to allocate array"
    dumped = mutant.model_dump()
    assert dumped["error_message"] == "Subprocess crashed: MemoryError: unable to allocate array"

    # Default should be None for normal mutants
    normal_mutant = Mutant(
        id="MUT-1",
        file_path="src/calc.py",
        line_number=10,
        original_op="==",
        mutated_op="!=",
        status="KILLED",
    )
    assert normal_mutant.error_message is None


def test_mutation_engine_captures_subprocess_error(tmp_path: Path):
    """Test that ASTMutationEngine.run_mutation_testing captures the actual exception

    message in mutant.error_message when an exception occurs during test execution.
    """
    src_file = tmp_path / "calculator.py"
    src_file.write_text("def mul(a, b):\n    return a * b\n", encoding="utf-8")
    test_file = tmp_path / "test_calculator.py"
    test_file.write_text("def test_mul(): pass\n", encoding="utf-8")

    engine = ASTMutationEngine(workspace_root=tmp_path)

    # Simulate subprocess error during test execution
    with patch(
        "subprocess.run",
        side_effect=RuntimeError("Subprocess failed: internal permission denied [Errno 13]"),
    ):
        report = engine.run_mutation_testing(
            target_file=src_file,
            test_file=test_file,
            max_mutants=1,
        )

    assert report.total_mutants == 1
    assert report.errors == 1
    assert len(report.mutants) == 1
    mutant = report.mutants[0]
    assert mutant.status == "ERROR"
    assert mutant.error_message is not None
    assert "Subprocess failed: internal permission denied" in mutant.error_message


# ============================================================================
# 5. ASTMutationEngine Isolated Temp Sandbox
# ============================================================================


def test_mutation_engine_with_temp_sandbox(tmp_path: Path):
    """Test ASTMutationEngine operating in isolated temporary sandbox mode

    (use_temp_sandbox=True) without altering the working file on disk at any point.
    """
    src_file = tmp_path / "pure_module.py"
    original_code = "def is_positive(x: int) -> bool:\n    return x > 0\n"
    src_file.write_text(original_code, encoding="utf-8")

    test_file = tmp_path / "test_pure_module.py"
    test_file.write_text(
        "from pure_module import is_positive\n\n"
        "def test_positive():\n"
        "    assert is_positive(10) is True\n"
        "    assert is_positive(-5) is False\n",
        encoding="utf-8",
    )

    # Initialize engine with use_temp_sandbox or pass to run_mutation_testing
    engine = ASTMutationEngine(workspace_root=tmp_path)

    # Track mtime and content before execution
    initial_mtime = src_file.stat().st_mtime
    initial_content = src_file.read_text(encoding="utf-8")

    report = engine.run_mutation_testing(
        target_file=src_file,
        test_file=test_file,
        max_mutants=3,
        use_temp_sandbox=True,
    )

    # Invariants for temp sandbox:
    # 1. Mutation testing executed and killed mutants
    assert report.total_mutants >= 1
    assert report.killed >= 1

    # 2. The original working file on disk was NEVER modified
    assert src_file.read_text(encoding="utf-8") == initial_content
    assert src_file.stat().st_mtime == initial_mtime

    # 3. No leftover temporary directories or .bak files
    bak_files = list(tmp_path.glob("*.bak"))
    assert len(bak_files) == 0


def test_mutation_engine_temp_sandbox_init_flag(tmp_path: Path):
    """Test ASTMutationEngine accepts use_temp_sandbox in __init__."""
    engine = ASTMutationEngine(workspace_root=tmp_path, use_temp_sandbox=True)
    assert getattr(engine, "use_temp_sandbox", False) is True
