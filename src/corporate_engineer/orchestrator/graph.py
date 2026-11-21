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

from corporate_engineer.models import (
    AgentState,
    CodeDiff,
    NodeExecutionResult,
    TaskInput,
    TraceReport,
)
from corporate_engineer.telemetry.tracer import AgentTracer


class AutonomousEngineeringGraph:
    def __init__(self, task: TaskInput):
        self.task = task
        self.state = AgentState(task=task)
        self.tracer = AgentTracer(service_name="corporate-engineer")

    def record_iteration(self) -> int:
        self.state.iteration_count += 1
        return self.state.iteration_count

    def is_budget_exceeded(self) -> bool:
        return self.state.iteration_count >= self.task.max_iterations

    def step_plan(self, plan_text: str) -> AgentState:
        with self.tracer.span("dag.node.planning", attributes={"phase": "PLANNING"}):
            self.record_iteration()
            self.state.plan = plan_text
            self.state.phase = "TDD"
            return self.state

    def step_tdd(self, test_file: str) -> AgentState:
        with self.tracer.span("dag.node.tdd", attributes={"phase": "TDD", "test_file": test_file}):
            self.record_iteration()
            if test_file not in self.state.test_files:
                self.state.test_files.append(test_file)
            self.state.phase = "IMPLEMENT"
            return self.state

    def step_implement(
        self, code_file: str, code: str, explanation: str = "Implementation"
    ) -> AgentState:
        with self.tracer.span(
            "dag.node.implement", attributes={"phase": "IMPLEMENT", "code_file": code_file}
        ):
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
        with self.tracer.span(
            "dag.node.audit", attributes={"phase": "AUDIT", "passed": all_passed}
        ):
            self.record_iteration()
            if all_passed:
                self.state.phase = "DELIVER"
                self.state.needs_human_approval = True
            else:
                # Loop back to implement for surgical auto-recovery
                self.state.phase = "IMPLEMENT"
            return self.state

    def execute_step(self) -> AgentState:
        """Advance the graph by one step based on current phase with telemetry tracking."""
        phase = self.state.phase
        if phase == "PLANNING":
            return self.step_plan("Auto-generated implementation plan")
        elif phase == "TDD":
            return self.step_tdd("tests/test_auto.py")
        elif phase == "IMPLEMENT":
            return self.step_implement("src/auto.py", "# auto implementation")
        elif phase == "AUDIT":
            return self.step_audit(True)
        return self.state

    def get_trace_report(self) -> TraceReport:
        """Export OpenTelemetry trace report from the internal tracer."""
        return self.tracer.export_trace()

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
                with self.tracer.span(f"dag.parallel.{name}"):
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

    @classmethod
    def fsm_to_mermaid(cls, highlight_phase: str | None = None) -> str:
        """Export the FSM lifecycle and transitions as a Mermaid flowchart TD diagram."""
        lines = [
            "flowchart TD",
            '    PLANNING["1. PLANNING"] -->|step_plan| TDD["2. TDD"]',
            '    TDD -->|step_tdd| IMPLEMENT["3. IMPLEMENT"]',
            '    IMPLEMENT -->|step_implement| AUDIT["4. AUDIT"]',
            '    AUDIT -->|step_audit(passed=True)| DELIVER["5. DELIVER"]',
            "    AUDIT -->|step_audit(passed=False)| IMPLEMENT",
        ]
        if highlight_phase:
            phase_clean = highlight_phase.upper()
            lines.append(
                f"    style {phase_clean} fill:#10b981,stroke:#059669,stroke-width:2px,color:#ffffff"
            )
        return "\n".join(lines)

    def to_mermaid(self, highlight_current: bool = False) -> str:
        """Export the current graph lifecycle as Mermaid diagram with optional active state highlighting."""
        highlight = self.state.phase if highlight_current else None
        return self.fsm_to_mermaid(highlight_phase=highlight)

    @classmethod
    def checkpoints_to_mermaid(cls, checkpoints: list[dict[str, Any]]) -> str:
        """Export a list of saved checkpoints as a chronological Mermaid flowchart LR timeline."""
        if not checkpoints:
            return 'flowchart LR\n    EMPTY["(Nenhum checkpoint salvo)"]'

        lines = ["flowchart LR"]
        node_ids: list[str] = []
        for idx, cp in enumerate(checkpoints):
            node_id = f"cp_{idx}"
            node_ids.append(node_id)
            ticket = cp.get("ticket_id") or "N/A"
            filename = cp.get("filename") or f"checkpoint_{idx}"
            phase = cp.get("phase") or "UNKNOWN"
            iter_cnt = cp.get("iteration_count", 0)
            label = f"[{ticket}] {filename}<br/>Phase: {phase} | Iter: {iter_cnt}"
            lines.append(f'    {node_id}["{label}"]')

        for i in range(len(node_ids) - 1):
            lines.append(f"    {node_ids[i]} --> {node_ids[i + 1]}")

        return "\n".join(lines)


class ExecutionGraph(AutonomousEngineeringGraph):
    """Grafo de execução com nós dinâmicos e inteligência de decisão do Sistema 1."""

    def __init__(self, task: TaskInput | None = None) -> None:
        actual_task = task or TaskInput(
            ticket_id="TASK-GRAPH-001",
            description="DAG Execution Graph",
            workspace_path=".",
        )
        super().__init__(actual_task)
        self.nodes: dict[str, Callable[[], Any]] = {}
        self.dependencies: dict[str, list[str]] = {}
        self._system_one_router: Any = None

    @property
    def router(self) -> Any:
        if self._system_one_router is None:
            from corporate_engineer.system_one.router import SystemOneRouter

            self._system_one_router = SystemOneRouter()
        return self._system_one_router

    def add_node(
        self,
        name: str,
        fn: Callable[[], Any],
        dependencies: list[str] | None = None,
    ) -> None:
        """Registra um nó no grafo de execução."""
        self.nodes[name] = fn
        self.dependencies[name] = dependencies or []

    def should_skip_node(self, node_name: str, context: str) -> bool:
        """Usa o Sistema 1 para avaliar se o nó pode ser ignorado."""
        decision = self.router.should_skip_node(node_name=node_name, context=context)
        return bool(decision.decision)

    def triage_failure(
        self,
        node_name: str,
        error_message: str,
        traceback_snippet: str = "",
    ) -> Any:
        """Usa o Sistema 1 para classificar a falha e recomendar política de recuperação."""
        return self.router.triage_failure(
            node_name=node_name,
            error_message=error_message,
            traceback_snippet=traceback_snippet,
        )
