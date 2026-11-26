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
    RevisedPromptSpec,
    RunExecutionReport,
    TaskInput,
    TraceReport,
)
from corporate_engineer.telemetry.tracer import AgentTracer


class AutonomousEngineeringGraph:
    def __init__(self, task: TaskInput) -> None:
        self.task = task
        self.state = AgentState(task=task)
        self.tracer = AgentTracer(service_name="corporate-engineer")
        from corporate_engineer.quality.gate import QualityGateRunner

        self.quality_runner = QualityGateRunner(project_root=self.workspace_path)

    @property
    def workspace_path(self) -> Path:
        return Path(self.task.workspace_path)

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
        self,
        code_file: str,
        code: str,
        explanation: str = "Implementation",
        original_content: str | None = None,
    ) -> AgentState:
        with self.tracer.span(
            "dag.node.implement", attributes={"phase": "IMPLEMENT", "code_file": code_file}
        ):
            self.record_iteration()
            diff = CodeDiff(
                file_path=code_file,
                original_content=original_content,
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

    def _run_implement_phase(
        self,
        code_target: str,
        spec: RevisedPromptSpec,
        dry_run: bool,
        code_executor: Callable[[str, RevisedPromptSpec], list[CodeDiff] | str] | None,
        details: dict[str, Any],
    ) -> None:
        """Execute Phase 3 (IMPLEMENT) via custom code_executor or deterministic AST pipeline."""
        from corporate_engineer.eval.fixer import ASTSelfHealingFixer

        fixer = ASTSelfHealingFixer()
        src_dir = self.workspace_path / "src"
        if src_dir.exists():
            fix_report = fixer.fix_workspace(src_dir, dry_run=dry_run)
            details["ast_fix_report"] = fix_report.model_dump()
        else:
            target_file = self.workspace_path / code_target
            if target_file.exists():
                fix_report = fixer.fix_file(target_file, dry_run=dry_run)
                details["ast_fix_report"] = fix_report.model_dump()

        if code_executor is not None:
            executor_result = code_executor(code_target, spec)
            if isinstance(executor_result, list):
                if not executor_result:
                    self.step_implement(
                        code_target,
                        f"# Custom code executor returned 0 diffs for {self.task.ticket_id}",
                        explanation=(
                            f"Custom code executor execution for {self.task.ticket_id} (no diffs)"
                        ),
                    )
                else:
                    for diff in executor_result:
                        self.step_implement(
                            diff.file_path,
                            diff.new_content,
                            explanation=diff.explanation,
                            original_content=diff.original_content,
                        )
            elif isinstance(executor_result, CodeDiff):
                self.step_implement(
                    executor_result.file_path,
                    executor_result.new_content,
                    explanation=executor_result.explanation,
                    original_content=executor_result.original_content,
                )
            else:
                self.step_implement(
                    code_target,
                    str(executor_result),
                    explanation=f"Custom code executor output for {self.task.ticket_id}",
                )
            return

        ast_fixes_count = details.get("ast_fix_report", {}).get("files_modified", 0)
        code_desc = (
            f"# Deterministic pipeline pass (ASTSelfHealingFixer, dry_run={dry_run}, "
            f"files_modified={ast_fixes_count}) for {self.task.ticket_id}\n"
            f"# Intent: {spec.core_intent}"
        )
        self.step_implement(
            code_target,
            code_desc,
            explanation=(
                f"Passagem determinística de pipeline (ASTSelfHealingFixer) para {self.task.ticket_id}"
            ),
        )

    def run_pipeline(
        self,
        dry_run: bool = False,
        auto_deliver: bool = True,
        strict_audit: bool = True,
        code_executor: Callable[[str, RevisedPromptSpec], list[CodeDiff] | str] | None = None,
    ) -> RunExecutionReport:
        """Executa o ciclo de vida completo de engenharia corporativa autônoma:

        PLANNING -> TDD -> IMPLEMENT -> AUDIT -> DELIVER com geração de checkpoints e telemetria.
        """
        t0 = time.perf_counter()
        checkpoints_created: list[str] = []
        execution_mode = (
            "custom-code-executor" if code_executor is not None else "deterministic-pipeline"
        )
        details: dict[str, Any] = {"execution_mode": execution_mode}

        with self.tracer.span(
            "dag.lifecycle.pipeline",
            attributes={
                "ticket_id": self.task.ticket_id,
                "dry_run": dry_run,
                "execution_mode": execution_mode,
            },
        ):
            # Fase 1: Planejamento & Antecipação Proativa
            from corporate_engineer.orchestrator.anticipator import ProactiveAnticipator

            anticipator = ProactiveAnticipator(workspace_path=self.workspace_path)
            anticipation_plan = anticipator.anticipate(self.task.description)
            spec = anticipator.refiner.refine(self.task.description, bypass_gate=False)

            plan_dict = anticipation_plan.model_dump()
            plan_dict["step_1"] = plan_dict.get("step_immediate_1")
            plan_dict["step_2"] = plan_dict.get("step_subsequent_2")
            details["anticipation_plan"] = plan_dict

            plan_text = (
                anticipation_plan.structured_metaprompt
                if anticipation_plan.structured_metaprompt
                else (
                    spec.metaprompt
                    if spec.metaprompt
                    else f"Plano de Engenharia para {self.task.ticket_id}"
                )
            )

            # Loop Dialético Tri-Fásico (Fases 1.5 -> 1.6 -> 1.7 - IMP-0026 / ADR-028)
            from corporate_engineer.orchestrator.adversarial import AdversarialLoopCoordinator

            dialectical_coord = AdversarialLoopCoordinator()
            dialectical_res = dialectical_coord.run_dialectical_loop(
                plan_id=self.task.ticket_id,
                plan_text=plan_text,
                risk_level=getattr(anticipation_plan, "risk_level", "MEDIUM"),
            )
            details["adversarial_verdict"] = dialectical_res.verdict.status.value
            details["chaos_matrix"] = [c.model_dump() for c in dialectical_res.verdict.chaos_matrix]
            details["dialectical_result"] = dialectical_res.model_dump()

            self.step_plan(plan_text)
            cp1 = self.save_checkpoint()
            checkpoints_created.append(cp1.name)

            # Fase 2: Shift-Left TDD com Surgical Test Runner
            from corporate_engineer.quality.surgical_runner import SurgicalTestRunner

            surgical_runner = SurgicalTestRunner(root_path=self.workspace_path)
            changed_files = surgical_runner.collect_changed_files()
            affected_tests = surgical_runner.resolve_affected_tests(changed_files)
            details["surgical_test"] = {
                "changed_files": changed_files,
                "affected_tests": affected_tests,
            }

            if affected_tests:
                test_target = affected_tests[0]
            elif spec.tdd_test_scenarios:
                test_target = spec.tdd_test_scenarios[0]
            else:
                test_target = f"tests/test_{self.task.ticket_id.lower().replace('-', '_')}.py"

            self.step_tdd(test_target)
            if affected_tests:
                for t in affected_tests:
                    if t not in self.state.test_files:
                        self.state.test_files.append(t)
            cp2 = self.save_checkpoint()
            checkpoints_created.append(cp2.name)

            # Fase 3: Implementação Cirúrgica (Executor Plugável ou Pipeline AST Determinístico)
            code_target = (
                spec.affected_modules[0]
                if spec.affected_modules
                else f"src/{self.task.ticket_id.lower().replace('-', '_')}.py"
            )
            self._run_implement_phase(
                code_target=code_target,
                spec=spec,
                dry_run=dry_run,
                code_executor=code_executor,
                details=details,
            )

            cp3 = self.save_checkpoint()
            checkpoints_created.append(cp3.name)

            # Fase 4: Portão de Qualidade & Auditoria Estrita
            from corporate_engineer.eval.scorecard import SemanticCodeEvaluator

            secret_scan = self.quality_runner.run_secret_scan()
            details["secret_scan"] = secret_scan
            audit_passed = bool(secret_scan.get("passed", False))

            wiring_audit = self.quality_runner.run_wiring_audit()
            details["wiring_audit"] = wiring_audit
            if strict_audit and not wiring_audit.get("passed", False):
                audit_passed = False

            test_run_details: dict[str, Any] = {}
            if strict_audit and audit_passed:
                test_res = self.quality_runner.run_tests()
                test_run_details = test_res
                audit_passed = bool(test_res.get("passed", False))
            details["test_run"] = test_run_details

            evaluator = SemanticCodeEvaluator(workspace_root=self.workspace_path)
            eval_report = evaluator.evaluate()
            details["semantic_evaluation"] = eval_report.model_dump()
            if strict_audit and not eval_report.passed_gate:
                audit_passed = False

            self.step_audit(audit_passed)
            cp4 = self.save_checkpoint()
            checkpoints_created.append(cp4.name)

            t1 = time.perf_counter()
            duration = round(t1 - t0, 4)

            if not audit_passed:
                return RunExecutionReport(
                    ticket_id=self.task.ticket_id,
                    task_description=self.task.description,
                    status="AUDIT_FAILED",
                    final_phase=self.state.phase,
                    iterations=self.state.iteration_count,
                    checkpoints_created=checkpoints_created,
                    refined_plan=self.state.plan,
                    test_files=self.state.test_files,
                    code_changes_count=len(self.state.code_changes),
                    audit_passed=False,
                    duration_seconds=duration,
                    dry_run=dry_run,
                    details=details,
                )

            # Fase 5: Entrega (DELIVER)
            if auto_deliver:
                self.state.needs_human_approval = False

            import corporate_engineer.git_utils

            try:
                pr_result = corporate_engineer.git_utils.generate_pr_url(
                    repo_path=self.workspace_path,
                    ensure_pushed=False,
                )
                if isinstance(pr_result, dict):
                    pr_url = (
                        pr_result.get("url")
                        or f"https://github.com/org/repo/compare/main...{self.task.ticket_id}?quick_pull=1"
                    )
                else:
                    pr_url = str(pr_result)
            except Exception:  # noqa: BLE001
                pr_url = (
                    f"https://github.com/org/repo/compare/main...{self.task.ticket_id}?quick_pull=1"
                )

            details["pr_url"] = pr_url

            return RunExecutionReport(
                ticket_id=self.task.ticket_id,
                task_description=self.task.description,
                status="SUCCESS",
                final_phase="DELIVER",
                iterations=self.state.iteration_count,
                checkpoints_created=checkpoints_created,
                refined_plan=self.state.plan,
                test_files=self.state.test_files,
                code_changes_count=len(self.state.code_changes),
                audit_passed=True,
                duration_seconds=duration,
                dry_run=dry_run,
                details=details,
            )

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
                    node_name=name, success=True, result=out, duration_seconds=round(t1 - t0, 4)
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
            ticket_id="TASK-GRAPH-001", description="DAG Execution Graph", workspace_path="."
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
        self, name: str, fn: Callable[[], Any], dependencies: list[str] | None = None
    ) -> None:
        """Registra um nó no grafo de execução."""
        self.nodes[name] = fn
        self.dependencies[name] = dependencies or []

    def should_skip_node(self, node_name: str, context: str) -> bool:
        """Usa o Sistema 1 para avaliar se o nó pode ser ignorado."""
        decision = self.router.should_skip_node(node_name=node_name, context=context)
        return bool(decision.decision)

    def triage_failure(
        self, node_name: str, error_message: str, traceback_snippet: str = ""
    ) -> Any:
        """Usa o Sistema 1 para classificar a falha e recomendar política de recuperação."""
        return self.router.triage_failure(
            node_name=node_name, error_message=error_message, traceback_snippet=traceback_snippet
        )
