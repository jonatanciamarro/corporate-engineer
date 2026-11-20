"""
Deterministic and heuristic implementation of SystemOneEngine.
Operates 100% offline with zero external dependencies and sub-millisecond execution.
"""

import math
import re
import time
from typing import Any

from corporate_engineer.models import (
    ChoiceDecision,
    NoulDecision,
    ScoreDecision,
    SystemOneReport,
)
from corporate_engineer.system_one.base import SystemOneEngine


class HeuristicDecisionEngine(SystemOneEngine):
    """Motor de decisão heurístico determinístico de altíssima velocidade."""

    def __init__(self) -> None:
        # Padrões lexicais de apoio para termos comuns do ecossistema
        self._keyword_profiles: dict[str, list[str]] = {
            "architect": [
                "arquitetura",
                "design",
                "adr",
                "contrato",
                "dto",
                "planejar",
                "planejamento",
                "modelagem",
                "sistema",
            ],
            "tdd-guide": [
                "teste",
                "testes",
                "tdd",
                "pytest",
                "unitário",
                "cobertura",
                "red",
                "green",
                "assert",
                "coverage",
            ],
            "code-reviewer": [
                "revisão",
                "review",
                "refatoração",
                "clean",
                "qualidade",
                "ruff",
                "mypy",
                "pep8",
                "estilo",
                "lint",
            ],
            "security-reviewer": [
                "segurança",
                "security",
                "senha",
                "secret",
                "vazamento",
                "owasp",
                "token",
                "jwt",
                "autenticação",
                "auth",
            ],
            "build-error-resolver": [
                "build",
                "erro",
                "falha",
                "quebrado",
                "fix",
                "resolver",
                "exceção",
                "traceback",
            ],
            "rag-pipeline-reviewer": [
                "ast",
                "indexador",
                "rag",
                "grafo",
                "símbolo",
                "herança",
                "call graph",
            ],
            "refactor-cleaner": [
                "limpeza",
                "reorganização",
                "duplicação",
                "dead code",
                "remover",
                "simplificar",
            ],
        }

    def is_available(self) -> bool:
        return True

    def _tokenize(self, text: str) -> set[str]:
        return set(re.findall(r"\b\w+\b", text.lower()))

    def decide_choice(
        self,
        state: str,
        choices: list[str] | dict[str, str],
        instructions: str | None = None,
    ) -> ChoiceDecision:
        state_tokens = self._tokenize(state + " " + (instructions or ""))

        choice_dict: dict[str, str] = (
            choices if isinstance(choices, dict) else {c: c for c in choices}
        )

        scores: dict[str, float] = {}
        for key, description in choice_dict.items():
            desc_tokens = self._tokenize(key + " " + description)
            # Adiciona termos do profile especializado se existir
            known_terms = set(self._keyword_profiles.get(key.lower(), []))
            combined_target = desc_tokens | known_terms

            matches = state_tokens.intersection(combined_target)
            # Pontuação base com suavização
            scores[key] = len(matches) * 2.0 + (1.0 if key.lower() in state_tokens else 0.1)

        # Softmax simples para converter em probabilidades calibradas
        max_score = max(scores.values()) if scores else 1.0
        exp_scores = {k: math.exp(v - max_score) for k, v in scores.items()}
        total_exp = sum(exp_scores.values()) or 1.0

        probabilities = {k: round(v / total_exp, 4) for k, v in exp_scores.items()}

        best_choice = max(probabilities.items(), key=lambda item: item[1])
        confidence = float(best_choice[1])

        return ChoiceDecision(
            choice=best_choice[0],
            confidence=confidence,
            probabilities=probabilities,
            rationale=f"Heuristic pattern match for choice '{best_choice[0]}'",
        )

    def decide_noul(
        self,
        state: str,
        hypothesis: str,
        instructions: str | None = None,
    ) -> NoulDecision:
        state_tokens = self._tokenize(state + " " + (instructions or ""))
        hypo_tokens = self._tokenize(hypothesis)

        intersection = state_tokens.intersection(hypo_tokens)
        negative_markers = {
            "não",
            "nenhum",
            "sem",
            "not",
            "no",
            "never",
            "trivial",
            "typo",
            "docs",
            "apenas",
        }
        positive_markers = {
            "crítico",
            "critical",
            "risco",
            "alto",
            "high",
            "quebra",
            "breaking",
            "segurança",
            "vazamento",
            "auth",
            "urgent",
        }

        pos_count = len(state_tokens.intersection(positive_markers))
        neg_count = len(state_tokens.intersection(negative_markers))
        overlap_ratio = len(intersection) / max(len(hypo_tokens), 1)

        raw_score = overlap_ratio * 0.6 + (pos_count * 0.25) - (neg_count * 0.3)
        # Sigmoid para mapear em [0.0, 1.0]
        prob = round(1.0 / (1.0 + math.exp(-raw_score * 3.0)), 4)
        prob = max(0.01, min(0.99, prob))

        decision = prob >= 0.5
        return NoulDecision(
            decision=decision,
            probability=prob,
            rationale=f"Heuristic noul match (prob={prob:.2f})",
        )

    def decide_score(
        self,
        state: str,
        rubric: list[str] | dict[str, Any],
        instructions: str | None = None,
    ) -> ScoreDecision:
        rubric_list = rubric if isinstance(rubric, list) else list(rubric.keys())
        num_levels = len(rubric_list)
        if num_levels == 0:
            return ScoreDecision(score=0, level="N/A", confidence=1.0)

        state_tokens = self._tokenize(state + " " + (instructions or ""))

        # Heurística de complexidade por termos
        high_severity = {"crítico", "critical", "breaking", "core", "auth", "secrets", "database"}
        medium_severity = {"refactor", "feature", "change", "alterar", "expandir"}

        if state_tokens.intersection(high_severity) and num_levels > 1:
            idx = num_levels - 1
            confidence = 0.85
        elif state_tokens.intersection(medium_severity) and num_levels > 2:
            idx = num_levels // 2
            confidence = 0.75
        else:
            idx = 0
            confidence = 0.80

        level_name = str(rubric_list[idx])
        return ScoreDecision(
            score=idx,
            level=level_name,
            confidence=confidence,
            rationale=f"Assigned rubric level '{level_name}' via heuristics",
        )

    def evaluate(
        self,
        state: str,
        questions: dict[str, Any],
    ) -> SystemOneReport:
        start_time = time.perf_counter()
        choices: dict[str, ChoiceDecision] = {}
        nouls: dict[str, NoulDecision] = {}
        scores: dict[str, ScoreDecision] = {}

        suggested_agent: str | None = None
        risk_level = "LOW"
        requires_human_approval = False

        for q_name, q_config in questions.items():
            q_type = str(q_config.get("type", "")).lower()
            instructions = q_config.get("instructions")

            if q_type == "choice":
                crit = q_config.get("criteria", q_config.get("choices", []))
                dec = self.decide_choice(state, crit, instructions=instructions)
                choices[q_name] = dec
                if q_name in ["agent", "target_agent", "subagent"]:
                    suggested_agent = dec.choice

            elif q_type == "noul":
                hypo = q_config.get("hypothesis", instructions or q_name)
                noul_dec = self.decide_noul(state, hypo, instructions=instructions)
                nouls[q_name] = noul_dec
                if q_name in ["requires_approval", "human_approval"] and noul_dec.decision:
                    requires_human_approval = True

            elif q_type == "score":
                rubric = q_config.get("rubric", q_config.get("criteria", []))
                score_dec = self.decide_score(state, rubric, instructions=instructions)
                scores[q_name] = score_dec
                if q_name in ["risk", "risk_level"]:
                    if score_dec.score >= 2:
                        risk_level = "HIGH"
                    elif score_dec.score == 1:
                        risk_level = "MEDIUM"

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return SystemOneReport(
            task=state[:120],
            engine_name="heuristic",
            duration_ms=duration_ms,
            choices=choices,
            nouls=nouls,
            scores=scores,
            suggested_agent=suggested_agent,
            risk_level=risk_level,
            requires_human_approval=requires_human_approval,
        )
