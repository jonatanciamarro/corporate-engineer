"""
Autonomous Engineering Graph managing deterministic FSM transitions,
checkpointing and Human-in-the-Loop interruptions.
"""

from corporate_engineer.models import AgentState, CodeDiff, TaskInput


class AutonomousEngineeringGraph:
    def __init__(self, task: TaskInput):
        self.task = task
        self.state = AgentState(task=task)

    def record_iteration(self) -> int:
        self.state.iteration_count += 1
        return self.state.iteration_count

    def is_budget_exceeded(self) -> bool:
        return self.state.iteration_count >= self.task.max_iterations

    def step_plan(self, plan_text: str) -> AgentState:
        self.record_iteration()
        self.state.plan = plan_text
        self.state.phase = "TDD"
        return self.state

    def step_tdd(self, test_file: str) -> AgentState:
        self.record_iteration()
        if test_file not in self.state.test_files:
            self.state.test_files.append(test_file)
        self.state.phase = "IMPLEMENT"
        return self.state

    def step_implement(
        self, code_file: str, code: str, explanation: str = "Implementation"
    ) -> AgentState:
        self.record_iteration()
        diff = CodeDiff(
            file_path=code_file,
            new_content=code,
            explanation=explanation,
        )
        self.state.code_changes.append(diff)
        self.state.phase = "AUDIT"
        return self.state

    def step_audit(self, all_passed: bool) -> AgentState:
        self.record_iteration()
        if all_passed:
            self.state.phase = "DELIVER"
            self.state.needs_human_approval = True
        else:
            # Loop back to implement for surgical auto-recovery
            self.state.phase = "IMPLEMENT"
        return self.state
