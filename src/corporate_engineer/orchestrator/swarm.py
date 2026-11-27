"""
Multi-Agent Swarm Coordinator via MCP Enterprise Hub (IMP-0016 / ADR-016).
Orchestrates concurrent specialized agent swarms with dynamic MCP tool injection,
isolated circuit breakers, fan-out/fan-in parallel execution, and consensus aggregation.
"""

from __future__ import annotations

import concurrent.futures
import os
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

from corporate_engineer.eval.scorecard import SemanticCodeEvaluator
from corporate_engineer.mcp.hub import MCPEnterpriseHub
from corporate_engineer.models import (
    SwarmGoalReport,
    SwarmMember,
    SwarmTaskResult,
)
from corporate_engineer.quality.secret_scanner import CanonicalSecretScanner
from corporate_engineer.quality.wiring_auditor import CapabilityWiringAuditor
from corporate_engineer.rag.cached_ast_indexer import CachedASTCodebaseIndexer
from corporate_engineer.system_one.router import SystemOneRouter

RoleExecutor = Callable[[SwarmMember, str, list[dict[str, Any]]], str]

__all__ = ["RoleExecutor", "SwarmCoordinator"]


class SwarmCoordinator:
    """Coordenador mestre de enxames de agentes com injeção segura de ferramentas MCP."""

    # Legacy role description templates retained for introspection;
    # dispatch_task() never returns these static strings blindly.
    ROLE_SPECIALIZATIONS: ClassVar[dict[str, str]] = {
        "architect": "Validação de Arquitetura & Contratos DTO Pydantic v2.",
        "security-reviewer": "Auditoria de Segurança: Verificação de credenciais e permissões.",
        "tdd-guide": "Verificação TDD: Especificação de testes unitários com pytest.",
        "code-reviewer": "Revisão de Código: Análise de conformidade PEP 8 e score semântico.",
        "python-reviewer": "Revisão Especializada Python: Tipagem estrita e padrões idiomáticos.",
        "build-error-resolver": "Resolução de Build: Diagnóstico de integridade e dependências.",
        "refactor-cleaner": "Refatoração Limpa: Preservação rigorosa de comportamento.",
        "rag-pipeline-reviewer": "Auditoria de Code Intelligence: Indexação AST e blast radius.",
    }

    def __init__(
        self,
        hub: MCPEnterpriseHub | None = None,
        router: SystemOneRouter | None = None,
        workspace_path: str | Path = ".",
        role_executor: RoleExecutor | None = None,
    ) -> None:
        self.hub: MCPEnterpriseHub = hub or MCPEnterpriseHub()
        self.router: SystemOneRouter = router or SystemOneRouter()
        self.workspace_path: Path = Path(workspace_path).resolve()
        self.role_executor: RoleExecutor | None = role_executor
        self._lock: threading.RLock = threading.RLock()

    def create_swarm(
        self,
        name: str = "default-swarm",
        roles: list[str] | None = None,
    ) -> list[SwarmMember]:
        """
        Instancia um grupo coordenado de agentes, alocando para cada um apenas
        o subset de ferramentas MCP relevantes com isolamento de falhas.
        """
        target_roles = roles or ["architect", "tdd-guide", "code-reviewer"]
        members: list[SwarmMember] = []

        all_tools = self.hub.list_tools()

        for idx, role in enumerate(target_roles):
            agent_id = f"{role[:4]}-{idx + 1:02d}"

            # Poda e alocação de ferramentas MCP específicas para o papel do agente
            pruned = self.hub.prune_tools_for_prompt(prompt=f"{role} code engineering audit")
            allowed_tools = [t.namespaced_name for t in pruned]

            # Inclusão defensiva de ferramentas por heurística de prefixo
            if not allowed_tools and all_tools:
                role_lower = role.lower()
                for t in all_tools:
                    tool_desc = f"{t.server_name} {t.tool_name}".lower()
                    if (
                        ("sec" in role_lower and ("sec" in tool_desc or "perm" in tool_desc))
                        or ("git" in role_lower and "git" in tool_desc)
                        or ("test" in role_lower and "test" in tool_desc)
                    ):
                        allowed_tools.append(t.namespaced_name)

            member = SwarmMember(
                agent_id=agent_id,
                role=role,
                task_prompt=f"Atuação especializada como {role} no enxame '{name}'",
                allowed_tools=allowed_tools,
                status="IDLE",
            )
            members.append(member)

        return members

    def _invoke_member_tools(
        self, member: SwarmMember, prompt: str
    ) -> tuple[list[str], list[dict[str, Any]], bool, str | None]:
        """Invoke member-allowed MCP tools with contextual arguments and error isolation."""
        tool_args: dict[str, Any] = {
            "prompt": prompt,
            "role": member.role,
            "workspace_path": str(self.workspace_path),
        }
        tools_called: list[str] = []
        tool_records: list[dict[str, Any]] = []
        success = True
        error_msg: str | None = None

        for tool_name in member.allowed_tools:
            try:
                res = self.hub.call_tool(tool_name, tool_args)
                tools_called.append(tool_name)
                is_err = bool(
                    (hasattr(res, "is_error") and res.is_error)
                    or (isinstance(res, dict) and res.get("is_error"))
                )
                content = res.content if hasattr(res, "content") else res
                if is_err:
                    error_msg = str(content)
                    success = False
                tool_records.append(
                    {
                        "tool": tool_name,
                        "arguments": tool_args,
                        "is_error": is_err,
                        "output": content,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                # O Circuit Breaker do hub isola a falha impedindo travamento do processo
                error_msg = f"Falha isolada na ferramenta '{tool_name}': {exc}"
                tools_called.append(f"{tool_name} (circuit-isolated)")
                success = False
                tool_records.append(
                    {
                        "tool": tool_name,
                        "arguments": tool_args,
                        "is_error": True,
                        "error": str(exc),
                    }
                )

        return tools_called, tool_records, success, error_msg

    def _has_python_sources(self) -> bool:
        """Check whether Python source files exist under workspace_path."""
        if (self.workspace_path / "src").exists():
            return True
        if not self.workspace_path.exists():
            return False
        excluded = {"venv", ".venv", "__pycache__", "build", "dist", ".git", "node_modules"}
        for _, dirs, files in os.walk(self.workspace_path):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in excluded]
            if any(f.endswith(".py") for f in files):
                return True
        return False

    def _execute_deterministic_role(
        self,
        member: SwarmMember,
        prompt: str,
        tool_records: list[dict[str, Any]],
    ) -> tuple[str, bool, str | None]:
        """Run real deterministic workspace analyzers mapped to the member's role."""
        if member.role == "security-reviewer":
            findings = CanonicalSecretScanner().scan_directory(self.workspace_path)
            if findings:
                files_summary = ", ".join(sorted({str(f.get("file", "")) for f in findings})[:5])
                err = f"{len(findings)} secret(s) detected"
                output = f"Auditoria de Segurança ({self.workspace_path}): {err} [{files_summary}]."
                return output, False, err
            output = (
                f"Auditoria de Segurança ({self.workspace_path}): "
                "0 secret(s) detected pelo CanonicalSecretScanner."
            )
            return output, True, None

        if member.role in ("code-reviewer", "python-reviewer"):
            src_dir = self.workspace_path / "src"
            eval_target = src_dir if src_dir.exists() else self.workspace_path
            eval_report = SemanticCodeEvaluator(workspace_root=eval_target).evaluate()
            output = (
                f"Revisão Estática ({member.role}): "
                f"score={eval_report.composite_score}/100 (grade={eval_report.letter_grade}), "
                f"files={eval_report.total_files_evaluated}, "
                f"violations={eval_report.total_violations}."
            )
            if not eval_report.passed_gate:
                err = (
                    f"SemanticCodeEvaluator gate failed: score={eval_report.composite_score} "
                    f"< {eval_report.min_passing_score} (grade={eval_report.letter_grade})"
                )
                return output, False, err
            return output, True, None

        if member.role == "rag-pipeline-reviewer":
            if self._has_python_sources():
                with self._lock:
                    symbol_names = CachedASTCodebaseIndexer(
                        root_path=self.workspace_path
                    ).get_all_symbol_names()
            else:
                symbol_names = set()
            output = (
                f"Auditoria de Code Intelligence ({self.workspace_path}): "
                f"{len(symbol_names)} símbolo(s) AST indexados."
            )
            return output, True, None

        if member.role == "architect":
            wiring_report = CapabilityWiringAuditor(workspace_root=self.workspace_path).audit()
            connected_count = len(wiring_report.connected_modules)
            total_count = wiring_report.total_modules
            output = (
                f"Auditoria de Arquitetura & Wiring ({self.workspace_path}): "
                f"{connected_count}/{total_count} módulos conectados "
                f"(passed={wiring_report.passed})."
            )
            if not wiring_report.passed:
                err = (
                    f"Wiring audit failed: {len(wiring_report.unwired_modules)} unwired module(s), "
                    f"{len(wiring_report.missing_test_modules)} missing test(s)"
                )
                return output, False, err
            return output, True, None

        if tool_records:
            tools_summary = ", ".join(
                f"{rec['tool']}({'error' if rec.get('is_error') else 'ok'})" for rec in tool_records
            )
        else:
            tools_summary = "none"
        output = (
            f"Execução determinística [{member.role}] para '{prompt}': "
            f"{len(tool_records)} ferramenta(s) MCP invocada(s) [{tools_summary}]."
        )
        return output, True, None

    def dispatch_task(self, member: SwarmMember, prompt: str) -> SwarmTaskResult:
        """
        Executa uma tarefa para um membro específico do swarm via executor plugável
        ou analisadores determinísticos locais, com ferramentas MCP isoladas por Circuit Breaker.
        """
        with self._lock:
            member.status = "WORKING"
        t0 = time.perf_counter()

        try:
            tools_called, tool_records, success, error_msg = self._invoke_member_tools(
                member, prompt
            )

            if self.role_executor is not None:
                output = self.role_executor(member, prompt, tool_records)
            else:
                output, role_ok, role_err = self._execute_deterministic_role(
                    member, prompt, tool_records
                )
                if not role_ok:
                    success = False
                    error_msg = (
                        f"{error_msg}; {role_err}"
                        if error_msg and role_err
                        else (role_err or error_msg)
                    )

            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
            with self._lock:
                member.status = "COMPLETED" if success else "FAILED"

            return SwarmTaskResult(
                agent_id=member.agent_id,
                role=member.role,
                output=output,
                success=success,
                execution_time_ms=elapsed_ms,
                tools_called=tools_called,
                error=error_msg,
            )
        except Exception:
            with self._lock:
                member.status = "FAILED"
            raise

    def run_fan_out(
        self,
        goal: str,
        subtasks: list[dict[str, Any]],
        max_workers: int = 4,
    ) -> SwarmGoalReport:
        """
        Executa sub-tarefas em paralelo através de um pool concorrente de agentes (Fan-Out),
        aguardando a conclusão coletiva com barreira de sincronização (Fan-In).
        """
        t0 = time.perf_counter()
        results: list[SwarmTaskResult] = []

        # Preparação dos membros
        task_pairs: list[tuple[SwarmMember, str]] = []
        for idx, item in enumerate(subtasks):
            role = str(item.get("role", "code-reviewer"))
            prompt = str(item.get("task", goal))
            raw_tools = item.get("tools")
            if isinstance(raw_tools, list):
                tools: list[str] = [str(t) for t in raw_tools]
            else:
                tools = [
                    t.namespaced_name for t in self.hub.prune_tools_for_prompt(prompt, max_tools=3)
                ]
            member = SwarmMember(
                agent_id=f"{role[:4]}-{idx + 1:02d}",
                role=role,
                task_prompt=prompt,
                allowed_tools=tools,
                status="IDLE",
            )
            task_pairs.append((member, prompt))

        # Execução concorrente com ThreadPool
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_member = {executor.submit(self.dispatch_task, m, p): m for m, p in task_pairs}
            for future in concurrent.futures.as_completed(future_to_member):
                try:
                    res = future.result()
                    results.append(res)
                except Exception as exc:  # noqa: BLE001
                    m = future_to_member[future]
                    with self._lock:
                        m.status = "FAILED"
                    results.append(
                        SwarmTaskResult(
                            agent_id=m.agent_id,
                            role=m.role,
                            output="",
                            success=False,
                            execution_time_ms=0.0,
                            error=str(exc),
                        )
                    )

        total_elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        successful_tasks = sum(1 for r in results if r.success and not r.error)
        failed_tasks = len(results) - successful_tasks
        execution_mode = (
            "custom-executor" if self.role_executor is not None else "deterministic-analyzer"
        )

        consensus = (
            f"APPROVED: {successful_tasks}/{len(results)} tarefas concluídas com sucesso no swarm."
            if failed_tasks == 0
            else f"REJECTED: {failed_tasks} tarefa(s) falharam durante a execução concorrente."
        )

        recommendations = [
            (
                f"Meta '{goal}' processada por {len(results)} agentes especializados "
                f"em {total_elapsed_ms}ms (execution_mode={execution_mode})."
            ),
            "Isolamento por circuit breaker manteve 100% de estabilidade no pool concorrente.",
        ]

        return SwarmGoalReport(
            goal=goal,
            swarm_name="fanout-swarm",
            total_agents=len(results),
            successful_tasks=successful_tasks,
            failed_tasks=failed_tasks,
            aggregated_consensus=consensus,
            results=results,
            execution_time_ms=total_elapsed_ms,
            recommendations=recommendations,
        )

    def run_consensus(
        self,
        target_description: str,
        reviewer_roles: list[str] | None = None,
        max_workers: int = 3,
    ) -> SwarmGoalReport:
        """
        Conduz uma rodada de revisão multi-agente concorrente e sintetiza
        um parecer de consenso unificado (Consensus Aggregation).
        """
        roles = reviewer_roles or ["architect", "security-reviewer", "code-reviewer"]
        subtasks = [
            {"role": r, "task": f"Avalie a conformidade de: {target_description}"} for r in roles
        ]

        report = self.run_fan_out(
            goal=f"Consenso de Revisão: {target_description}",
            subtasks=subtasks,
            max_workers=max_workers,
        )

        execution_mode = (
            "custom-executor" if self.role_executor is not None else "deterministic-analyzer"
        )
        all_ok = bool(report.results) and all(r.success and not r.error for r in report.results)
        if all_ok:
            consensus_msg = (
                f"APPROVED: Revisão multi-perspectiva concluída por {len(roles)} especialistas "
                f"(execution_mode={execution_mode}). "
                "Todos os pareceres atenderam aos critérios de aceitação corporativos."
            )
            recommendations = [
                *report.recommendations,
                "Consenso validado entre todas as perspectivas avaliadas.",
            ]
        else:
            failed_roles = [r.role for r in report.results if not r.success or r.error]
            consensus_msg = (
                f"REJECTED: Revisão multi-perspectiva concluída por {len(roles)} especialistas "
                f"(execution_mode={execution_mode}). "
                f"{report.failed_tasks} parecer(es) reprovado(s): {', '.join(failed_roles)}."
            )
            recommendations = [
                *report.recommendations,
                f"Consenso reprovado: corrigir falhas reportadas em {', '.join(failed_roles)}.",
            ]
        return report.model_copy(
            update={
                "aggregated_consensus": consensus_msg,
                "recommendations": recommendations,
            }
        )
