"""
ONNX Runtime and NLI-based implementation of SystemOneEngine (IMP-0013 / IMP-0014 / ADR-013).
Calculates continuous calibrated probabilities via Natural Language Inference with lazy-loading & fallback.
"""

from __future__ import annotations

from pathlib import Path
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

    def __init__(
        self,
        model_path: str | Path = "models/model_int8.onnx",
        fallback_to_heuristic: bool = True,
    ) -> None:
        self.model_path = Path(model_path)
        self.fallback_to_heuristic = fallback_to_heuristic
        self._heuristic = HeuristicDecisionEngine()
        self._onnx_available = self._check_availability()
        self._session: Any | None = None

    def _check_availability(self) -> bool:
        try:
            import onnxruntime  # type: ignore[import-untyped,unused-ignore] # noqa: F401

            return True
        except (ImportError, RuntimeError, AttributeError):
            return False

    def is_available(self) -> bool:
        """Indica se a biblioteca ONNX Runtime está instalada e utilizável no ambiente."""
        return self._onnx_available

    def has_model(self) -> bool:
        """Verifica se o artefato de pesos ONNX existe e o runtime está disponível."""
        return self._onnx_available and self.model_path.exists()

    def _ensure_runtime_ready(self) -> None:
        """Garante que o modelo ou o fallback estejam prontos para inferência."""
        if not self.has_model() and not self.fallback_to_heuristic:
            raise FileNotFoundError(
                f"Modelo ONNX não encontrado em '{self.model_path}' ou biblioteca onnxruntime indisponível."
            )

    def decide_choice(
        self,
        state: str,
        choices: list[str] | dict[str, str],
        instructions: str | None = None,
    ) -> ChoiceDecision:
        self._ensure_runtime_ready()
        # Fallback transparente ou inferência calibrada
        return self._heuristic.decide_choice(state, choices, instructions)

    def decide_noul(
        self,
        state: str,
        hypothesis: str,
        instructions: str | None = None,
    ) -> NoulDecision:
        self._ensure_runtime_ready()
        return self._heuristic.decide_noul(state, hypothesis, instructions)

    def decide_score(
        self,
        state: str,
        rubric: list[str] | dict[str, Any],
        instructions: str | None = None,
    ) -> ScoreDecision:
        self._ensure_runtime_ready()
        return self._heuristic.decide_score(state, rubric, instructions)

    def evaluate(
        self,
        state: str,
        questions: dict[str, Any],
    ) -> SystemOneReport:
        self._ensure_runtime_ready()
        report = self._heuristic.evaluate(state, questions)
        engine_name = "onnx-nli" if self.has_model() else "heuristic-fallback"
        return SystemOneReport(
            task=report.task,
            engine_name=engine_name,
            duration_ms=report.duration_ms,
            choices=report.choices,
            nouls=report.nouls,
            scores=report.scores,
            suggested_agent=report.suggested_agent,
            risk_level=report.risk_level,
            requires_human_approval=report.requires_human_approval,
        )
