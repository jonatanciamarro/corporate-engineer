"""
Test Suite for Tri-Phase Adversarial Loop (IMP-0026 / ADR-028).
Shift-Left TDD: Red Team 1.5 -> Transcendence 1.6 -> Re-Verification 1.7.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from corporate_engineer.models import (
    ChaosTestCase,
    DialecticalLoopResult,
    RedTeamAttackReport,
    RedTeamThreatCategory,
    RedTeamVerdictStatus,
    RedTeamVulnerabilitySeverity,
    TranscendencePlan,
)
from corporate_engineer.orchestrator.adversarial import (
    AdversarialLoopCoordinator,
    AdversarialRedTeam,
    ArchitectureTranscender,
)


@pytest.fixture
def vulnerable_plan_text() -> str:
    return (
        "Plano de Execução: Iniciar 50 threads concorrentes consumindo filas sem controle de lock. "
        "Acessar endpoints HTTP externos sem configurar timeout. Ler parâmetros de entrada do usuário "
        "diretamente em dicionários mutáveis sem validação de esquema Pydantic. Executar comandos Git "
        "com subprocess sem tratamento de erro ou fallback para caso o repositório esteja travado. "
        "Executar ferramentas com privilégios de root no servidor MCP sem circuit breaker."
    )


@pytest.fixture
def clean_plan_text() -> str:
    return (
        "Plano de Execução: Implementação cirúrgica com modelos imutáveis Pydantic v2, "
        "RLock reentrante para sincronização de threads, timeouts estritos de 15s com tratamento "
        "de TimeoutExpired, circuit breaker individual para ferramentas MCP e rollback automático "
        "com AtomicFileSandbox."
    )


def test_red_team_attack_detects_threat_axes(vulnerable_plan_text: str):
    """Phase 1.5: Verify Red Team detects flaws across the 5 corporate threat axes."""
    red_team = AdversarialRedTeam()
    report: RedTeamAttackReport = red_team.attack(
        plan_id="IMP-0026-TEST", plan_text=vulnerable_plan_text
    )

    assert report.plan_id == "IMP-0026-TEST"
    assert report.total_vulnerabilities > 0
    assert report.highest_severity in (
        RedTeamVulnerabilitySeverity.CRITICAL,
        RedTeamVulnerabilitySeverity.HIGH,
    )
    assert report.is_blocked is True
    assert len(report.attack_narrative) > 0

    categories = {v.category for v in report.vulnerabilities}
    assert RedTeamThreatCategory.CONCURRENCY in categories
    assert RedTeamThreatCategory.NETWORK_TIMEOUTS in categories
    assert RedTeamThreatCategory.DATA_INTEGRITY in categories
    assert RedTeamThreatCategory.PRIVILEGE_MCP in categories
    assert RedTeamThreatCategory.FAULT_TOLERANCE in categories


def test_architecture_transcender_synthesizes_hardenings(vulnerable_plan_text: str):
    """Phase 1.6: Verify Transcender elevates vulnerabilities into formal structural invariants."""
    red_team = AdversarialRedTeam()
    attack_report = red_team.attack(plan_id="IMP-0026-TEST", plan_text=vulnerable_plan_text)

    transcender = ArchitectureTranscender()
    plan: TranscendencePlan = transcender.transcend(
        plan_id="IMP-0026-TEST",
        original_plan=vulnerable_plan_text,
        attack_report=attack_report,
    )

    assert plan.plan_id == "IMP-0026-TEST"
    assert len(plan.hardenings) == len(attack_report.vulnerabilities)
    assert len(plan.structural_invariants) > 0
    assert plan.residual_risk == "LOW"

    for hardening in plan.hardenings:
        assert len(hardening.formal_invariant) > 0
        assert len(hardening.resilience_mechanism) > 0
        assert len(hardening.transcendence_strategy) > 0


def test_adversarial_re_verification_and_chaos_matrix(vulnerable_plan_text: str):
    """Phase 1.7: Verify second pass evaluates transcendence and synthesizes chaos test cases."""
    red_team = AdversarialRedTeam()
    attack_report = red_team.attack(plan_id="IMP-0026-TEST", plan_text=vulnerable_plan_text)

    transcender = ArchitectureTranscender()
    transcendence_plan = transcender.transcend(
        plan_id="IMP-0026-TEST",
        original_plan=vulnerable_plan_text,
        attack_report=attack_report,
    )

    re_attack = red_team.re_verify(transcendence_plan)
    assert re_attack.is_blocked is False
    assert re_attack.highest_severity in (
        RedTeamVulnerabilitySeverity.LOW,
        RedTeamVulnerabilitySeverity.MEDIUM,
    )

    chaos_tests: list[ChaosTestCase] = red_team.generate_chaos_matrix(transcendence_plan)
    assert len(chaos_tests) > 0
    for case in chaos_tests:
        assert case.case_id.startswith("CHAOS-")
        assert len(case.injection_trigger) > 0
        assert len(case.expected_behavior) > 0
        assert case.tdd_scenario.startswith("test_")


def test_dialectical_loop_coordinator_end_to_end(vulnerable_plan_text: str):
    """Verify coordinator executes 1.5 -> 1.6 -> 1.7 and produces VERIFIED verdict."""
    coordinator = AdversarialLoopCoordinator()
    result: DialecticalLoopResult = coordinator.run_dialectical_loop(
        plan_id="CORP-202",
        plan_text=vulnerable_plan_text,
    )

    assert result.plan_id == "CORP-202"
    assert result.initial_attack.is_blocked is True
    assert result.transcendence is not None
    assert result.re_verification is not None
    assert result.re_verification.is_blocked is False
    assert result.verdict.status == RedTeamVerdictStatus.VERIFIED
    assert len(result.verdict.chaos_matrix) > 0
    assert result.verdict.bypassed is False
    assert result.duration_ms >= 0.0


def test_dialectical_loop_fast_path_bypass():
    """Verify fast-path bypass for low risk tasks and operational bypass."""
    coordinator = AdversarialLoopCoordinator()

    # Low risk operational prompt
    result_bypassed = coordinator.run_dialectical_loop(
        plan_id="CORP-203",
        plan_text="pytest tests/test_models.py",
        risk_level="LOW",
    )
    assert result_bypassed.verdict.status == RedTeamVerdictStatus.BYPASSED
    assert result_bypassed.verdict.bypassed is True

    # Force attack overrides bypass
    result_forced = coordinator.run_dialectical_loop(
        plan_id="CORP-203",
        plan_text="pytest tests/test_models.py",
        risk_level="LOW",
        force_attack=True,
    )
    assert result_forced.verdict.status == RedTeamVerdictStatus.VERIFIED
    assert result_forced.verdict.bypassed is False


def test_graph_run_pipeline_integrates_adversarial_loop(tmp_path: Path):
    """Verify AutonomousEngineeringGraph.run_pipeline triggers adversarial loop and populates details."""
    from corporate_engineer.models import TaskInput
    from corporate_engineer.orchestrator.graph import AutonomousEngineeringGraph

    task = TaskInput(
        ticket_id="CORP-CHAOS-01",
        description="Refatoração concorrente com pool de workers assíncronos e acesso a arquivos",
        workspace_path=str(tmp_path),
    )
    graph = AutonomousEngineeringGraph(task=task)
    report = graph.run_pipeline(dry_run=True, auto_deliver=True)

    assert report.ticket_id == "CORP-CHAOS-01"
    assert "adversarial_verdict" in report.details
    assert "chaos_matrix" in report.details
    assert report.details["adversarial_verdict"] in ("VERIFIED", "BYPASSED")
    assert isinstance(report.details["chaos_matrix"], list)


def test_cli_dialectic_command():
    """Verify corporate-engineer dialectic CLI command produces valid report."""
    from corporate_engineer.cli import main

    # text format
    exit_code_text = main(["dialectic", "Concorrência com pool sem locks", "--format", "text"])
    assert exit_code_text == 0

    # json format
    exit_code_json = main(["dialectic", "Concorrência com pool sem locks", "--format", "json"])
    assert exit_code_json == 0
