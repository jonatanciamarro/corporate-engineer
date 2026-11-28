"""
Outlines-based implementation of SystemOneEngine using constrained logits decoding.
"""

from __future__ import annotations

import threading
import time
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
        model_id: str = "Qwen/Qwen2.5-0.5B-Instruct",
        fallback_to_heuristic: bool = True,
        generator_override: Callable[..., Any] | None = None,
    ) -> None:
        self.model_id = model_id
        self.fallback_to_heuristic = fallback_to_heuristic
        self.generator_override = generator_override
        self._heuristic = HeuristicDecisionEngine()
        self._lock = threading.RLock()
        self._model: Any | None = None
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

    def _get_model(self) -> Any:
        with self._lock:
            if self._model is None:
                import outlines  # type: ignore[import-untyped,unused-ignore]

                self._model = outlines.models.transformers(self.model_id)
            return self._model

    def _decide_choice_detailed(
        self,
        state: str,
        choices: list[str] | dict[str, str],
        instructions: str | None = None,
    ) -> tuple[ChoiceDecision, bool, str | None]:
        choice_list = list(choices.keys()) if isinstance(choices, dict) else choices

        if self.generator_override is not None:
            result = str(self.generator_override(state, choice_list))
            return (
                ChoiceDecision(
                    choice=result,
                    confidence=1.0,
                    probabilities={c: (1.0 if c == result else 0.0) for c in choice_list},
                    rationale="Determined via Outlines constrained logits",
                ),
                True,
                None,
            )

        if not self._outlines_available:
            if self.fallback_to_heuristic:
                return (
                    self._heuristic.decide_choice(state, choices, instructions),
                    False,
                    "outlines dependency unavailable",
                )
            raise RuntimeError("Outlines runtime is unavailable.")

        try:
            import outlines  # type: ignore[import-untyped,unused-ignore]

            model = self._get_model()
            generator = outlines.generate.choice(model, choice_list)
            res = str(generator(state))
            return (
                ChoiceDecision(
                    choice=res,
                    confidence=1.0,
                    probabilities={c: (1.0 if c == res else 0.0) for c in choice_list},
                    rationale="Outlines constrained generation",
                ),
                True,
                None,
            )
        except Exception as exc:
            if self.fallback_to_heuristic:
                return (
                    self._heuristic.decide_choice(state, choices, instructions),
                    False,
                    f"Outlines inference error ({type(exc).__name__}): {exc}",
                )
            raise

    def _decide_choice_with_source(
        self,
        state: str,
        choices: list[str] | dict[str, str],
        instructions: str | None = None,
    ) -> tuple[ChoiceDecision, bool]:
        decision, used_outlines, _ = self._decide_choice_detailed(state, choices, instructions)
        return decision, used_outlines

    def _decide_noul_detailed(
        self,
        state: str,
        hypothesis: str,
        instructions: str | None = None,
    ) -> tuple[NoulDecision, bool, str | None]:
        if self.generator_override is not None:
            raw = self.generator_override(state, hypothesis)
            res = (
                raw.strip().lower() in ("true", "yes", "1", "sim")
                if isinstance(raw, str)
                else bool(raw)
            )
            return (
                NoulDecision(
                    decision=res,
                    probability=1.0 if res else 0.0,
                    rationale="Determined via Outlines boolean constraint",
                ),
                True,
                None,
            )

        if not self._outlines_available:
            if self.fallback_to_heuristic:
                return (
                    self._heuristic.decide_noul(state, hypothesis, instructions),
                    False,
                    "outlines dependency unavailable",
                )
            raise RuntimeError("Outlines runtime is unavailable.")

        try:
            import outlines  # type: ignore[import-untyped,unused-ignore]

            model = self._get_model()
            generator = outlines.generate.choice(model, ["True", "False"])
            raw = str(generator(f"{state}\nHypothesis: {hypothesis}")).strip().lower()
            res = raw in ("true", "yes", "1", "sim")
            return (
                NoulDecision(
                    decision=res,
                    probability=1.0 if res else 0.0,
                    rationale="Outlines constrained boolean generation",
                ),
                True,
                None,
            )
        except Exception as exc:
            if self.fallback_to_heuristic:
                return (
                    self._heuristic.decide_noul(state, hypothesis, instructions),
                    False,
                    f"Outlines inference error ({type(exc).__name__}): {exc}",
                )
            raise

    def _decide_noul_with_source(
        self,
        state: str,
        hypothesis: str,
        instructions: str | None = None,
    ) -> tuple[NoulDecision, bool]:
        decision, used_outlines, _ = self._decide_noul_detailed(state, hypothesis, instructions)
        return decision, used_outlines

    def _decide_score_detailed(
        self,
        state: str,
        rubric: list[str] | dict[str, Any],
        instructions: str | None = None,
    ) -> tuple[ScoreDecision, bool, str | None]:
        rubric_list = [
            str(item) for item in (rubric if isinstance(rubric, list) else rubric.keys())
        ]
        if not rubric_list:
            reason = None if self._outlines_available else "outlines dependency unavailable"
            return (
                ScoreDecision(score=0, level="N/A", confidence=1.0),
                self._outlines_available,
                reason,
            )

        if self.generator_override is not None:
            raw_score = self.generator_override(state, rubric)
            if isinstance(raw_score, str) and raw_score in rubric_list:
                idx = rubric_list.index(raw_score)
                level = raw_score
            else:
                idx = max(0, min(int(raw_score), len(rubric_list) - 1))
                level = rubric_list[idx]
            return (
                ScoreDecision(
                    score=idx,
                    level=level,
                    confidence=1.0,
                    rationale="Determined via Outlines score",
                ),
                True,
                None,
            )

        if not self._outlines_available:
            if self.fallback_to_heuristic:
                return (
                    self._heuristic.decide_score(state, rubric, instructions),
                    False,
                    "outlines dependency unavailable",
                )
            raise RuntimeError("Outlines runtime is unavailable.")

        try:
            import outlines  # type: ignore[import-untyped,unused-ignore]

            model = self._get_model()
            generator = outlines.generate.choice(model, rubric_list)
            chosen = str(generator(state))
            idx = rubric_list.index(chosen) if chosen in rubric_list else 0
            level = rubric_list[idx]
            return (
                ScoreDecision(
                    score=idx,
                    level=level,
                    confidence=1.0,
                    rationale="Outlines constrained rubric generation",
                ),
                True,
                None,
            )
        except Exception as exc:
            if self.fallback_to_heuristic:
                return (
                    self._heuristic.decide_score(state, rubric, instructions),
                    False,
                    f"Outlines inference error ({type(exc).__name__}): {exc}",
                )
            raise

    def _decide_score_with_source(
        self,
        state: str,
        rubric: list[str] | dict[str, Any],
        instructions: str | None = None,
    ) -> tuple[ScoreDecision, bool]:
        decision, used_outlines, _ = self._decide_score_detailed(state, rubric, instructions)
        return decision, used_outlines

    def decide_choice(
        self,
        state: str,
        choices: list[str] | dict[str, str],
        instructions: str | None = None,
    ) -> ChoiceDecision:
        decision, _ = self._decide_choice_with_source(state, choices, instructions)
        return decision

    def decide_noul(
        self,
        state: str,
        hypothesis: str,
        instructions: str | None = None,
    ) -> NoulDecision:
        decision, _ = self._decide_noul_with_source(state, hypothesis, instructions)
        return decision

    def decide_score(
        self,
        state: str,
        rubric: list[str] | dict[str, Any],
        instructions: str | None = None,
    ) -> ScoreDecision:
        decision, _ = self._decide_score_with_source(state, rubric, instructions)
        return decision

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

        any_outlines = False
        any_fallback = False
        fallback_reasons: list[str] = []

        if not questions:
            if self.generator_override is not None:
                any_outlines = True
            elif self._outlines_available:
                try:
                    self._get_model()
                    any_outlines = True
                except Exception as exc:
                    if not self.fallback_to_heuristic:
                        raise
                    any_fallback = True
                    fallback_reasons.append(f"Outlines model initialization failed: {exc}")
            else:
                any_fallback = True
                fallback_reasons.append("outlines dependency unavailable")

        for q_name, q_config in questions.items():
            q_type = str(q_config.get("type", "")).lower()
            instructions = q_config.get("instructions")

            if q_type == "choice":
                crit = q_config.get("criteria", q_config.get("choices", []))
                dec, used_outlines, fb_reason = self._decide_choice_detailed(
                    state, crit, instructions=instructions
                )
                choices[q_name] = dec
                any_outlines = any_outlines or used_outlines
                any_fallback = any_fallback or (not used_outlines)
                if fb_reason:
                    fallback_reasons.append(fb_reason)
                if q_name in ["agent", "target_agent", "subagent"]:
                    suggested_agent = dec.choice

            elif q_type == "noul":
                hypo = q_config.get("hypothesis", instructions or q_name)
                noul_dec, used_outlines, fb_reason = self._decide_noul_detailed(
                    state, hypo, instructions=instructions
                )
                nouls[q_name] = noul_dec
                any_outlines = any_outlines or used_outlines
                any_fallback = any_fallback or (not used_outlines)
                if fb_reason:
                    fallback_reasons.append(fb_reason)
                if q_name in ["requires_approval", "human_approval"] and noul_dec.decision:
                    requires_human_approval = True

            elif q_type == "score":
                rubric = q_config.get("rubric", q_config.get("criteria", []))
                score_dec, used_outlines, fb_reason = self._decide_score_detailed(
                    state, rubric, instructions=instructions
                )
                scores[q_name] = score_dec
                any_outlines = any_outlines or used_outlines
                any_fallback = any_fallback or (not used_outlines)
                if fb_reason:
                    fallback_reasons.append(fb_reason)
                if q_name in ["risk", "risk_level"]:
                    if score_dec.score >= 2:
                        risk_level = "HIGH"
                    elif score_dec.score == 1:
                        risk_level = "MEDIUM"

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        is_real_outlines = any_outlines and not any_fallback
        engine_name = "outlines" if is_real_outlines else "heuristic-fallback"
        fallback_reason: str | None = (
            None
            if is_real_outlines
            else (
                "; ".join(dict.fromkeys(fallback_reasons))
                or "Outlines runtime unavailable; fell back to heuristic engine"
            )
        )

        return SystemOneReport(
            task=state[:120],
            engine_name=engine_name,
            fallback_reason=fallback_reason,
            duration_ms=duration_ms,
            choices=choices,
            nouls=nouls,
            scores=scores,
            suggested_agent=suggested_agent,
            risk_level=risk_level,
            requires_human_approval=requires_human_approval,
        )
