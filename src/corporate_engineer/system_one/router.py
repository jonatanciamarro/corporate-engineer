"""
High-level SystemOneRouter for capability intelligence, agent routing, and quality gate triage.
"""

import re
from typing import Any, ClassVar

from corporate_engineer.models import (
    ChoiceDecision,
    ContextPruningReport,
    FailureActionDecision,
    NoulDecision,
    SystemOneReport,
)
from corporate_engineer.system_one.base import SystemOneEngine
from corporate_engineer.system_one.heuristic_engine import HeuristicDecisionEngine


class SystemOneRouter:
    """Fachada unificada de inteligência de decisão rápida System One."""

    CANONICAL_AGENTS: ClassVar[dict[str, str]] = {
        "architect": "Design de arquitetura, contratos DTO Pydantic e formalização de ADRs",
        "tdd-guide": "Shift-left TDD, criação e execução de testes automatizados com pytest",
        "code-reviewer": "Revisão geral de código, qualidade, linters e imutabilidade",
        "python-reviewer": "Revisão especializada de padrões idiomáticos Python, typing e PEP 8",
        "security-reviewer": "Auditoria de segurança, escaneamento de secrets, OWASP e autenticação",
        "rag-pipeline-reviewer": "Indexação AST, análise de call graphs e code intelligence",
        "build-error-resolver": "Correção rápida e cirúrgica de falhas de build e quebras de testes",
        "refactor-cleaner": "Refatoração segura com preservação rigorosa de comportamento",
    }

    COMMIT_TYPES: ClassVar[dict[str, str]] = {
        "feat": "Nova funcionalidade, capacidade, recurso ou endpoint adicionado",
        "fix": "Correção de bug, falha, defeito, erro ou problema corrigido",
        "refactor": "Refatoração, limpeza, simplificação ou melhoria de código preservando comportamento",
        "test": "Adição, atualização ou execução de testes unitários, e2e e pytest",
        "docs": "Documentação, manuais, ADRs, guias, README e comentários",
        "chore": "Manutenção, dependências, build, linting, formatação e tooling",
    }

    def __init__(self, engine: SystemOneEngine | None = None) -> None:
        self.engine: SystemOneEngine = engine or HeuristicDecisionEngine()

    def route_agent(self, prompt: str) -> ChoiceDecision:
        """Roteia o prompt do usuário para o subagente especialista ideal."""
        return self.engine.decide_choice(
            state=prompt,
            choices=self.CANONICAL_AGENTS,
            instructions="Selecione o subagente especialista mais indicado para atender a esta solicitação.",
        )

    def assess_risk(self, code_diff_or_prompt: str) -> NoulDecision:
        """Avalia se a alteração de código ou prompt introduz alto risco estrutural ou de segurança."""
        return self.engine.decide_noul(
            state=code_diff_or_prompt,
            hypothesis="Esta modificação toca o núcleo da arquitetura, dados confidenciais ou introduz alto risco de regressão.",
            instructions="Avalie o risco estrutural, impacto de segurança e estabilidade da mudança.",
        )

    def triage_quality_gate(
        self,
        prompt: str = "",
        diff: str = "",
    ) -> SystemOneReport:
        """Realiza triagem completa do quality gate para despacho otimizado."""
        combined_state = f"PROMPT: {prompt}\nDIFF:\n{diff}".strip()

        questions: dict[str, Any] = {
            "target_agent": {
                "type": "choice",
                "criteria": self.CANONICAL_AGENTS,
                "instructions": "Determine o subagente responsável por conduzir esta tarefa.",
            },
            "is_high_risk": {
                "type": "noul",
                "hypothesis": "Esta mudança apresenta risco crítico e exige aprovação humana ou suíte completa de testes.",
            },
            "risk_score": {
                "type": "score",
                "rubric": ["Baixo Risco", "Risco Moderado", "Risco Crítico / Arquitetural"],
            },
        }

        report = self.engine.evaluate(combined_state, questions)

        # Ajusta propriedades convenientes de nível superior
        if "target_agent" in report.choices:
            report.suggested_agent = report.choices["target_agent"].choice

        if "is_high_risk" in report.nouls:
            is_risky = report.nouls["is_high_risk"].decision
            report.requires_human_approval = is_risky
            if is_risky:
                report.risk_level = "HIGH"

        return report

    def classify_commit(self, git_diff_or_message: str) -> ChoiceDecision:
        """Classifica o tipo de commit convencional com base no diff ou na descrição da mudança."""
        lowered = git_diff_or_message.lower()
        if (
            "test" in lowered
            and ("def test_" in lowered or "pytest" in lowered or "tests/" in lowered)
            and "src/" not in lowered
        ):
            return ChoiceDecision(
                choice="test",
                confidence=0.98,
                probabilities={"test": 0.98, "feat": 0.02},
                rationale="Alterações restritas a arquivos de teste e asserções pytest.",
            )
        return self.engine.decide_choice(
            state=git_diff_or_message,
            choices=self.COMMIT_TYPES,
            instructions="Classifique o tipo de commit convencional mais adequado para a mudança.",
        )

    def should_skip_node(self, node_name: str, context: str) -> NoulDecision:
        """Avalia se um nó específico da DAG pode ser ignorado com segurança no contexto fornecido."""
        lowered = context.lower()
        if "security" in node_name:
            if any(
                k in lowered
                for k in ["bearer", "auth", "token", "password", "secret", "models", "client"]
            ):
                return NoulDecision(
                    decision=False,
                    probability=0.08,
                    rationale=f"Nó '{node_name}' não pode ser ignorado: contexto envolve autenticação ou modelos centrais.",
                )
            if any(k in lowered for k in ["readme", "docs", "documentação", ".md", "apenas"]):
                return NoulDecision(
                    decision=True,
                    probability=0.92,
                    rationale=f"Nó '{node_name}' pode ser ignorado com segurança: contexto restrito a documentação.",
                )

        return self.engine.decide_noul(
            state=f"NÓ: {node_name}\nCONTEXTO: {context}",
            hypothesis=f"O nó de execução '{node_name}' é dispensável e pode ser ignorado com segurança.",
            instructions="Avalie se a execução deste nó é estritamente necessária.",
        )

    def triage_failure(
        self,
        node_name: str,
        error_message: str,
        traceback_snippet: str = "",
    ) -> FailureActionDecision:
        """Realiza triagem instantânea de falha de execução para decidir política de recuperação."""
        full_text = f"{node_name} {error_message} {traceback_snippet}".lower()
        if any(
            k in full_text
            for k in [
                "timeout",
                "timed out",
                "econnreset",
                "connection reset",
                "transitório",
                "retry",
            ]
        ):
            return FailureActionDecision(
                action="retry",
                confidence=0.9,
                target_agent=None,
                rationale="Falha de rede ou timeout transitório detectado; recomendada nova tentativa.",
            )
        if any(
            k in full_text
            for k in [
                "assertionerror",
                "test_",
                "pytest",
                "failed",
                "quebra",
                "build",
                "syntaxerror",
                "importerror",
            ]
        ):
            target = (
                "tdd-guide"
                if ("test" in full_text or "assert" in full_text)
                else "build-error-resolver"
            )
            return FailureActionDecision(
                action="dispatch_agent",
                confidence=0.95,
                target_agent=target,
                rationale=f"Erro de código ou quebra de teste detectado; despachando subagente '{target}'.",
            )
        return FailureActionDecision(
            action="rollback",
            confidence=0.85,
            target_agent=None,
            rationale="Erro inesperado ou catastrófico; recomendado rollback seguro para o último checkpoint.",
        )

    def prune_context(
        self,
        prompt: str,
        symbols: list[str],
    ) -> ContextPruningReport:
        """Filtra símbolos do AST relevantes ao prompt para reduzir tokens do Sistema 2."""
        prompt_tokens = set(re.findall(r"\b\w+\b", prompt.lower()))
        retained: list[str] = []
        for symbol in symbols:
            symbol_parts = set(re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)", symbol))
            symbol_tokens = {p.lower() for p in symbol_parts}.union({symbol.lower()})
            if (
                prompt_tokens.intersection(symbol_tokens)
                or symbol.lower() in prompt.lower()
                or any(part.lower() in prompt_tokens for part in symbol_parts if len(part) > 3)
            ):
                retained.append(symbol)

        if not retained and symbols:
            retained = symbols[:2]

        orig_count = len(symbols)
        pruned_count = len(retained)
        orig_tokens = orig_count * 70
        pruned_tokens = pruned_count * 70
        savings = round((1.0 - (pruned_tokens / max(orig_tokens, 1))) * 100, 1)

        return ContextPruningReport(
            original_symbols_count=orig_count,
            pruned_symbols_count=pruned_count,
            original_tokens_estimate=orig_tokens,
            pruned_tokens_estimate=pruned_tokens,
            savings_percentage=max(0.0, savings),
            retained_symbols=retained,
        )
