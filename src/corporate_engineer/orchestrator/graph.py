"""
Autonomous Engineering Graph managing deterministic FSM transitions,
checkpointing, rollback recovery and parallel stage execution.
"""

import concurrent.futures
import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from corporate_engineer.models import AgentState, CodeDiff, NodeExecutionResult, TaskInput


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

    def save_checkpoint(self, checkpoint_path: Path | str | None = None) -> Path:
        """Persist current graph state to a JSON checkpoint."""
        if checkpoint_path is None:
            ckpt_dir = Path(self.task.workspace_path) / ".checkpoints"
            ckpt_dir.mkdir(parents=True, exist_ok=True)
            filename = (
                f"cp_{self.task.ticket_id}_{self.state.phase}_{self.state.iteration_count}.json"
            )
            dest = ckpt_dir / filename
        else:
            dest = Path(checkpoint_path)
            dest.parent.mkdir(parents=True, exist_ok=True)

        dest.write_text(self.state.model_dump_json(indent=2), encoding="utf-8")
        return dest

    @classmethod
    def load_checkpoint(cls, checkpoint_path: Path | str) -> "AutonomousEngineeringGraph":
        """Reconstitute an AutonomousEngineeringGraph instance from a saved checkpoint."""
        path = Path(checkpoint_path)
        content = path.read_text(encoding="utf-8")
        state = AgentState.model_validate_json(content)
        graph = cls(task=state.task)
        graph.state = state
        return graph

    def rollback_to_checkpoint(self, checkpoint_path: Path | str) -> AgentState:
        """Revert the graph state to the snapshot stored in the given checkpoint."""
        path = Path(checkpoint_path)
        content = path.read_text(encoding="utf-8")
        self.state = AgentState.model_validate_json(content)
        return self.state

    @classmethod
    def list_checkpoints(cls, workspace_path: Path | str) -> list[dict[str, Any]]:
        """List all checkpoint files in the workspace with metadata."""
        ckpt_dir = Path(workspace_path) / ".checkpoints"
        if not ckpt_dir.exists():
            return []

        checkpoints: list[dict[str, Any]] = []
        for file in sorted(ckpt_dir.glob("*.json")):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                checkpoints.append(
                    {
                        "filename": file.name,
                        "path": str(file.resolve()),
                        "ticket_id": data.get("task", {}).get("ticket_id"),
                        "phase": data.get("phase"),
                        "iteration_count": data.get("iteration_count"),
                        "mtime": file.stat().st_mtime,
                    }
                )
            except (json.JSONDecodeError, OSError):
                checkpoints.append(
                    {
                        "filename": file.name,
                        "path": str(file.resolve()),
                        "mtime": file.stat().st_mtime,
                    }
                )
        return checkpoints

    def execute_parallel_tasks(
        self, tasks: dict[str, Callable[[], Any]], max_workers: int = 4
    ) -> dict[str, NodeExecutionResult]:
        """Execute independent stage tasks in parallel with error isolation and timing metrics."""
        results: dict[str, NodeExecutionResult] = {}

        def _runner(name: str, fn: Callable[[], Any]) -> NodeExecutionResult:
            t0 = time.perf_counter()
            try:
                out = fn()
                t1 = time.perf_counter()
                return NodeExecutionResult(
                    node_name=name,
                    success=True,
                    result=out,
                    duration_seconds=round(t1 - t0, 4),
                )
            except Exception as exc:  # noqa: BLE001
                t1 = time.perf_counter()
                return NodeExecutionResult(
                    node_name=name,
                    success=False,
                    error=str(exc),
                    duration_seconds=round(t1 - t0, 4),
                )

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_name = {
                executor.submit(_runner, name, fn): name for name, fn in tasks.items()
            }
            for future in concurrent.futures.as_completed(future_to_name):
                node_res = future.result()
                results[node_res.node_name] = node_res

        return results
