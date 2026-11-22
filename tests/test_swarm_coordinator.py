"""
Testes unitários e de integração para o Multi-Agent Swarm Coordinator via MCP Hub (IMP-0016 / ADR-016).
Validação de modelos DTO, despacho concorrente (Fan-Out/Fan-In), consenso multi-agente e CLI.
"""

from __future__ import annotations

import json
import subprocess
import sys

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
    """Verifica a execução concorrente Fan-Out / Fan-In de múltiplas tarefas especializadas."""
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
    assert report.successful_tasks == 3
    assert report.failed_tasks == 0
    assert len(report.results) == 3
    assert report.execution_time_ms > 0.0


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
