"""
Tri-Phase Adversarial Loop Engine (IMP-0026 / ADR-028).
Dialectical architecture: Phase 1.5 Red Team Attack -> Phase 1.6 Transcendence -> Phase 1.7 Re-Verification.
"""

from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any

from corporate_engineer.models import (
    AdversarialVerdict,
    ChaosTestCase,
    DialecticalLoopResult,
    RedTeamAttackReport,
    RedTeamThreatCategory,
    RedTeamVerdictStatus,
    RedTeamVulnerability,
    RedTeamVulnerabilitySeverity,
    TranscendenceHardening,
    TranscendencePlan,
)

logger = logging.getLogger(__name__)

# Heuristic threat pattern definitions across 5 corporate axes
_THREAT_RULES: list[dict[str, Any]] = [
    {
        "category": RedTeamThreatCategory.CONCURRENCY,
        "patterns": (
            [r"threads?\b", r"concorr[eê]ncia\b", r"concorrentes?\b", r"workers?\b"]
            + [r"sem\s+controle\s+de\s+lock", r"sem\s+locks?", r"race\s+conditions?"]
            + [r"deadlocks?", r"pool\s+de\s+workers"]
        ),
        "severity": RedTeamVulnerabilitySeverity.CRITICAL,
        "title": "Vulnerabilidade Crítica de Concorrência e Race Condition",
        "description": "Threads ou workers assíncronos operando em concorrência sem isolamento ou mecanismos reentrantes de sincronização.",
        "attack_vector": "Sobrecarga concorrente resultando em corrupção de estado compartilhado ou deadlocks em tempo de execução.",
        "target_component": "threading / worker pool",
    },
    {
        "category": RedTeamThreatCategory.FAULT_TOLERANCE,
        "patterns": (
            [r"sem\s+fallback\b", r"sem\s+tratamento\s+de\s+erro", r"ponto\s+[uú]nico\s+de\s+falha"]
            + [r"spof\b", r"sem\s+rollback\b", r"falha\s+catastr[oó]fica", r"revers[aã]o\s+ausente"]
        ),
        "severity": RedTeamVulnerabilitySeverity.HIGH,
        "title": "Ponto Único de Falha (SPOF) e Ausência de Mecanismo de Rollback",
        "description": "Fluxo crítico sem contingência, fallback determinístico ou reversão atômica de arquivos e estado em caso de aborto.",
        "attack_vector": "Injeção de falha inesperada em nó intermediário deixando o repositório em estado inconsistente.",
        "target_component": "fault tolerance & rollback sandbox",
    },
    {
        "category": RedTeamThreatCategory.PRIVILEGE_MCP,
        "patterns": (
            [r"privil[eé]gios?\s+de\s+root", r"root\s+no\s+servidor", r"sem\s+circuit\s+breaker"]
            + [r"ferramentas?\s+sem\s+limite", r"permiss[oõ]es?\s+excessivas?"]
            + [r"credenciais?\s+expostas?", r"tokens?\s+abertos?"]
        ),
        "severity": RedTeamVulnerabilitySeverity.CRITICAL,
        "title": "Privilégios Excessivos e Ausência de Circuit Breaker em Ferramentas MCP",
        "description": "Execução de ferramentas de sistema/MCP sem isolamento de privilégio, limites de escopo ou Circuit Breakers por ferramenta.",
        "attack_vector": "Esgotamento de quota, loops infinitos de chamadas ou vazamento de credenciais através de payloads não sanitizados.",
        "target_component": "mcp client / tool hub",
    },
    {
        "category": RedTeamThreatCategory.NETWORK_TIMEOUTS,
        "patterns": (
            [r"sem\s+configurar\s+timeout", r"sem\s+timeout\b", r"endpoints?\s+externos?\s+sem"]
            + [r"subprocess\s+sem\s+timeout", r"processos?\s+travados?"]
            + [r"swallowing\s+silencioso", r"engolir\s+erros?"]
        ),
        "severity": RedTeamVulnerabilitySeverity.HIGH,
        "title": "Timeouts Indefinidos em Rede/Subprocessos e Erros Silenciosos",
        "description": "Chamadas de rede HTTP ou subprocessos executando sem limites de tempo (timeouts) ou suprimindo exceções silenciosamente.",
        "attack_vector": "Atrasos no remote git ou APIs externas congelando o orquestrador permanentemente.",
        "target_component": "network client / subprocess runner",
    },
    {
        "category": RedTeamThreatCategory.DATA_INTEGRITY,
        "patterns": (
            [r"dicion[aá]rios?\s+mut[aá]veis?", r"sem\s+valida[cç][aã]o\s+de\s+esquema"]
            + [r"sem\s+pydantic", r"muta[cç][aã]o\s+in-place", r"par[aâ]metros?\s+soltos?"]
            + [r"any\s+sem\s+tipo"]
        ),
        "severity": RedTeamVulnerabilitySeverity.HIGH,
        "title": "Mutabilidade In-Place e Ausência de Contratos Tipados Pydantic v2",
        "description": "Manipulação de estruturas de dados mutáveis sem validação de tipos ou esquemas formais, contrariando o princípio da imutabilidade.",
        "attack_vector": "Injeção de payloads com tipos incompatíveis corrompendo estados internos sem acionar falha rápida.",
        "target_component": "models & data contracts",
    },
]

# Transcendence strategy dictionary mapping threat categories to structural invariants
_TRANSCENDENCE_STRATEGIES: dict[RedTeamThreatCategory, dict[str, str]] = {
    RedTeamThreatCategory.CONCURRENCY: {
        "strategy": "Sincronização Reentrante e Concorrência Segura",
        "invariant": "Todo acesso concorrente a estado compartilhado deve ser protegido por threading.RLock() e estruturas imutáveis.",
        "mechanism": "threading.RLock() + ContextVars com isolamento atômico de workers.",
    },
    RedTeamThreatCategory.FAULT_TOLERANCE: {
        "strategy": "Sandboxing Atômico e Fallback Determinístico",
        "invariant": "Toda mutação em disco deve operar sob AtomicFileSandbox garantindo reversão determinística via atexit/sinais.",
        "mechanism": "AtomicFileSandbox + Fallback defensivo com logging explícito de incidentes.",
    },
    RedTeamThreatCategory.PRIVILEGE_MCP: {
        "strategy": "Princípio do Menor Privilégio e Circuit Breakers por Ferramenta",
        "invariant": "Cada ferramenta MCP é encapsulada por CircuitBreaker individual com sanitização Zero-Secret Guard.",
        "mechanism": "CircuitBreaker com estados CLOSED/OPEN/HALF_OPEN + isolamento semântico via Sistema 1.",
    },
    RedTeamThreatCategory.NETWORK_TIMEOUTS: {
        "strategy": "Timeouts Explícitos e Tratamento Rigoroso de Exceções",
        "invariant": "Toda operação de I/O de rede ou subprocesso deve definir timeout estrito com tratamento explícito de TimeoutExpired.",
        "mechanism": "timeout=15.0s (configurável via env) + backoff exponencial e captura de exceções tipadas.",
    },
    RedTeamThreatCategory.DATA_INTEGRITY: {
        "strategy": "Contratos Tipados Estritos e Imutabilidade com Pydantic v2",
        "invariant": "Todas as estruturas de entrada e saída devem utilizar modelos Pydantic v2 validados e imutáveis.",
        "mechanism": "BaseModel Pydantic v2 com validação antecipada e cópias defensivas em updates.",
    },
}


_MAX_DIALECTICAL_ROUNDS = 2
_SEVERITY_RANK: dict[RedTeamVulnerabilitySeverity, int] = {
    RedTeamVulnerabilitySeverity.LOW: 0,
    RedTeamVulnerabilitySeverity.MEDIUM: 1,
    RedTeamVulnerabilitySeverity.HIGH: 2,
    RedTeamVulnerabilitySeverity.CRITICAL: 3,
}
_PLACEHOLDER_TOKENS: frozenset[str] = frozenset(
    {"", "todo", "tbd", "fixme", "xxx", "none", "null", "nil", "n/a", "na", "ok", "done"}
    | {"nenhum", "nenhuma", "vazio", "placeholder", "pending", "pendente", "stub", "mock"}
    | {"dummy", "skip", "skipped", "pass"}
)
_PLACEHOLDER_PATTERN = re.compile(r"\b(?:tbd|fixme|placeholder|not\s+implemented|a\s+definir)\b")
_TODO_PLACEHOLDER_RE = re.compile(r"\bTODO\b|\btodo\s*:")
_NEGATION_PREFIX_RE = re.compile(
    r"(?:sem\s+controle\s+de|sem\s+configurar|aus[eê]ncia\s+de|falta\s+de|"
    r"sem|n[aã]o|without|no|missing|lacking)\s+$"
)
_NEGATION_SUFFIX_RE = re.compile(
    r"^\s*(?:indefinid[oa]s?|ausentes?|missing|disabled|desabilitad[oa]s?|bypass)"
)

_BENIGN_TOPIC_PATTERNS: frozenset[str] = frozenset(
    {r"threads?\b", r"concorr[eê]ncia\b", r"concorrentes?\b", r"workers?\b", r"pool\s+de\s+workers"}
)
_CATEGORY_TITLE_PATTERNS: dict[RedTeamThreatCategory, tuple[str, ...]] = {
    RedTeamThreatCategory.CONCURRENCY: (r"concorr[eê]ncia", r"race\s+condition", r"deadlock"),
    RedTeamThreatCategory.FAULT_TOLERANCE: (
        (r"ponto\s+[uú]nico\s+de\s+falha", r"\bspof\b", r"rollback", r"fallback")
        + (r"toler[aâ]ncia",)
    ),
    RedTeamThreatCategory.PRIVILEGE_MCP: (
        (r"privil[eé]gios?\s+excessivos?", r"circuit\s+breaker", r"ferramentas?\s+mcp")
        + (r"credenciais?",)
    ),
    RedTeamThreatCategory.NETWORK_TIMEOUTS: (
        (r"timeouts?\s+indefinidos?", r"erros?\s+silenciosos?", r"subprocess")
        + (r"swallowing", r"\btimeout\b")
    ),
    RedTeamThreatCategory.DATA_INTEGRITY: (
        (r"mutabilidade\s+in-place", r"contratos?\s+tipados?", r"pydantic")
        + (r"imutabilidade", r"valida[cç][aã]o\s+de\s+esquema")
    ),
}
_CATEGORY_MITIGATION_SIGNALS: dict[RedTeamThreatCategory, tuple[str, ...]] = {
    RedTeamThreatCategory.CONCURRENCY: (
        ("rlock", "lock", "mutex", "semaphore", "semáforo", "contextvar", "contextvars")
        + ("atomic", "atômico", "atômica", "immutable", "imutável", "imutáveis")
        + ("reentrant", "reentrante", "thread-safe", "asyncio.lock")
    ),
    RedTeamThreatCategory.FAULT_TOLERANCE: (
        ("sandbox", "atomicfilesandbox", "fallback", "rollback", "reversão", "reversao")
        + ("contingência", "contingencia", "retry", "checkpoint", "atexit", "idempotent")
    ),
    RedTeamThreatCategory.PRIVILEGE_MCP: (
        ("circuitbreaker", "circuit breaker", "circuit_breaker", "menor privilégio")
        + ("menor privilegio", "least privilege", "zero-secret", "sanitização", "sanitizacao")
        + ("sanitize", "rbac", "allowlist", "whitelist", "rate limit", "quota")
        + ("escopo restrito", "poda semântica")
    ),
    RedTeamThreatCategory.NETWORK_TIMEOUTS: (
        ("timeout", "timeouts", "timeoutexpired", "backoff", "deadline")
        + ("cancellation", "cancelamento", "read_timeout", "connect_timeout")
    ),
    RedTeamThreatCategory.DATA_INTEGRITY: (
        ("pydantic", "basemodel", "frozen", "schema", "esquema", "validação", "validacao")
        + ("validation", "imutabilidade", "immutability", "cópia defensiva")
        + ("cópias defensivas", "deepcopy", "type hint", "contratos tipados", "strict")
    ),
}


@dataclass
class _ReVerifyContext:
    """Mutable accumulator confined to a single Phase 1.7 re_verify pass."""

    valid_invariants: list[str]
    residual_vulns: list[RedTeamVulnerability] = field(default_factory=list)
    mitigated_categories: set[RedTeamThreatCategory] = field(default_factory=set)
    seen_ids: set[str] = field(default_factory=set)
    checked_hardening_ids: set[int] = field(default_factory=set)
    counter: int = 1

    def next_id(self, preferred: str = "") -> str:
        """Allocate a unique residual vulnerability ID."""
        candidate = preferred.strip()
        if candidate and candidate not in self.seen_ids:
            self.seen_ids.add(candidate)
            return candidate
        while f"RESIDUAL-{self.counter:03d}" in self.seen_ids:
            self.counter += 1
        generated = f"RESIDUAL-{self.counter:03d}"
        self.seen_ids.add(generated)
        self.counter += 1
        return generated

    def add_from_vuln(
        self,
        vuln: RedTeamVulnerability,
        title: str,
        description: str,
        severity: RedTeamVulnerabilitySeverity | None = None,
    ) -> None:
        """Record a residual vulnerability derived from an attack finding."""
        self.residual_vulns.append(
            RedTeamVulnerability(
                id=self.next_id(vuln.id),
                category=vuln.category,
                severity=severity or vuln.severity,
                title=title,
                description=description,
                attack_vector=vuln.attack_vector,
                target_component=vuln.target_component,
            )
        )


def _compute_highest_severity(vulns: list[RedTeamVulnerability]) -> RedTeamVulnerabilitySeverity:
    """Return the highest severity present across a list of vulnerabilities."""
    if not vulns:
        return RedTeamVulnerabilitySeverity.LOW
    return max(vulns, key=lambda v: _SEVERITY_RANK[v.severity]).severity


def _is_blocking_severity(severity: RedTeamVulnerabilitySeverity) -> bool:
    """Determine whether the given severity blocks downstream execution."""
    return severity in (RedTeamVulnerabilitySeverity.CRITICAL, RedTeamVulnerabilitySeverity.HIGH)


def _is_placeholder_or_empty(text: str) -> bool:
    """Return True if text is empty, trivial, or uses a placeholder marker."""
    stripped = text.strip()
    if not stripped:
        return True
    normalized = stripped.lower().strip(".:;-!?[]()")
    if normalized in _PLACEHOLDER_TOKENS or len(normalized) < 4:
        return True
    return bool(_TODO_PLACEHOLDER_RE.search(stripped) or _PLACEHOLDER_PATTERN.search(normalized))


def _has_mitigation_signal(text: str, category: RedTeamThreatCategory) -> bool:
    """Verify text contains at least one positive, non-negated category control signal."""
    text_lower = text.lower()
    for signal in _CATEGORY_MITIGATION_SIGNALS.get(category, ()):
        for match in re.finditer(rf"\b{re.escape(signal)}\b", text_lower):
            prefix = text_lower[max(0, match.start() - 32) : match.start()]
            suffix = text_lower[match.end() : min(len(text_lower), match.end() + 24)]
            if not _NEGATION_PREFIX_RE.search(prefix) and not _NEGATION_SUFFIX_RE.search(suffix):
                return True
    return False


def _contains_non_negated(needle: str, haystack: str) -> bool:
    """Return True if needle appears at word/token boundaries without a negation prefix."""
    if needle == haystack:
        return not _NEGATION_PREFIX_RE.search(haystack)
    for match in re.finditer(rf"(?<!\w){re.escape(needle)}(?!\w)", haystack):
        prefix = haystack[max(0, match.start() - 32) : match.start()]
        if not _NEGATION_PREFIX_RE.search(prefix):
            return True
    return False


def _is_invariant_reflected(formal_invariant: str, valid_invariants: list[str]) -> bool:
    """Check whether a hardening's formal invariant is reflected in structural_invariants."""
    if _is_placeholder_or_empty(formal_invariant) or not valid_invariants:
        return False
    norm_target = " ".join(formal_invariant.lower().split())
    for inv in valid_invariants:
        norm_inv = " ".join(inv.lower().split())
        if _contains_non_negated(norm_target, norm_inv) or (
            len(norm_inv) >= 8 and _contains_non_negated(norm_inv, norm_target)
        ):
            return True
    return False


def _infer_category_from_text(text: str) -> RedTeamThreatCategory | None:
    """Infer a threat category from weakness/plan text using rules and title cues."""
    text_lower = text.lower()
    for rule in _THREAT_RULES:
        if rule["title"].lower() == text_lower.strip() or any(
            re.search(pattern, text_lower) for pattern in rule["patterns"]
        ):
            cat = rule["category"]
            return cat if isinstance(cat, RedTeamThreatCategory) else None
    for category, patterns in _CATEGORY_TITLE_PATTERNS.items():
        if any(re.search(pattern, text_lower) for pattern in patterns):
            return category
    return None


def _validate_hardening(
    hardening: TranscendenceHardening,
    valid_invariants: list[str],
    expected_category: RedTeamThreatCategory | None = None,
) -> list[str]:
    """Audit a single TranscendenceHardening for substance, invariants, and category controls."""
    checks = (
        ("estratégia de transcendência", hardening.transcendence_strategy),
        ("invariante formal", hardening.formal_invariant),
        ("mecanismo de resiliência", hardening.resilience_mechanism),
    )
    reasons = [
        f"{label} ausente ou placeholder" for label, val in checks if _is_placeholder_or_empty(val)
    ]
    if not _is_invariant_reflected(hardening.formal_invariant, valid_invariants):
        reasons.append("invariante formal não refletida em structural_invariants")

    cat = expected_category or _infer_category_from_text(hardening.original_weakness)
    if cat is not None:
        combined = f"{hardening.transcendence_strategy} {hardening.formal_invariant} {hardening.resilience_mechanism}"
        if not _has_mitigation_signal(combined, cat):
            reasons.append(f"controles arquiteturais insuficientes para categoria {cat.value}")
    return reasons


class AdversarialRedTeam:
    """Phase 1.5 and Phase 1.7: Attacks plans and re-verifies transcended architectures."""

    def attack(
        self, plan_id: str, plan_text: str, context: dict[str, Any] | None = None
    ) -> RedTeamAttackReport:
        """Execute Phase 1.5 adversarial attack across 5 threat axes."""
        vulnerabilities: list[RedTeamVulnerability] = []
        combined_text = plan_text.lower() + (f" {str(context).lower()}" if context else "")
        for rule in _THREAT_RULES:
            if any(re.search(p, combined_text) for p in rule["patterns"]):
                vulnerabilities.append(
                    RedTeamVulnerability(
                        id=f"VULN-{len(vulnerabilities) + 1:03d}",
                        category=rule["category"],
                        severity=rule["severity"],
                        title=rule["title"],
                        description=rule["description"],
                        attack_vector=rule["attack_vector"],
                        target_component=rule["target_component"],
                    )
                )
        highest = _compute_highest_severity(vulnerabilities)
        is_blocked = _is_blocking_severity(highest)
        narrative = (
            f"[analysis_mode=heuristic-pattern-matcher] O Red Team identificou "
            f"{len(vulnerabilities)} vulnerabilidades conceituais no plano {plan_id}. "
            f"Severidade máxima: {highest.value}. "
            f"Bloqueio de avanço para implementação: {'SIM' if is_blocked else 'NÃO'}."
        )
        return RedTeamAttackReport(
            plan_id=plan_id,
            total_vulnerabilities=len(vulnerabilities),
            vulnerabilities=vulnerabilities,
            highest_severity=highest,
            attack_narrative=narrative,
            is_blocked=is_blocked,
        )

    def re_verify(
        self,
        transcendence_plan: TranscendencePlan,
        attack_report: RedTeamAttackReport | None = None,
    ) -> RedTeamAttackReport:
        """Execute Phase 1.7: Re-verify hardenings, invariants, residual risk, and architecture."""
        valid_invariants = [
            inv.strip()
            for inv in transcendence_plan.structural_invariants
            if not _is_placeholder_or_empty(inv)
        ]
        ctx = _ReVerifyContext(valid_invariants=valid_invariants)

        self._check_residual_risk(transcendence_plan, ctx)
        if attack_report is not None:
            self._audit_attack_coverage(attack_report, transcendence_plan.hardenings, ctx)
        self._audit_remaining_hardenings(transcendence_plan.hardenings, ctx)
        self._scan_architecture_threats(transcendence_plan.transcended_architecture, ctx)

        highest = _compute_highest_severity(ctx.residual_vulns)
        is_blocked = _is_blocking_severity(highest)
        narrative = self._build_reverify_narrative(transcendence_plan, ctx, highest, is_blocked)

        return RedTeamAttackReport(
            plan_id=transcendence_plan.plan_id,
            total_vulnerabilities=len(ctx.residual_vulns),
            vulnerabilities=ctx.residual_vulns,
            highest_severity=highest,
            attack_narrative=narrative,
            is_blocked=is_blocked,
        )

    @staticmethod
    def _check_residual_risk(plan: TranscendencePlan, ctx: _ReVerifyContext) -> None:
        risk_level = plan.residual_risk.strip().upper()
        if risk_level in ("LOW", "MEDIUM", "NONE"):
            return
        severity = (
            RedTeamVulnerabilitySeverity.CRITICAL
            if risk_level == "CRITICAL"
            else RedTeamVulnerabilitySeverity.HIGH
        )
        label = risk_level or "<VAZIO>"
        ctx.residual_vulns.append(
            RedTeamVulnerability(
                id=ctx.next_id("RESIDUAL-RISK"),
                category=RedTeamThreatCategory.FAULT_TOLERANCE,
                severity=severity,
                title=f"Risco Residual Não Aceitável ({label})",
                description=f"TranscendencePlan declarou residual_risk='{plan.residual_risk}', bloqueando Fase 1.7.",
                attack_vector="Risco residual elevado ou não reconhecido aceito sem blindagem.",
                target_component="transcendence_plan.residual_risk",
            )
        )

    @classmethod
    def _audit_attack_coverage(
        cls,
        attack_report: RedTeamAttackReport,
        hardenings: list[TranscendenceHardening],
        ctx: _ReVerifyContext,
    ) -> None:
        hardenings_by_id: dict[str, list[TranscendenceHardening]] = {}
        for hardening in hardenings:
            hardenings_by_id.setdefault(hardening.vulnerability_id, []).append(hardening)
        for vuln in attack_report.vulnerabilities:
            matched = hardenings_by_id.get(vuln.id, [])
            if not matched:
                ctx.add_from_vuln(
                    vuln,
                    title=f"Vulnerabilidade Não Coberta: {vuln.title}",
                    description=f"{vuln.description} (Sem TranscendenceHardening cobrindo '{vuln.id}')",
                )
                continue
            cls._evaluate_matched_hardenings(vuln, matched, ctx)

    @staticmethod
    def _evaluate_matched_hardenings(
        vuln: RedTeamVulnerability,
        matched: list[TranscendenceHardening],
        ctx: _ReVerifyContext,
    ) -> None:
        failure_reasons: list[str] = []
        for hardening in matched:
            ctx.checked_hardening_ids.add(id(hardening))
            failure_reasons.extend(
                _validate_hardening(hardening, ctx.valid_invariants, vuln.category)
            )
        if not failure_reasons:
            ctx.mitigated_categories.add(vuln.category)
            return
        eff_sev = (
            vuln.severity
            if _is_blocking_severity(vuln.severity)
            else RedTeamVulnerabilitySeverity.HIGH
        )
        ctx.add_from_vuln(
            vuln,
            title=f"Mitigação Insuficiente para {vuln.id}: {vuln.title}",
            description="; ".join(dict.fromkeys(failure_reasons)),
            severity=eff_sev,
        )

    @classmethod
    def _audit_remaining_hardenings(
        cls, hardenings: list[TranscendenceHardening], ctx: _ReVerifyContext
    ) -> None:
        for hardening in hardenings:
            if id(hardening) in ctx.checked_hardening_ids:
                continue
            reasons = _validate_hardening(hardening, ctx.valid_invariants)
            inferred_cat = _infer_category_from_text(hardening.original_weakness)
            if reasons:
                ctx.residual_vulns.append(
                    RedTeamVulnerability(
                        id=ctx.next_id(hardening.vulnerability_id),
                        category=inferred_cat or RedTeamThreatCategory.FAULT_TOLERANCE,
                        severity=RedTeamVulnerabilitySeverity.HIGH,
                        title=f"Hardening Hollow ou Sem Invariante ({hardening.vulnerability_id or 'sem ID'})",
                        description="; ".join(dict.fromkeys(reasons)),
                        attack_vector="Defesa superficial ou placeholder sem invariante formal.",
                        target_component="transcendence_plan.hardenings",
                    )
                )
                continue
            cls._register_valid_hardening_signals(hardening, inferred_cat, ctx)

    @staticmethod
    def _register_valid_hardening_signals(
        hardening: TranscendenceHardening,
        inferred_cat: RedTeamThreatCategory | None,
        ctx: _ReVerifyContext,
    ) -> None:
        if inferred_cat is not None:
            ctx.mitigated_categories.add(inferred_cat)
        combined = f"{hardening.transcendence_strategy} {hardening.formal_invariant} {hardening.resilience_mechanism}"
        for cat in RedTeamThreatCategory:
            if _has_mitigation_signal(combined, cat):
                ctx.mitigated_categories.add(cat)

    @staticmethod
    def _scan_architecture_threats(transcended_architecture: str, ctx: _ReVerifyContext) -> None:
        arch_lower = transcended_architecture.lower()
        if not arch_lower.strip():
            return
        flagged = {
            v.category
            for v in ctx.residual_vulns
            if v.target_component != "transcendence_plan.residual_risk"
        }
        for rule in _THREAT_RULES:
            rule_cat = rule["category"]
            if rule_cat in flagged:
                continue
            patterns = (
                [p for p in rule["patterns"] if p not in _BENIGN_TOPIC_PATTERNS]
                if rule_cat in ctx.mitigated_categories
                else rule["patterns"]
            )
            if any(re.search(pattern, arch_lower) for pattern in patterns):
                ctx.residual_vulns.append(
                    RedTeamVulnerability(
                        id=ctx.next_id(),
                        category=rule_cat,
                        severity=rule["severity"],
                        title=f"Ameaça Não Mitigada na Arquitetura Transcendida: {rule['title']}",
                        description=f"{rule['description']} (Detectado em transcended_architecture sem invariante)",
                        attack_vector=rule["attack_vector"],
                        target_component="transcendence_plan.transcended_architecture",
                    )
                )

    @staticmethod
    def _build_reverify_narrative(
        plan: TranscendencePlan,
        ctx: _ReVerifyContext,
        highest: RedTeamVulnerabilitySeverity,
        is_blocked: bool,
    ) -> str:
        prefix = (
            f"[analysis_mode=heuristic-pattern-matcher] "
            f"Re-verificação adversarial da Fase 1.7 para o plano {plan.plan_id}: "
        )
        stats = f"{len(plan.hardenings)} hardenings e {len(ctx.valid_invariants)} invariantes (residual_risk={plan.residual_risk})"
        if not ctx.residual_vulns:
            return f"{prefix}{stats} auditados com 0 falhas residuais. Selo concedido."
        ids = ", ".join(
            f"{v.id}({v.category.value}/{v.severity.value})" for v in ctx.residual_vulns
        )
        return (
            f"{prefix}{len(ctx.residual_vulns)} falhas residuais detectadas [{ids}] após "
            f"auditoria de {stats}. Severidade máxima: {highest.value}. "
            f"Bloqueio: {'SIM' if is_blocked else 'NÃO'}."
        )

    def generate_chaos_matrix(self, transcendence_plan: TranscendencePlan) -> list[ChaosTestCase]:
        """Synthesize mandatory Chaos Test cases for Shift-Left TDD based on hardenings."""
        chaos_cases = [
            ChaosTestCase(
                case_id=f"CHAOS-{i:03d}",
                vulnerability_id=h.vulnerability_id,
                name=f"Injeção de Caos: {h.transcendence_strategy}",
                category="CHAOS",
                injection_trigger=f"Injetar falha artificial simulando {h.original_weakness.lower()}",
                expected_behavior=(
                    f"Sistema contém falha via {h.resilience_mechanism} e preserva invariante: "
                    f"{h.formal_invariant}"
                ),
                tdd_scenario=f"test_chaos_{h.vulnerability_id.lower().replace('-', '_')}_{i}",
            )
            for i, h in enumerate(transcendence_plan.hardenings, start=1)
        ]
        if not chaos_cases:
            chaos_cases.append(
                ChaosTestCase(
                    case_id="CHAOS-001",
                    vulnerability_id="",
                    name="Injeção de Caos Baseline: Timeout e Cancelamento",
                    category="CHAOS",
                    injection_trigger="Simular interrupção abrupta de sinal (SIGINT/Timeout)",
                    expected_behavior="Garante que recursos abertos sejam encerrados limpos e sem vazamentos",
                    tdd_scenario="test_chaos_baseline_cancellation",
                )
            )
        return chaos_cases


class ArchitectureTranscender:
    """Phase 1.6: Transcends vulnerabilities into formal invariants and immune architectures."""

    def transcend(
        self,
        plan_id: str,
        original_plan: str,
        attack_report: RedTeamAttackReport,
    ) -> TranscendencePlan:
        """Synthesize dialectical transcendence plan resolving all detected flaws."""
        hardenings: list[TranscendenceHardening] = []
        structural_invariants: list[str] = []

        for vuln in attack_report.vulnerabilities:
            mapping = _TRANSCENDENCE_STRATEGIES.get(
                vuln.category,
                {
                    "strategy": "Defesa em Profundidade e Imutabilidade",
                    "invariant": "Todo dado externo deve ser validado estritamente em fronteiras de sistema.",
                    "mechanism": "Contratos Pydantic v2 e isolamento de escopo.",
                },
            )

            hardenings.append(
                TranscendenceHardening(
                    vulnerability_id=vuln.id,
                    original_weakness=vuln.title,
                    transcendence_strategy=mapping["strategy"],
                    formal_invariant=mapping["invariant"],
                    resilience_mechanism=mapping["mechanism"],
                )
            )
            structural_invariants.append(mapping["invariant"])

        dedup_invariants = list(dict.fromkeys(structural_invariants))
        return TranscendencePlan(
            plan_id=plan_id,
            hardenings=hardenings,
            transcended_architecture=self._build_arch_summary(
                plan_id, hardenings, dedup_invariants
            ),
            structural_invariants=dedup_invariants,
            residual_risk="LOW",
        )

    @staticmethod
    def _build_arch_summary(
        plan_id: str, hardenings: list[TranscendenceHardening], dedup_invariants: list[str]
    ) -> str:
        """Build an accurate architectural summary matching active hardenings or baseline."""
        if not hardenings:
            return (
                f"Arquitetura Baseline Verificada para {plan_id}:\n"
                f"- Invariantes Formais Ativas: 0 (nenhuma vulnerabilidade detectada na Fase 1.5).\n"
                f"- Postura de Resiliência: Execução determinística com contratos Pydantic v2 preservados."
            )
        mechanisms = "; ".join(dict.fromkeys(h.resilience_mechanism for h in hardenings))
        strategies = "; ".join(dict.fromkeys(h.transcendence_strategy for h in hardenings))
        return (
            f"Arquitetura Transcendida para {plan_id}:\n"
            f"- Invariantes Formais Ativas: {len(dedup_invariants)}\n"
            f"- Estratégias Aplicadas: {strategies}\n"
            f"- Mecanismos de Resiliência: {mechanisms}"
        )


class AdversarialLoopCoordinator:
    """Master Coordinator for Tri-Phase Adversarial Loop (1.5 -> 1.6 -> 1.7)."""

    def __init__(
        self,
        red_team: AdversarialRedTeam | None = None,
        transcender: ArchitectureTranscender | None = None,
    ) -> None:
        self.red_team = red_team or AdversarialRedTeam()
        self.transcender = transcender or ArchitectureTranscender()

    def run_dialectical_loop(
        self,
        plan_id: str,
        plan_text: str,
        context: dict[str, Any] | None = None,
        risk_level: str = "MEDIUM",
        force_attack: bool = False,
    ) -> DialecticalLoopResult:
        """Run the full 3-phase dialectical loop or evaluate fast-path bypass."""
        start_time = time.perf_counter()

        # Fast-Path Bypass evaluation
        if not force_attack and self._is_bypass_eligible(plan_text, risk_level):
            return self._build_bypass_result(plan_id, start_time)

        # Phase 1.5: Adversarial Red Team Attack
        attack_report = self.red_team.attack(plan_id=plan_id, plan_text=plan_text, context=context)
        transcendence_plan, re_attack, iterations_completed = self._run_hardening_rounds(
            plan_id, plan_text, attack_report
        )

        status = (
            RedTeamVerdictStatus.VERIFIED
            if not re_attack.is_blocked
            else RedTeamVerdictStatus.HARDEN_REQUIRED
        )
        verdict = AdversarialVerdict(
            status=status,
            iterations_completed=iterations_completed,
            unresolved_vulnerabilities=[v.id for v in re_attack.vulnerabilities],
            chaos_matrix=self.red_team.generate_chaos_matrix(transcendence_plan),
            confidence_score=0.98 if status == RedTeamVerdictStatus.VERIFIED else 0.5,
        )
        return DialecticalLoopResult(
            plan_id=plan_id,
            initial_attack=attack_report,
            transcendence=transcendence_plan,
            re_verification=re_attack,
            verdict=verdict,
            duration_ms=round((time.perf_counter() - start_time) * 1000.0, 3),
        )

    def _run_hardening_rounds(
        self, plan_id: str, plan_text: str, attack_report: RedTeamAttackReport
    ) -> tuple[TranscendencePlan, RedTeamAttackReport, int]:
        """Run bounded iterative hardening (1.6 -> 1.7) up to _MAX_DIALECTICAL_ROUNDS."""
        current_attack = attack_report
        transcendence_plan: TranscendencePlan | None = None
        re_attack: RedTeamAttackReport | None = None
        iterations_completed = 0

        for iteration in range(1, _MAX_DIALECTICAL_ROUNDS + 1):
            iterations_completed = iteration
            transcendence_plan = self.transcender.transcend(plan_id, plan_text, current_attack)
            re_attack = self.red_team.re_verify(transcendence_plan, attack_report=current_attack)
            if not re_attack.is_blocked:
                break
            if iteration < _MAX_DIALECTICAL_ROUNDS:
                current_attack = self._build_refinement_report(attack_report, re_attack)

        if transcendence_plan is None or re_attack is None:
            raise RuntimeError("Dialectical loop executed zero iterations unexpectedly.")
        return transcendence_plan, re_attack, iterations_completed

    @staticmethod
    def _build_bypass_result(plan_id: str, start_time: float) -> DialecticalLoopResult:
        """Construct fast-path bypass result when low-risk heuristics qualify."""
        return DialecticalLoopResult(
            plan_id=plan_id,
            initial_attack=RedTeamAttackReport(
                plan_id=plan_id,
                attack_narrative=(
                    "[analysis_mode=heuristic-pattern-matcher] "
                    "Fast-Path Bypass: Nenhuma vulnerabilidade avaliada."
                ),
            ),
            verdict=AdversarialVerdict(
                status=RedTeamVerdictStatus.BYPASSED,
                iterations_completed=0,
                bypassed=True,
                bypass_reason=(
                    "[analysis_mode=heuristic-pattern-matcher] "
                    "Operação rotineira de baixo risco (Fast-Path Bypass ativado)"
                ),
                confidence_score=1.0,
            ),
            duration_ms=round((time.perf_counter() - start_time) * 1000.0, 3),
        )

    @staticmethod
    def _build_refinement_report(
        initial_attack: RedTeamAttackReport, re_attack: RedTeamAttackReport
    ) -> RedTeamAttackReport:
        """Merge initial vulnerabilities with residual flaws to guide round-2 hardening."""
        merged: list[RedTeamVulnerability] = list(initial_attack.vulnerabilities)
        known_ids = {v.id for v in merged}
        for vuln in re_attack.vulnerabilities:
            if vuln.id not in known_ids:
                merged.append(vuln)
                known_ids.add(vuln.id)
        highest = _compute_highest_severity(merged)
        return RedTeamAttackReport(
            plan_id=initial_attack.plan_id,
            total_vulnerabilities=len(merged),
            vulnerabilities=merged,
            highest_severity=highest,
            attack_narrative=f"Refinamento dialético (Rodada 2): {re_attack.attack_narrative}",
            is_blocked=_is_blocking_severity(highest),
        )

    def _is_bypass_eligible(self, plan_text: str, risk_level: str) -> bool:
        """Determine if a prompt or task qualifies for fast-path bypass."""
        if risk_level == "LOW":
            return True
        text_lower = plan_text.strip().lower()
        return text_lower.startswith(("pytest", "git status", "ruff", "mypy"))
