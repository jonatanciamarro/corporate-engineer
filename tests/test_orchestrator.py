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
