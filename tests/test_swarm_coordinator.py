"""
Testes unitários e de integração para o Multi-Agent Swarm Coordinator via MCP Hub (IMP-0016 / ADR-016).
Validação de modelos DTO, despacho concorrente (Fan-Out/Fan-In), consenso multi-agente e CLI.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from corporate_engineer.mcp.hub import MCPEnterpriseHub
from corporate_engineer.models import (
    MCPNamespacedTool,
    MCPServerDefinition,
    SwarmGoalReport,
    SwarmMember,
    SwarmTaskResult,
)
from corporate_engineer.orchestrator.swarm import SwarmCoordinator


def test_swarm_models_validation() -> None:
    """Verifica a validação de tipos e serialização Pydantic v2 dos contratos de Swarm."""
    member = SwarmMember(
        agent_id="sec-01",
        role="security-reviewer",
        task_prompt="Auditar arquivos de configuração",
        allowed_tools=["git.diff", "secret_scanner.scan"],
        status="IDLE",
    )
    assert member.agent_id == "sec-01"
    assert member.role == "security-reviewer"
    assert "git.diff" in member.allowed_tools

    task_res = SwarmTaskResult(
        agent_id="sec-01",
        role="security-reviewer",
        output="Auditoria concluída: 0 segredos detectados.",
        success=True,
        execution_time_ms=12.5,
        tools_called=["secret_scanner.scan"],
    )
    assert task_res.success is True
    assert task_res.execution_time_ms == 12.5

    report = SwarmGoalReport(
        goal="Revisão Tripartite de PR",
        swarm_name="quality-trio",
        total_agents=3,
        successful_tasks=3,
        failed_tasks=0,
        aggregated_consensus="APPROVED: Todos os pareceres foram favoráveis.",
        results=[task_res],
        execution_time_ms=35.0,
        recommendations=["Manter pipeline de auditoria contínua."],
    )
    dumped = report.model_dump_json()
    loaded = SwarmGoalReport.model_validate_json(dumped)
    assert loaded.total_agents == 3
    assert loaded.successful_tasks == 3
    assert loaded.aggregated_consensus.startswith("APPROVED")


def test_swarm_coordinator_initialization() -> None:
    """Verifica a inicialização do coordenador com dependências padrão e customizadas."""
    coordinator = SwarmCoordinator()
    assert coordinator.hub is not None
    assert coordinator.router is not None


def test_swarm_coordinator_create_swarm() -> None:
    """Verifica a instanciação de um grupo de trabalho com papéis especializados e injeção de ferramentas."""
    hub = MCPEnterpriseHub()
    hub.register_server(
        name="security",
        config=MCPServerDefinition(command="echo"),
    )
    hub.register_tool(
        MCPNamespacedTool(
            server_name="security",
            tool_name="scan_secrets",
            namespaced_name="security.scan_secrets",
            description="Auditoria de secrets",
        )
    )
    hub.register_server(
        name="git",
        config=MCPServerDefinition(command="echo"),
    )
    hub.register_tool(
        MCPNamespacedTool(
            server_name="git",
            tool_name="diff",
            namespaced_name="git.diff",
            description="Inspeção de diff",
        )
    )

    coordinator = SwarmCoordinator(hub=hub)
    members = coordinator.create_swarm(
        name="sec-review-swarm",
        roles=["security-reviewer", "architect", "tdd-guide"],
    )

    assert len(members) == 3
    roles = [m.role for m in members]
    assert "security-reviewer" in roles
    assert "architect" in roles
    assert "tdd-guide" in roles

    # Security reviewer deve receber ferramentas associadas a segurança
    sec_member = next(m for m in members if m.role == "security-reviewer")
    assert any("security." in t for t in sec_member.allowed_tools)


def test_swarm_coordinator_dispatch_single_task() -> None:
    """Verifica o despacho de tarefa para um membro individual do swarm."""
    coordinator = SwarmCoordinator()
    member = SwarmMember(
        agent_id="arch-01",
        role="architect",
        task_prompt="Valide contratos DTO Pydantic",
        allowed_tools=[],
    )
    result = coordinator.dispatch_task(member, "Analise a estrutura de dados")

    assert isinstance(result, SwarmTaskResult)
    assert result.agent_id == "arch-01"
    assert result.success is True
    assert result.execution_time_ms > 0.0
    assert len(result.output) > 0


def test_swarm_coordinator_fan_out() -> None:
    """Verifica a execução concorrente Fan-Out / Fan-In com honestidade para papéis sem executor."""
    coordinator = SwarmCoordinator()
    subtasks = [
        {"role": "architect", "task": "Design dos contratos Pydantic v2"},
        {"role": "tdd-guide", "task": "Criação de testes unitários com pytest"},
        {"role": "security-reviewer", "task": "Auditoria de permissões e chaves"},
    ]

    report = coordinator.run_fan_out(
        goal="Construção de novo microsserviço",
        subtasks=subtasks,
        max_workers=3,
    )

    assert isinstance(report, SwarmGoalReport)
    assert report.total_agents == 3
    assert report.successful_tasks == 2
    assert report.skipped_tasks == 1
    assert report.failed_tasks == 0
    assert len(report.results) == 3
    assert report.execution_time_ms > 0.0
    assert not report.aggregated_consensus.startswith("APPROVED")

    by_role = {r.role: r for r in report.results}
    assert by_role["architect"].status == "COMPLETED"
    assert by_role["security-reviewer"].status == "COMPLETED"
    assert by_role["tdd-guide"].status == "SKIPPED"
    assert by_role["tdd-guide"].success is False
    assert "No role_executor or deterministic analyzer" in (by_role["tdd-guide"].error or "")

    # Quando uma ferramenta MCP real é fornecida ao papel sem analisador, ele executa e aprova
    hub = MCPEnterpriseHub()
    hub.register_server(name="pytest_mcp", config=MCPServerDefinition(command="echo"))
    hub.register_tool(
        MCPNamespacedTool(
            server_name="pytest_mcp",
            tool_name="run_suite",
            namespaced_name="pytest_mcp.run_suite",
            description="Run pytest suite",
        )
    )
    mcp_coordinator = SwarmCoordinator(hub=hub)
    mcp_report = mcp_coordinator.run_fan_out(
        goal="Construção com ferramenta MCP para tdd-guide",
        subtasks=[
            {"role": "architect", "task": "Design dos contratos Pydantic v2", "tools": []},
            {
                "role": "tdd-guide",
                "task": "Executar testes com MCP",
                "tools": ["pytest_mcp.run_suite"],
            },
            {"role": "security-reviewer", "task": "Auditoria de permissões e chaves", "tools": []},
        ],
        max_workers=3,
    )
    assert mcp_report.successful_tasks == 3
    assert mcp_report.skipped_tasks == 0
    assert mcp_report.failed_tasks == 0
    assert mcp_report.aggregated_consensus.startswith("APPROVED")


def test_swarm_coordinator_consensus() -> None:
    """Verifica a formação de consenso multi-agente em torno de um alvo de revisão."""
    coordinator = SwarmCoordinator()
    report = coordinator.run_consensus(
        target_description="Implementação do motor AST com validação sintática estrita",
        reviewer_roles=["architect", "security-reviewer", "code-reviewer"],
    )

    assert isinstance(report, SwarmGoalReport)
    assert report.total_agents == 3
    assert "APPROVED" in report.aggregated_consensus or "REJECTED" in report.aggregated_consensus
    assert len(report.recommendations) > 0


def test_swarm_coordinator_resilience_circuit_breaker() -> None:
    """Verifica que a falha de uma ferramenta com circuit breaker não derruba os demais agentes."""
    hub = MCPEnterpriseHub()
    # Registra servidor instável com circuit breaker
    hub.register_server(
        name="flaky_service",
        config=MCPServerDefinition(command="non_existent_command_12345"),
    )
    hub.register_tool(
        MCPNamespacedTool(
            server_name="flaky_service",
            tool_name="flaky_action",
            namespaced_name="flaky_service.flaky_action",
            description="Ação instável",
        )
    )
    coordinator = SwarmCoordinator(hub=hub)
    member = SwarmMember(
        agent_id="test-01",
        role="tdd-guide",
        task_prompt="Executar ação com ferramenta",
        allowed_tools=["flaky_service.flaky_action"],
    )

    # Não deve lançar exceção não tratada; o circuit breaker deve conter a falha
    result = coordinator.dispatch_task(member, "Tente invocar flaky_service")
    assert isinstance(result, SwarmTaskResult)


def test_swarm_cli_execution() -> None:
    """Verifica a invocação do subcomando corporate-engineer swarm via linha de comando."""
    cmd = [
        sys.executable,
        "-m",
        "corporate_engineer.cli",
        "swarm",
        "--goal",
        "Auditoria de arquitetura e qualidade",
        "--roles",
        "architect",
        "security-reviewer",
        "--format",
        "json",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert result.returncode == 0, f"Falha na CLI swarm: {result.stderr}"
    data = json.loads(result.stdout)
    assert "total_agents" in data
    assert data["total_agents"] == 2
    assert "aggregated_consensus" in data


def test_swarm_custom_role_executor(tmp_path: Path) -> None:
    """Verifica que role_executor injetado recebe (member, prompt, tool_records) e define a saída."""
    hub = MCPEnterpriseHub()
    hub.register_server(name="lint", config=MCPServerDefinition(command="echo"))
    hub.register_tool(
        MCPNamespacedTool(
            server_name="lint",
            tool_name="check",
            namespaced_name="lint.check",
            description="Static lint check",
        )
    )

    captured_calls: list[tuple[SwarmMember, str, list[dict[str, object]]]] = []

    def custom_executor(
        member: SwarmMember,
        prompt: str,
        tool_records: list[dict[str, object]],
    ) -> str:
        captured_calls.append((member, prompt, tool_records))
        return f"CUSTOM[{member.role}]::{prompt}::tools={len(tool_records)}"

    coordinator = SwarmCoordinator(
        hub=hub,
        workspace_path=tmp_path,
        role_executor=custom_executor,
    )
    member = SwarmMember(
        agent_id="code-01",
        role="code-reviewer",
        task_prompt="Review code",
        allowed_tools=["lint.check"],
    )

    result = coordinator.dispatch_task(member, "Analisar módulo X")
    assert result.success is True
    assert result.output == "CUSTOM[code-reviewer]::Analisar módulo X::tools=1"
    assert len(captured_calls) == 1
    rec_member, rec_prompt, rec_tools = captured_calls[0]
    assert rec_member.agent_id == "code-01"
    assert rec_prompt == "Analisar módulo X"
    assert len(rec_tools) == 1
    assert rec_tools[0]["tool"] == "lint.check"
    assert rec_tools[0]["is_error"] is False

    report = coordinator.run_fan_out(
        goal="Custom execution mode verification",
        subtasks=[{"role": "code-reviewer", "task": "Revisar"}],
    )
    assert any("execution_mode=custom-executor" in r for r in report.recommendations)


def test_swarm_deterministic_security_analyzer_detects_real_secret(tmp_path: Path) -> None:
    """Verifica que security-reviewer detecta segredo real no workspace e reprova consenso."""
    leak_file = tmp_path / "credentials.py"
    pfx = "AKIA"
    leak_file.write_text(f'AWS_ACCESS_KEY = "{pfx}IOSFODNN7EXAMPLE12"\n', encoding="utf-8")

    coordinator = SwarmCoordinator(workspace_path=tmp_path)
    sec_member = SwarmMember(
        agent_id="sec-01",
        role="security-reviewer",
        task_prompt="Auditar workspace",
        allowed_tools=[],
    )

    task_result = coordinator.dispatch_task(sec_member, "Verificar segredos")
    assert task_result.success is False
    assert task_result.error == "1 secret(s) detected"
    assert "1" in task_result.output

    report = coordinator.run_consensus(
        target_description="Workspace com segredo vazado",
        reviewer_roles=["architect", "security-reviewer", "code-reviewer"],
    )
    assert report.failed_tasks == 1
    assert report.successful_tasks == 2
    assert "REJECTED" in report.aggregated_consensus
    assert any("execution_mode=deterministic-analyzer" in r for r in report.recommendations)


def test_swarm_consensus_rejected_message_honest(tmp_path: Path) -> None:
    """Verifica que run_consensus não afirma aprovação quando há tarefas reprovadas."""
    leak_file = tmp_path / "token_leak.py"
    gh_prefix = "ghp_"
    leak_file.write_text(f'TOKEN = "{gh_prefix}{"A" * 36}"\n', encoding="utf-8")

    coordinator = SwarmCoordinator(workspace_path=tmp_path)
    report = coordinator.run_consensus(
        target_description="Validação honesta de falha",
        reviewer_roles=["architect", "security-reviewer"],
    )

    assert report.failed_tasks == 1
    assert report.aggregated_consensus.startswith("REJECTED")
    assert "Todos os pareceres atenderam" not in report.aggregated_consensus
    assert not any("Consenso validado" in rec for rec in report.recommendations)


def test_swarm_deterministic_analyzers_for_architect_code_and_rag(tmp_path: Path) -> None:
    """Verifica analisadores determinísticos reais para architect, code-reviewer e rag-pipeline-reviewer."""
    src_pkg = tmp_path / "src" / "corporate_engineer"
    src_pkg.mkdir(parents=True)
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(parents=True)

    (src_pkg / "widget.py").write_text(
        "class CleanWidget:\n    def run(self, x: int) -> int:\n        return x + 1\n",
        encoding="utf-8",
    )
    (src_pkg / "__init__.py").write_text('__all__ = ["CleanWidget"]\n', encoding="utf-8")
    (tests_dir / "test_widget.py").write_text(
        "from corporate_engineer.widget import CleanWidget\n"
        "def test_widget() -> None:\n"
        "    assert CleanWidget().run(1) == 2\n",
        encoding="utf-8",
    )

    coordinator = SwarmCoordinator(workspace_path=tmp_path)

    arch_res = coordinator.dispatch_task(
        SwarmMember(agent_id="arch-01", role="architect"), "Verificar wiring"
    )
    assert arch_res.success is True
    assert "1/1" in arch_res.output

    code_res = coordinator.dispatch_task(
        SwarmMember(agent_id="code-01", role="code-reviewer"), "Verificar scorecard"
    )
    assert code_res.success is True
    assert "score=" in code_res.output
    assert "grade=" in code_res.output
    assert "violations=" in code_res.output

    rag_res = coordinator.dispatch_task(
        SwarmMember(agent_id="rag-01", role="rag-pipeline-reviewer"), "Verificar símbolos AST"
    )
    assert rag_res.success is True
    assert "2" in rag_res.output or "1" in rag_res.output

    # Adiciona módulo órfão com baixa qualidade para provar falha real em architect e code-reviewer
    bad_lines = [
        "def terrible(a, b, c, d, e, f):",
        "    global X",
        "    if a:",
        "        if b:",
        "            if c:",
        "                if d:",
        "                    if e:",
        "                        if f:",
        "                            return {'bad': 1}",
        "    return {'bad': 2}",
    ]
    (src_pkg / "orphan_bad.py").write_text("\n".join(bad_lines) + "\n", encoding="utf-8")

    arch_fail = coordinator.dispatch_task(
        SwarmMember(agent_id="arch-02", role="architect"), "Verificar módulo órfão"
    )
    assert arch_fail.success is False
    assert arch_fail.error is not None

    code_fail = coordinator.dispatch_task(
        SwarmMember(agent_id="code-02", role="code-reviewer"), "Verificar queda de nota"
    )
    assert code_fail.success is False
    assert code_fail.error is not None
