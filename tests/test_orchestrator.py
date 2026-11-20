from pathlib import Path

from corporate_engineer.models import TaskInput
from corporate_engineer.orchestrator.graph import AutonomousEngineeringGraph


def test_graph_fsm_lifecycle(tmp_path: Path):
    task = TaskInput(
        ticket_id="CORP-200",
        description="Add healthcheck endpoint",
        workspace_path=str(tmp_path),
        max_iterations=5,
    )
    graph = AutonomousEngineeringGraph(task=task)

    # Initial state
    assert graph.state.phase == "PLANNING"
    assert graph.state.iteration_count == 0

    # Step into TDD
    state_after_plan = graph.step_plan("1. Create tests. 2. Create endpoint.")
    assert state_after_plan.phase == "TDD"
    assert state_after_plan.plan is not None

    # Step into Implement
    state_after_tdd = graph.step_tdd(test_file="tests/test_health.py")
    assert state_after_tdd.phase == "IMPLEMENT"
    assert "tests/test_health.py" in state_after_tdd.test_files

    # Step into Audit
    state_after_impl = graph.step_implement(
        code_file="src/health.py", code="def health(): return 200"
    )
    assert state_after_impl.phase == "AUDIT"

    # Step into Deliver / Gate
    state_after_audit = graph.step_audit(all_passed=True)
    assert state_after_audit.phase == "DELIVER"
    assert state_after_audit.needs_human_approval is True


def test_graph_max_iterations_guardrail(tmp_path: Path):
    task = TaskInput(
        ticket_id="CORP-201",
        description="Failing loop test",
        workspace_path=str(tmp_path),
        max_iterations=2,
    )
    graph = AutonomousEngineeringGraph(task=task)

    graph.record_iteration()
    graph.record_iteration()
    assert graph.is_budget_exceeded() is True


def test_graph_checkpoint_save_and_load(tmp_path: Path):
    task = TaskInput(
        ticket_id="CORP-301",
        description="Checkpoint test",
        workspace_path=str(tmp_path),
        max_iterations=10,
    )
    graph = AutonomousEngineeringGraph(task=task)
    graph.step_plan("Plan step executed.")
    graph.step_tdd(test_file="tests/test_feature.py")

    cp_file = tmp_path / "checkpoints" / "cp_test.json"
    saved_path = graph.save_checkpoint(cp_file)
    assert saved_path == cp_file
    assert cp_file.exists()

    # Load restored graph
    restored = AutonomousEngineeringGraph.load_checkpoint(cp_file)
    assert restored.task.ticket_id == "CORP-301"
    assert restored.state.phase == "IMPLEMENT"
    assert restored.state.iteration_count == 2
    assert "tests/test_feature.py" in restored.state.test_files
    assert restored.state.plan == "Plan step executed."


def test_graph_checkpoint_auto_naming_and_list(tmp_path: Path):
    task = TaskInput(
        ticket_id="CORP-302",
        description="Auto naming checkpoint test",
        workspace_path=str(tmp_path),
        max_iterations=10,
    )
    graph = AutonomousEngineeringGraph(task=task)
    graph.step_plan("Phase 1")
    cp1 = graph.save_checkpoint()
    assert cp1.exists()

    graph.step_tdd("tests/test_tdd.py")
    cp2 = graph.save_checkpoint()
    assert cp2.exists()
    assert cp1 != cp2

    checkpoints = AutonomousEngineeringGraph.list_checkpoints(tmp_path)
    assert len(checkpoints) >= 2
    filenames = [c["filename"] for c in checkpoints]
    assert cp1.name in filenames
    assert cp2.name in filenames


def test_graph_rollback(tmp_path: Path):
    task = TaskInput(
        ticket_id="CORP-303",
        description="Rollback test",
        workspace_path=str(tmp_path),
        max_iterations=10,
    )
    graph = AutonomousEngineeringGraph(task=task)
    graph.step_plan("Original plan")
    cp = graph.save_checkpoint()

    # Advance state
    graph.step_tdd("tests/test_foo.py")
    graph.step_implement("src/foo.py", "def foo(): pass")
    assert graph.state.phase == "AUDIT"
    assert graph.state.iteration_count == 3

    # Rollback
    reverted_state = graph.rollback_to_checkpoint(cp)
    assert reverted_state.phase == "TDD"
    assert reverted_state.iteration_count == 1
    assert len(graph.state.code_changes) == 0


def test_graph_parallel_stage_execution(tmp_path: Path):
    import time

    task = TaskInput(
        ticket_id="CORP-304",
        description="Parallel stages test",
        workspace_path=str(tmp_path),
    )
    graph = AutonomousEngineeringGraph(task=task)

    def task_lint():
        time.sleep(0.05)
        return {"linter": "ruff", "violations": 0}

    def task_typecheck():
        time.sleep(0.05)
        return {"typechecker": "mypy", "errors": 0}

    def task_security():
        time.sleep(0.05)
        return {"scanner": "secret_scanner", "leaks": 0}

    tasks = {
        "lint": task_lint,
        "typecheck": task_typecheck,
        "security": task_security,
    }

    start = time.perf_counter()
    results = graph.execute_parallel_tasks(tasks, max_workers=3)
    duration = time.perf_counter() - start

    assert len(results) == 3
    assert results["lint"].success is True
    assert results["lint"].result["violations"] == 0
    assert results["typecheck"].success is True
    assert results["security"].success is True
    assert duration < 0.25


def test_graph_parallel_stage_error_isolation(tmp_path: Path):
    task = TaskInput(
        ticket_id="CORP-305",
        description="Parallel error isolation test",
        workspace_path=str(tmp_path),
    )
    graph = AutonomousEngineeringGraph(task=task)

    def failing_task():
        raise ValueError("Critical lint syntax error")

    def passing_task():
        return "audit_ok"

    tasks = {
        "failing_node": failing_task,
        "passing_node": passing_task,
    }

    results = graph.execute_parallel_tasks(tasks, max_workers=2)
    assert results["failing_node"].success is False
    assert "Critical lint syntax error" in (results["failing_node"].error or "")
    assert results["passing_node"].success is True
    assert results["passing_node"].result == "audit_ok"


def test_graph_fsm_to_mermaid():
    diagram = AutonomousEngineeringGraph.fsm_to_mermaid()
    assert "flowchart TD" in diagram
    assert "PLANNING" in diagram
    assert "TDD" in diagram
    assert "IMPLEMENT" in diagram
    assert "AUDIT" in diagram
    assert "DELIVER" in diagram
    assert "step_plan" in diagram
    assert "step_audit" in diagram


def test_graph_instance_to_mermaid_with_highlight(tmp_path: Path):
    task = TaskInput(
        ticket_id="CORP-306",
        description="Mermaid highlight test",
        workspace_path=str(tmp_path),
    )
    graph = AutonomousEngineeringGraph(task=task)
    graph.step_plan("Plan done")
    assert graph.state.phase == "TDD"

    diagram = graph.to_mermaid(highlight_current=True)
    assert "flowchart TD" in diagram
    assert "TDD" in diagram
    assert "style TDD" in diagram


def test_graph_checkpoints_to_mermaid():
    checkpoints = [
        {
            "filename": "cp_CORP-1_PLANNING_1.json",
            "ticket_id": "CORP-1",
            "phase": "PLANNING",
            "iteration_count": 1,
        },
        {
            "filename": "cp_CORP-1_TDD_2.json",
            "ticket_id": "CORP-1",
            "phase": "TDD",
            "iteration_count": 2,
        },
    ]
    diagram = AutonomousEngineeringGraph.checkpoints_to_mermaid(checkpoints)
    assert "flowchart LR" in diagram
    assert "cp_CORP-1_PLANNING_1" in diagram
    assert "cp_CORP-1_TDD_2" in diagram
    assert "-->" in diagram


def test_graph_checkpoints_to_mermaid_empty():
    diagram = AutonomousEngineeringGraph.checkpoints_to_mermaid([])
    assert "flowchart LR" in diagram
    assert "Nenhum checkpoint" in diagram
