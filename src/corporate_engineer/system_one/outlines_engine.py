"""
Outlines-based implementation of SystemOneEngine using constrained logits decoding.
"""

from collections.abc import Callable
from typing import Any

from corporate_engineer.models import (
    ChoiceDecision,
    NoulDecision,
    ScoreDecision,
    SystemOneReport,
)
from corporate_engineer.system_one.base import SystemOneEngine
from corporate_engineer.system_one.heuristic_engine import HeuristicDecisionEngine


class OutlinesDecisionEngine(SystemOneEngine):
    """Motor de decisão System One baseado em decodificação restrita via Outlines."""

    def __init__(
        self,
        fallback_to_heuristic: bool = True,
        generator_override: Callable[..., Any] | None = None,
    ) -> None:
        self.fallback_to_heuristic = fallback_to_heuristic
        self.generator_override = generator_override
        self._heuristic = HeuristicDecisionEngine()
        self._outlines_available = self._check_availability()

    def _check_availability(self) -> bool:
        if self.generator_override is not None:
            return True
        try:
            import outlines  # type: ignore[import-untyped,unused-ignore] # noqa: F401

            return True
        except (ImportError, RuntimeError, AttributeError):
            return False

    def is_available(self) -> bool:
        return self._outlines_available

    def decide_choice(
        self,
        state: str,
        choices: list[str] | dict[str, str],
        instructions: str | None = None,
    ) -> ChoiceDecision:
        choice_list = list(choices.keys()) if isinstance(choices, dict) else choices

        if self.generator_override is not None:
            result = str(self.generator_override(state, choice_list))
            return ChoiceDecision(
                choice=result,
                confidence=1.0,
                probabilities={c: (1.0 if c == result else 0.0) for c in choice_list},
                rationale="Determined via Outlines constrained logits",
            )

        if not self._outlines_available and self.fallback_to_heuristic:
            return self._heuristic.decide_choice(state, choices, instructions)

        # Caso outlines esteja disponível em runtime
        try:
            import outlines  # type: ignore[import-untyped]

            model = outlines.models.transformers("Qwen/Qwen2.5-0.5B-Instruct")
            generator = outlines.generate.choice(model, choice_list)
            res = str(generator(state))
            return ChoiceDecision(
                choice=res,
                confidence=1.0,
                probabilities={c: (1.0 if c == res else 0.0) for c in choice_list},
                rationale="Outlines constrained generation",
            )
        except Exception:
            if self.fallback_to_heuristic:
                return self._heuristic.decide_choice(state, choices, instructions)
            raise

    def decide_noul(
        self,
        state: str,
        hypothesis: str,
        instructions: str | None = None,
    ) -> NoulDecision:
        if self.generator_override is not None:
            res = bool(self.generator_override(state, hypothesis))
            return NoulDecision(
                decision=res,
                probability=1.0 if res else 0.0,
                rationale="Determined via Outlines boolean constraint",
            )

        if not self._outlines_available and self.fallback_to_heuristic:
            return self._heuristic.decide_noul(state, hypothesis, instructions)

        return self._heuristic.decide_noul(state, hypothesis, instructions)

    def decide_score(
        self,
        state: str,
        rubric: list[str] | dict[str, Any],
        instructions: str | None = None,
    ) -> ScoreDecision:
        if self.generator_override is not None:
            res_score = self.generator_override(state, rubric)
            return ScoreDecision(
                score=int(res_score),
                level=str(res_score),
                confidence=1.0,
                rationale="Determined via Outlines score",
            )

        return self._heuristic.decide_score(state, rubric, instructions)

    def evaluate(
        self,
        state: str,
        questions: dict[str, Any],
    ) -> SystemOneReport:
        if not self._outlines_available and self.fallback_to_heuristic:
            report = self._heuristic.evaluate(state, questions)
            return report

        report = self._heuristic.evaluate(state, questions)
        # Identifica o motor utilizado no relatório
        return SystemOneReport(
            task=report.task,
            engine_name="outlines" if self.is_available() else "heuristic-fallback",
            duration_ms=report.duration_ms,
            choices=report.choices,
            nouls=report.nouls,
            scores=report.scores,
            suggested_agent=report.suggested_agent,
            risk_level=report.risk_level,
            requires_human_approval=report.requires_human_approval,
        )
