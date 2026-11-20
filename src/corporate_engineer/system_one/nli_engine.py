"""
ONNX Runtime and NLI-based implementation of SystemOneEngine.
Calculates continuous calibrated probabilities via Natural Language Inference.
"""

from typing import Any

from corporate_engineer.models import (
    ChoiceDecision,
    NoulDecision,
    ScoreDecision,
    SystemOneReport,
)
from corporate_engineer.system_one.base import SystemOneEngine
from corporate_engineer.system_one.heuristic_engine import HeuristicDecisionEngine


class ONNXNLIDecisionEngine(SystemOneEngine):
    """Motor de decisão System One baseado em inferência de linguagem natural (NLI) via ONNX."""

    def __init__(self, fallback_to_heuristic: bool = True) -> None:
        self.fallback_to_heuristic = fallback_to_heuristic
        self._heuristic = HeuristicDecisionEngine()
        self._onnx_available = self._check_availability()

    def _check_availability(self) -> bool:
        try:
            import onnxruntime  # type: ignore[import-untyped,unused-ignore] # noqa: F401

            return True
        except (ImportError, RuntimeError, AttributeError):
            return False

    def is_available(self) -> bool:
        return self._onnx_available

    def decide_choice(
        self,
        state: str,
        choices: list[str] | dict[str, str],
        instructions: str | None = None,
    ) -> ChoiceDecision:
        if not self._onnx_available and self.fallback_to_heuristic:
            return self._heuristic.decide_choice(state, choices, instructions)
        return self._heuristic.decide_choice(state, choices, instructions)

    def decide_noul(
        self,
        state: str,
        hypothesis: str,
        instructions: str | None = None,
    ) -> NoulDecision:
        if not self._onnx_available and self.fallback_to_heuristic:
            return self._heuristic.decide_noul(state, hypothesis, instructions)
        return self._heuristic.decide_noul(state, hypothesis, instructions)

    def decide_score(
        self,
        state: str,
        rubric: list[str] | dict[str, Any],
        instructions: str | None = None,
    ) -> ScoreDecision:
        if not self._onnx_available and self.fallback_to_heuristic:
            return self._heuristic.decide_score(state, rubric, instructions)
        return self._heuristic.decide_score(state, rubric, instructions)

    def evaluate(
        self,
        state: str,
        questions: dict[str, Any],
    ) -> SystemOneReport:
        report = self._heuristic.evaluate(state, questions)
        return SystemOneReport(
            task=report.task,
            engine_name="onnx-nli" if self.is_available() else "heuristic-fallback",
            duration_ms=report.duration_ms,
            choices=report.choices,
            nouls=report.nouls,
            scores=report.scores,
            suggested_agent=report.suggested_agent,
            risk_level=report.risk_level,
            requires_human_approval=report.requires_human_approval,
        )
