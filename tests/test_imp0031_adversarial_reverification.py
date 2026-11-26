"""
Shift-Left TDD Suite for IMP-0031: Genuine Phase 1.7 Adversarial Re-Verification
and Bounded Dialectical Hardening Loop (ADR-028).
"""

from __future__ import annotations

import pytest

from corporate_engineer.models import (
    RedTeamAttackReport,
    RedTeamThreatCategory,
    RedTeamVerdictStatus,
    RedTeamVulnerability,
    RedTeamVulnerabilitySeverity,
    TranscendenceHardening,
    TranscendencePlan,
)
from corporate_engineer.orchestrator.adversarial import (
    AdversarialLoopCoordinator,
    AdversarialRedTeam,
    ArchitectureTranscender,
)


def _sample_attack_report() -> RedTeamAttackReport:
    """Create a representative attack report with two blocking vulnerabilities."""
    vulns = [
        RedTeamVulnerability(
            id="VULN-001",
            category=RedTeamThreatCategory.CONCURRENCY,
            severity=RedTeamVulnerabilitySeverity.CRITICAL,
            title="Vulnerabilidade Crítica de Concorrência e Race Condition",
            description="Workers concorrentes sem controle de lock.",
            attack_vector="Race condition em estado compartilhado.",
            target_component="threading / worker pool",
        ),
        RedTeamVulnerability(
            id="VULN-002",
            category=RedTeamThreatCategory.NETWORK_TIMEOUTS,
            severity=RedTeamVulnerabilitySeverity.HIGH,
            title="Timeouts Indefinidos em Rede/Subprocessos",
            description="Subprocesso sem timeout explícito.",
            attack_vector="Bloqueio indefinido do orquestrador.",
            target_component="subprocess runner",
        ),
    ]
    return RedTeamAttackReport(
        plan_id="IMP-0031-TEST",
        total_vulnerabilities=len(vulns),
        vulnerabilities=vulns,
        highest_severity=RedTeamVulnerabilitySeverity.CRITICAL,
        attack_narrative="2 falhas bloqueantes identificadas.",
        is_blocked=True,
    )


def test_re_verify_blocks_uncovered_attack_vulnerabilities() -> None:
    """Phase 1.7 must block when attack vulnerabilities are missing from hardenings."""
    red_team = AdversarialRedTeam()
    attack_report = _sample_attack_report()

    partial_plan = TranscendencePlan(
        plan_id="IMP-0031-TEST",
        hardenings=[
            TranscendenceHardening(
                vulnerability_id="VULN-001",
                original_weakness="Vulnerabilidade Crítica de Concorrência e Race Condition",
                transcendence_strategy="Sincronização Reentrante",
                formal_invariant="Todo acesso compartilhado usa threading.RLock().",
                resilience_mechanism="threading.RLock() + ContextVars.",
            )
        ],
        transcended_architecture="Arquitetura com threading.RLock().",
        structural_invariants=["Todo acesso compartilhado usa threading.RLock()."],
        residual_risk="LOW",
    )

    re_report = red_team.re_verify(partial_plan, attack_report=attack_report)
    assert re_report.is_blocked is True
    assert re_report.total_vulnerabilities >= 1
    assert re_report.highest_severity in (
        RedTeamVulnerabilitySeverity.CRITICAL,
        RedTeamVulnerabilitySeverity.HIGH,
    )

    empty_plan = TranscendencePlan(
        plan_id="IMP-0031-TEST",
        hardenings=[],
        transcended_architecture="Arquitetura vazia.",
        structural_invariants=[],
        residual_risk="LOW",
    )
    re_empty = red_team.re_verify(empty_plan, attack_report=attack_report)
    assert re_empty.is_blocked is True
    assert re_empty.total_vulnerabilities >= 2
    assert re_empty.highest_severity == RedTeamVulnerabilitySeverity.CRITICAL


@pytest.mark.parametrize(
    ("formal_invariant", "resilience_mechanism", "structural_invariants"),
    [
        ("", "threading.RLock() aplicado", [""]),
        ("TODO", "threading.RLock() aplicado", ["TODO"]),
        ("Todo acesso usa RLock", "none", ["Todo acesso usa RLock"]),
        ("Todo acesso usa RLock", "N/A", ["Todo acesso usa RLock"]),
        ("Todo acesso usa threading.RLock()", "threading.RLock()", []),
    ],
)
def test_re_verify_blocks_hollow_or_placeholder_hardening(
    formal_invariant: str,
    resilience_mechanism: str,
    structural_invariants: list[str],
) -> None:
    """Phase 1.7 must reject empty, placeholder, or unbacked hardenings."""
    red_team = AdversarialRedTeam()
    hollow_plan = TranscendencePlan(
        plan_id="IMP-0031-HOLLOW",
        hardenings=[
            TranscendenceHardening(
                vulnerability_id="VULN-001",
                original_weakness="Race condition em workers",
                transcendence_strategy="Blindagem concorrente",
                formal_invariant=formal_invariant,
                resilience_mechanism=resilience_mechanism,
            )
        ],
        transcended_architecture="Arquitetura em revisão.",
        structural_invariants=structural_invariants,
        residual_risk="LOW",
    )

    re_report = red_team.re_verify(hollow_plan)
    assert re_report.is_blocked is True
    assert re_report.total_vulnerabilities >= 1
    assert re_report.highest_severity in (
        RedTeamVulnerabilitySeverity.CRITICAL,
        RedTeamVulnerabilitySeverity.HIGH,
    )


def test_re_verify_blocks_weak_hardening_missing_category_controls() -> None:
    """Phase 1.7 must block hardenings that lack real category resilience controls."""
    red_team = AdversarialRedTeam()
    concurrency_vuln = RedTeamVulnerability(
        id="VULN-001",
        category=RedTeamThreatCategory.CONCURRENCY,
        severity=RedTeamVulnerabilitySeverity.CRITICAL,
        title="Vulnerabilidade Crítica de Concorrência e Race Condition",
        description="Acesso concorrente sem sincronização.",
        attack_vector="Corrupção de estado compartilhado.",
        target_component="worker pool",
    )
    attack_report = RedTeamAttackReport(
        plan_id="IMP-0031-WEAK",
        total_vulnerabilities=1,
        vulnerabilities=[concurrency_vuln],
        highest_severity=RedTeamVulnerabilitySeverity.CRITICAL,
        attack_narrative="Concorrência sem proteção.",
        is_blocked=True,
    )

    weak_plan = TranscendencePlan(
        plan_id="IMP-0031-WEAK",
        hardenings=[
            TranscendenceHardening(
                vulnerability_id="VULN-001",
                original_weakness=concurrency_vuln.title,
                transcendence_strategy="Observabilidade simples",
                formal_invariant="Todas as operações devem adicionar logs no stdout.",
                resilience_mechanism="adicionar logs no stdout",
            )
        ],
        transcended_architecture="Sistema instrumentado com logs no stdout.",
        structural_invariants=["Todas as operações devem adicionar logs no stdout."],
        residual_risk="LOW",
    )

    re_report = red_team.re_verify(weak_plan, attack_report=attack_report)
    assert re_report.is_blocked is True
    assert re_report.total_vulnerabilities >= 1
    assert re_report.highest_severity == RedTeamVulnerabilitySeverity.CRITICAL


def test_re_verify_detects_new_threats_in_transcended_architecture() -> None:
    """Phase 1.7 must detect unmitigated threats introduced in transcended_architecture."""
    red_team = AdversarialRedTeam()
    plan_with_new_threats = TranscendencePlan(
        plan_id="IMP-0031-ARCH-THREAT",
        hardenings=[
            TranscendenceHardening(
                vulnerability_id="VULN-001",
                original_weakness="Vulnerabilidade Crítica de Concorrência",
                transcendence_strategy="Sincronização Reentrante",
                formal_invariant="Estado compartilhado protegido por threading.RLock().",
                resilience_mechanism="threading.RLock() + ContextVars.",
            )
        ],
        transcended_architecture=(
            "Executar comandos subprocess sem timeout e ferramentas sem circuit breaker "
            "com acesso protegido por RLock."
        ),
        structural_invariants=["Estado compartilhado protegido por threading.RLock()."],
        residual_risk="LOW",
    )

    re_report = red_team.re_verify(plan_with_new_threats)
    assert re_report.is_blocked is True
    assert re_report.total_vulnerabilities >= 2
    assert re_report.highest_severity in (
        RedTeamVulnerabilitySeverity.CRITICAL,
        RedTeamVulnerabilitySeverity.HIGH,
    )
    detected_categories = {v.category for v in re_report.vulnerabilities}
    assert RedTeamThreatCategory.NETWORK_TIMEOUTS in detected_categories
    assert RedTeamThreatCategory.PRIVILEGE_MCP in detected_categories


@pytest.mark.parametrize("residual_risk", ["HIGH", "CRITICAL"])
def test_re_verify_blocks_high_or_critical_residual_risk(residual_risk: str) -> None:
    """Phase 1.7 must block any TranscendencePlan declaring HIGH or CRITICAL residual risk."""
    red_team = AdversarialRedTeam()
    plan = TranscendencePlan(
        plan_id="IMP-0031-RISK",
        hardenings=[],
        transcended_architecture="Arquitetura baseline com risco residual elevado.",
        structural_invariants=[],
        residual_risk=residual_risk,
    )

    re_report = red_team.re_verify(plan)
    assert re_report.is_blocked is True
    assert re_report.total_vulnerabilities >= 1
    assert re_report.highest_severity in (
        RedTeamVulnerabilitySeverity.CRITICAL,
        RedTeamVulnerabilitySeverity.HIGH,
    )


def test_re_verify_approves_genuine_transcendence() -> None:
    """Phase 1.7 must approve genuine ArchitectureTranscender plans with 0 residual flaws."""
    red_team = AdversarialRedTeam()
    transcender = ArchitectureTranscender()

    vulnerable_plan = (
        "Iniciar threads concorrentes sem controle de lock. "
        "Executar subprocess sem timeout e sem tratamento de erro ou fallback. "
        "Usar dicionários mutáveis sem pydantic e ferramentas sem circuit breaker."
    )
    attack_report = red_team.attack(plan_id="IMP-0031-VALID", plan_text=vulnerable_plan)
    assert attack_report.is_blocked is True

    transcendence_plan = transcender.transcend(
        plan_id="IMP-0031-VALID",
        original_plan=vulnerable_plan,
        attack_report=attack_report,
    )
    re_report = red_team.re_verify(transcendence_plan, attack_report=attack_report)
    assert re_report.is_blocked is False
    assert re_report.total_vulnerabilities == 0
    assert re_report.highest_severity == RedTeamVulnerabilitySeverity.LOW

    clean_attack = red_team.attack(
        plan_id="IMP-0031-CLEAN", plan_text="pytest tests/test_models.py"
    )
    assert clean_attack.total_vulnerabilities == 0
    clean_transcendence = transcender.transcend(
        plan_id="IMP-0031-CLEAN",
        original_plan="pytest tests/test_models.py",
        attack_report=clean_attack,
    )
    re_clean = red_team.re_verify(clean_transcendence, attack_report=clean_attack)
    assert re_clean.is_blocked is False
    assert re_clean.total_vulnerabilities == 0


class _WeakStubTranscender(ArchitectureTranscender):
    """Stub transcender that intentionally fails to remediate vulnerabilities."""

    def __init__(self) -> None:
        self.calls = 0

    def transcend(
        self,
        plan_id: str,
        original_plan: str,
        attack_report: RedTeamAttackReport,
    ) -> TranscendencePlan:
        self.calls += 1
        return TranscendencePlan(
            plan_id=plan_id,
            hardenings=[
                TranscendenceHardening(
                    vulnerability_id=v.id,
                    original_weakness=v.title,
                    transcendence_strategy="Placeholder strategy",
                    formal_invariant="TODO",
                    resilience_mechanism="adicionar logs no stdout",
                )
                for v in attack_report.vulnerabilities
            ],
            transcended_architecture="Executar comandos subprocess sem timeout.",
            structural_invariants=[],
            residual_risk="HIGH",
        )


def test_coordinator_enforces_bounded_loop_and_harden_required() -> None:
    """Coordinator must run up to 2 dialectical rounds and return HARDEN_REQUIRED if blocked."""
    weak_transcender = _WeakStubTranscender()
    coordinator = AdversarialLoopCoordinator(transcender=weak_transcender)

    result = coordinator.run_dialectical_loop(
        plan_id="IMP-0031-LOOP",
        plan_text="Iniciar pool de workers sem controle de lock e subprocess sem timeout.",
        risk_level="HIGH",
    )

    assert weak_transcender.calls == 2
    assert result.verdict.status == RedTeamVerdictStatus.HARDEN_REQUIRED
    assert result.verdict.iterations_completed == 2
    assert len(result.verdict.unresolved_vulnerabilities) > 0
    assert result.re_verification is not None
    assert result.re_verification.is_blocked is True


def test_re_verify_rejects_negated_category_signals() -> None:
    """Negated signal phrases like 'sem lock' must not count as category controls."""
    red_team = AdversarialRedTeam()
    vuln = RedTeamVulnerability(
        id="VULN-001",
        category=RedTeamThreatCategory.CONCURRENCY,
        severity=RedTeamVulnerabilitySeverity.CRITICAL,
        title="Race condition",
        description="Acesso concorrente sem controle de lock.",
        attack_vector="Corrupção de estado.",
        target_component="worker pool",
    )
    attack_report = RedTeamAttackReport(
        plan_id="IMP-0031-NEG",
        total_vulnerabilities=1,
        vulnerabilities=[vuln],
        highest_severity=RedTeamVulnerabilitySeverity.CRITICAL,
        attack_narrative="Concorrência sem proteção.",
        is_blocked=True,
    )
    negated_plan = TranscendencePlan(
        plan_id="IMP-0031-NEG",
        hardenings=[
            TranscendenceHardening(
                vulnerability_id="VULN-001",
                original_weakness=vuln.title,
                transcendence_strategy="Execução sem lock para velocidade",
                formal_invariant="Operar sem controle de lock em memória.",
                resilience_mechanism="sem lock",
            )
        ],
        transcended_architecture="Execução sem lock.",
        structural_invariants=["Operar sem controle de lock em memória."],
        residual_risk="LOW",
    )
    re_report = red_team.re_verify(negated_plan, attack_report=attack_report)
    assert re_report.is_blocked is True
    assert re_report.total_vulnerabilities >= 1


class _SecondRoundAdaptiveTranscender(ArchitectureTranscender):
    """Stub transcender that fails round 1 and resolves all flaws on round 2."""

    def __init__(self) -> None:
        self.calls = 0

    def transcend(
        self,
        plan_id: str,
        original_plan: str,
        attack_report: RedTeamAttackReport,
    ) -> TranscendencePlan:
        self.calls += 1
        if self.calls == 1:
            return TranscendencePlan(
                plan_id=plan_id,
                hardenings=[],
                transcended_architecture="Executar subprocess sem timeout.",
                structural_invariants=[],
                residual_risk="HIGH",
            )
        return super().transcend(
            plan_id=plan_id, original_plan=original_plan, attack_report=attack_report
        )


def test_coordinator_converges_on_second_dialectical_round() -> None:
    """Coordinator must allow round-2 transcendence to reach VERIFIED within 2 rounds."""
    adaptive = _SecondRoundAdaptiveTranscender()
    coordinator = AdversarialLoopCoordinator(transcender=adaptive)

    result = coordinator.run_dialectical_loop(
        plan_id="IMP-0031-ROUND2",
        plan_text="Iniciar pool de workers sem controle de lock e subprocess sem timeout.",
        risk_level="HIGH",
    )

    assert adaptive.calls == 2
    assert result.verdict.status == RedTeamVerdictStatus.VERIFIED
    assert result.verdict.iterations_completed == 2
    assert result.verdict.unresolved_vulnerabilities == []
    assert result.re_verification is not None
    assert result.re_verification.is_blocked is False


@pytest.mark.parametrize(
    ("weakness_title", "expected_category"),
    [
        (
            "Vulnerabilidade Crítica de Concorrência e Race Condition",
            RedTeamThreatCategory.CONCURRENCY,
        ),
        (
            "Ponto Único de Falha (SPOF) e Ausência de Mecanismo de Rollback",
            RedTeamThreatCategory.FAULT_TOLERANCE,
        ),
        (
            "Privilégios Excessivos e Ausência de Circuit Breaker em Ferramentas MCP",
            RedTeamThreatCategory.PRIVILEGE_MCP,
        ),
        (
            "Timeouts Indefinidos em Rede/Subprocessos e Erros Silenciosos",
            RedTeamThreatCategory.NETWORK_TIMEOUTS,
        ),
        (
            "Mutabilidade In-Place e Ausência de Contratos Tipados Pydantic v2",
            RedTeamThreatCategory.DATA_INTEGRITY,
        ),
    ],
)
def test_re_verify_infers_all_threat_categories_without_attack_report(
    weakness_title: str,
    expected_category: RedTeamThreatCategory,
) -> None:
    """Phase 1.7 with attack_report=None must infer all 5 rule titles and check controls."""
    red_team = AdversarialRedTeam()
    plan = TranscendencePlan(
        plan_id="IMP-0031-INFER",
        hardenings=[
            TranscendenceHardening(
                vulnerability_id="VULN-001",
                original_weakness=weakness_title,
                transcendence_strategy="Observabilidade simples",
                formal_invariant="Todas as chamadas devem emitir logs no stdout.",
                resilience_mechanism="adicionar logs no stdout",
            )
        ],
        transcended_architecture="Sistema instrumentado apenas com logs no stdout.",
        structural_invariants=["Todas as chamadas devem emitir logs no stdout."],
        residual_risk="LOW",
    )

    re_report = red_team.re_verify(plan)
    assert re_report.is_blocked is True
    assert re_report.total_vulnerabilities >= 1
    assert expected_category in {v.category for v in re_report.vulnerabilities}


def test_re_verify_catches_same_category_defect_in_transcended_architecture() -> None:
    """Same-category defect phrases in transcended_architecture must not be masked by mitigation."""
    red_team = AdversarialRedTeam()
    vuln = RedTeamVulnerability(
        id="VULN-001",
        category=RedTeamThreatCategory.CONCURRENCY,
        severity=RedTeamVulnerabilitySeverity.CRITICAL,
        title="Vulnerabilidade Crítica de Concorrência e Race Condition",
        description="Acesso concorrente sem controle de lock.",
        attack_vector="Corrupção de estado compartilhado.",
        target_component="worker pool",
    )
    attack_report = RedTeamAttackReport(
        plan_id="IMP-0031-SAME-CAT",
        total_vulnerabilities=1,
        vulnerabilities=[vuln],
        highest_severity=RedTeamVulnerabilitySeverity.CRITICAL,
        attack_narrative="Concorrência sem lock.",
        is_blocked=True,
    )
    plan = TranscendencePlan(
        plan_id="IMP-0031-SAME-CAT",
        hardenings=[
            TranscendenceHardening(
                vulnerability_id="VULN-001",
                original_weakness=vuln.title,
                transcendence_strategy="Sincronização Reentrante",
                formal_invariant="Cache protegido por threading.RLock().",
                resilience_mechanism="threading.RLock() + ContextVars.",
            )
        ],
        transcended_architecture=(
            "Workers usam threading.RLock() no cache, mas fila principal opera "
            "sem controle de lock gerando race condition e deadlock."
        ),
        structural_invariants=["Cache protegido por threading.RLock()."],
        residual_risk="LOW",
    )

    re_report = red_team.re_verify(plan, attack_report=attack_report)
    assert re_report.is_blocked is True
    assert re_report.total_vulnerabilities >= 1
    assert RedTeamThreatCategory.CONCURRENCY in {v.category for v in re_report.vulnerabilities}


class _SpyRedTeam(AdversarialRedTeam):
    """Spy RedTeam recording attack_report arguments passed to re_verify across rounds."""

    def __init__(self) -> None:
        self.received_attack_reports: list[RedTeamAttackReport | None] = []

    def re_verify(
        self,
        transcendence_plan: TranscendencePlan,
        attack_report: RedTeamAttackReport | None = None,
    ) -> RedTeamAttackReport:
        self.received_attack_reports.append(attack_report)
        return super().re_verify(transcendence_plan, attack_report=attack_report)


class _Round1NewThreatTranscender(ArchitectureTranscender):
    """Round 1 resolves initial flaw but introduces a new timeout threat in architecture."""

    def __init__(self) -> None:
        self.calls = 0

    def transcend(
        self,
        plan_id: str,
        original_plan: str,
        attack_report: RedTeamAttackReport,
    ) -> TranscendencePlan:
        self.calls += 1
        if self.calls == 1:
            base = super().transcend(plan_id, original_plan, attack_report)
            return base.model_copy(
                update={
                    "transcended_architecture": (
                        f"{base.transcended_architecture}\nExecutar subprocess sem timeout."
                    )
                }
            )
        return super().transcend(plan_id, original_plan, attack_report)


def test_coordinator_passes_refined_current_attack_to_round2_re_verify() -> None:
    """Round 2 re_verify must receive refined current_attack including round-1 residual flaws."""
    spy_red_team = _SpyRedTeam()
    transcender = _Round1NewThreatTranscender()
    coordinator = AdversarialLoopCoordinator(red_team=spy_red_team, transcender=transcender)

    result = coordinator.run_dialectical_loop(
        plan_id="IMP-0031-SPY",
        plan_text="Iniciar pool de workers sem controle de lock.",
        risk_level="HIGH",
    )

    assert len(spy_red_team.received_attack_reports) == 2
    round1_report = spy_red_team.received_attack_reports[0]
    round2_report = spy_red_team.received_attack_reports[1]
    assert round1_report is not None
    assert round2_report is not None
    assert round1_report.total_vulnerabilities == 1
    assert round2_report.total_vulnerabilities >= 2
    assert any(
        v.category == RedTeamThreatCategory.NETWORK_TIMEOUTS for v in round2_report.vulnerabilities
    )
    assert result.verdict.status == RedTeamVerdictStatus.VERIFIED
    assert result.verdict.iterations_completed == 2


@pytest.mark.parametrize("bad_risk", ["", "UNKNOWN", "EXTREME"])
def test_re_verify_blocks_empty_or_unrecognized_residual_risk(bad_risk: str) -> None:
    """Phase 1.7 must fail closed for empty or unrecognized residual_risk declarations."""
    red_team = AdversarialRedTeam()
    plan = TranscendencePlan(
        plan_id="IMP-0031-BAD-RISK",
        hardenings=[],
        transcended_architecture="Arquitetura baseline.",
        structural_invariants=[],
        residual_risk=bad_risk,
    )

    re_report = red_team.re_verify(plan)
    assert re_report.is_blocked is True
    assert re_report.total_vulnerabilities >= 1


def test_re_verify_rejects_short_deadlock_and_negated_invariant_reflections() -> None:
    """Short invariant tokens must not match substrings like 'deadlock' or negated phrases."""
    red_team = AdversarialRedTeam()
    for bad_invariant in ("Avoid deadlock entirely", "Operar sem lock compartilhado"):
        plan = TranscendencePlan(
            plan_id="IMP-0031-INV",
            hardenings=[
                TranscendenceHardening(
                    vulnerability_id="VULN-001",
                    original_weakness="Race condition",
                    transcendence_strategy="Sincronização",
                    formal_invariant="lock",
                    resilience_mechanism="threading.RLock()",
                )
            ],
            transcended_architecture="Arquitetura protegida.",
            structural_invariants=[bad_invariant],
            residual_risk="LOW",
        )
        re_report = red_team.re_verify(plan)
        assert re_report.is_blocked is True
        assert re_report.total_vulnerabilities >= 1
