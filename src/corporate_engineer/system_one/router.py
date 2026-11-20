"""
High-level SystemOneRouter for capability intelligence, agent routing, and quality gate triage.
"""

from typing import Any, ClassVar

from corporate_engineer.models import (
    ChoiceDecision,
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
