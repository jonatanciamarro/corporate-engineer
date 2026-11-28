"""
ONNX Runtime and NLI-based implementation of SystemOneEngine (IMP-0013 / IMP-0014 / ADR-013).
Calculates continuous calibrated probabilities via Natural Language Inference with lazy-loading & fallback.
"""

from __future__ import annotations

import math
import threading
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


def _softmax(values: list[float]) -> list[float]:
    if not values:
        return []
    max_val = max(values)
    exps = [math.exp(max(-50.0, min(50.0, v - max_val))) for v in values]
    total = sum(exps) or 1.0
    return [v / total for v in exps]


def _sigmoid(value: float) -> float:
    clamped = max(-50.0, min(50.0, value))
    return 1.0 / (1.0 + math.exp(-clamped))


def _unwrap_logits(raw_output: Any) -> list[float]:
    data = raw_output.tolist() if hasattr(raw_output, "tolist") else raw_output
    while isinstance(data, (list, tuple)) and data and isinstance(data[0], (list, tuple)):
        # For 3D (batch, seq_len, vocab), pick the last token slice on sequence axis
        if (
            len(data) == 1
            and isinstance(data[0], (list, tuple))
            and data[0]
            and isinstance(data[0][0], (list, tuple))
        ):
            data = data[0][-1]
        else:
            data = data[0]
    if not isinstance(data, (list, tuple)):
        return [float(data)]
    return [float(x) for x in data]


class ONNXNLIDecisionEngine(SystemOneEngine):
    """Motor de decisão System One baseado em inferência de linguagem natural (NLI) via ONNX."""

    def __init__(
        self,
        model_path: str | Path = "models/model_int8.onnx",
        fallback_to_heuristic: bool = True,
        session: Any | None = None,
        tokenizer: Any | None = None,
    ) -> None:
        self.model_path = Path(model_path)
        self.fallback_to_heuristic = fallback_to_heuristic
        self._heuristic = HeuristicDecisionEngine()
        self._lock = threading.RLock()
        self._session: Any | None = session
        self._tokenizer: Any | None = tokenizer
        self._onnx_available = self._check_availability()

    def _check_availability(self) -> bool:
        if self._session is not None and self._tokenizer is not None:
            return True
        try:
            import onnxruntime  # type: ignore[import-untyped,unused-ignore] # noqa: F401

            return True
        except (ImportError, RuntimeError, AttributeError):
            return False

    def is_available(self) -> bool:
        """Indica se o runtime ONNX (ou sessão/tokenizer injetados) está disponível."""
        return (self._session is not None and self._tokenizer is not None) or self._onnx_available

    def has_model(self) -> bool:
        """Verifica se o artefato de pesos ONNX existe e o runtime está disponível."""
        if self._session is not None and self._tokenizer is not None:
            return True
        return self._onnx_available and self.model_path.exists()

    def _resolve_runtime(self) -> tuple[tuple[Any, Any] | None, str | None]:
        """Load ONNX session and tokenizer thread-safely, returning fallback reason if unavailable."""
        with self._lock:
            if self._session is not None and self._tokenizer is not None:
                return (self._session, self._tokenizer), None

            if not self._onnx_available:
                reason = "onnxruntime dependency unavailable"
                if not self.fallback_to_heuristic:
                    raise FileNotFoundError(
                        f"Modelo ONNX não encontrado em '{self.model_path}' "
                        "ou biblioteca onnxruntime indisponível."
                    )
                return None, reason

            if not self.model_path.exists():
                reason = f"ONNX model artifact not found at '{self.model_path}'"
                if not self.fallback_to_heuristic:
                    raise FileNotFoundError(
                        f"Modelo ONNX não encontrado em '{self.model_path}' "
                        "ou biblioteca onnxruntime indisponível."
                    )
                return None, reason

            try:
                if self._session is None:
                    import onnxruntime as ort  # type: ignore[import-untyped,unused-ignore]

                    self._session = ort.InferenceSession(str(self.model_path))

                if self._tokenizer is None:
                    tokenizer_path = self.model_path.parent / "tokenizer.json"
                    if not tokenizer_path.exists():
                        raise FileNotFoundError(
                            f"Tokenizer ONNX não encontrado em '{tokenizer_path}'."
                        )
                    from tokenizers import Tokenizer  # type: ignore[import-untyped,unused-ignore]

                    self._tokenizer = Tokenizer.from_file(str(tokenizer_path))

                return (self._session, self._tokenizer), None
            except (ImportError, FileNotFoundError, RuntimeError, OSError, AttributeError) as exc:
                if not self.fallback_to_heuristic:
                    if isinstance(exc, FileNotFoundError):
                        raise
                    raise FileNotFoundError(
                        f"Falha ao inicializar runtime ONNX/tokenizer: {exc}"
                    ) from exc
                return None, f"ONNX runtime initialization failed: {exc}"

    def _ensure_loaded(self) -> tuple[Any, Any] | None:
        """Carrega sessão ONNX e tokenizer de forma thread-safe sob RLock."""
        runtime, _ = self._resolve_runtime()
        return runtime

    def _encode_pair(
        self, tokenizer: Any, premise: str, hypothesis: str
    ) -> tuple[list[int], list[int], list[int]]:
        try:
            encoded = tokenizer.encode(premise, hypothesis)
        except TypeError:
            encoded = tokenizer.encode(f"{premise} [SEP] {hypothesis}")

        if isinstance(encoded, dict):
            ids = [int(x) for x in encoded.get("input_ids", [])]
            mask = [int(x) for x in encoded.get("attention_mask", [1] * len(ids))]
            type_ids = [int(x) for x in encoded.get("token_type_ids", [0] * len(ids))]
            return ids, mask, type_ids

        ids = [int(x) for x in getattr(encoded, "ids", [])]
        mask = [int(x) for x in getattr(encoded, "attention_mask", [1] * len(ids))]
        type_ids = [int(x) for x in getattr(encoded, "type_ids", [0] * len(ids))]
        return ids, mask, type_ids

    def _build_feed_dict(
        self,
        session: Any,
        input_ids: list[int],
        attention_mask: list[int],
        token_type_ids: list[int],
    ) -> dict[str, Any]:
        available_arrays: dict[str, list[list[int]]] = {
            "input_ids": [input_ids],
            "attention_mask": [attention_mask],
            "token_type_ids": [token_type_ids],
        }
        try:
            import numpy as np  # type: ignore[import-not-found,unused-ignore]

            def _to_tensor(seq: list[list[int]]) -> Any:
                return np.asarray(seq, dtype=np.int64)
        except ImportError:

            def _to_tensor(seq: list[list[int]]) -> Any:
                return seq

        input_names: list[str] = []
        if hasattr(session, "get_inputs"):
            try:
                input_names = [
                    str(inp.name) for inp in session.get_inputs() if hasattr(inp, "name")
                ]
            except (AttributeError, RuntimeError, TypeError, ValueError):
                input_names = []

        if not input_names:
            return {
                "input_ids": _to_tensor(available_arrays["input_ids"]),
                "attention_mask": _to_tensor(available_arrays["attention_mask"]),
            }

        feed: dict[str, Any] = {}
        for name in input_names:
            if name in available_arrays:
                feed[name] = _to_tensor(available_arrays[name])
            elif "mask" in name:
                feed[name] = _to_tensor(available_arrays["attention_mask"])
            elif "type" in name:
                feed[name] = _to_tensor(available_arrays["token_type_ids"])
            else:
                feed[name] = _to_tensor(available_arrays["input_ids"])
        return feed

    def _score_pair(
        self,
        session: Any,
        tokenizer: Any,
        premise: str,
        hypothesis: str,
    ) -> tuple[float, float]:
        input_ids, attention_mask, token_type_ids = self._encode_pair(
            tokenizer, premise, hypothesis
        )
        feed = self._build_feed_dict(session, input_ids, attention_mask, token_type_ids)
        outputs = session.run(None, feed)
        logits = _unwrap_logits(outputs[0])
        if not logits:
            return 0.0, 0.5
        if len(logits) == 1:
            return logits[0], _sigmoid(logits[0])
        probs = _softmax(logits)
        return logits[-1] - logits[0], probs[-1]

    def _decide_choice_detailed(
        self,
        state: str,
        choices: list[str] | dict[str, str],
        instructions: str | None = None,
    ) -> tuple[ChoiceDecision, bool, str | None]:
        runtime, load_reason = self._resolve_runtime()
        choice_dict = choices if isinstance(choices, dict) else {c: c for c in choices}
        if runtime is None or not choice_dict:
            reason = load_reason or "Empty choice criteria; fell back to heuristic engine"
            return self._heuristic.decide_choice(state, choices, instructions), False, reason

        session, tokenizer = runtime
        premise = f"{instructions}\n{state}" if instructions else state
        try:
            raw_scores: dict[str, float] = {}
            for key, desc in choice_dict.items():
                hypothesis = f"{key}: {desc}" if desc != key else key
                logit_score, _ = self._score_pair(session, tokenizer, premise, hypothesis)
                raw_scores[key] = logit_score

            keys = list(raw_scores.keys())
            probs_list = _softmax([raw_scores[k] for k in keys])
            probabilities = {k: round(p, 4) for k, p in zip(keys, probs_list, strict=True)}
            best_choice = max(probabilities.items(), key=lambda item: item[1])
            return (
                ChoiceDecision(
                    choice=best_choice[0],
                    confidence=float(best_choice[1]),
                    probabilities=probabilities,
                    rationale=f"ONNX NLI logit inference for choice '{best_choice[0]}'",
                ),
                True,
                None,
            )
        except Exception as exc:
            if self.fallback_to_heuristic:
                return (
                    self._heuristic.decide_choice(state, choices, instructions),
                    False,
                    f"ONNX NLI inference error ({type(exc).__name__}): {exc}",
                )
            raise

    def _decide_choice_with_source(
        self,
        state: str,
        choices: list[str] | dict[str, str],
        instructions: str | None = None,
    ) -> tuple[ChoiceDecision, bool]:
        decision, used_onnx, _ = self._decide_choice_detailed(state, choices, instructions)
        return decision, used_onnx

    def _decide_noul_detailed(
        self,
        state: str,
        hypothesis: str,
        instructions: str | None = None,
    ) -> tuple[NoulDecision, bool, str | None]:
        runtime, load_reason = self._resolve_runtime()
        if runtime is None:
            return (
                self._heuristic.decide_noul(state, hypothesis, instructions),
                False,
                load_reason or "ONNX NLI runtime unavailable",
            )

        session, tokenizer = runtime
        premise = f"{instructions}\n{state}" if instructions else state
        try:
            _, entailment_prob = self._score_pair(session, tokenizer, premise, hypothesis)
            prob = round(max(0.0, min(1.0, entailment_prob)), 4)
            return (
                NoulDecision(
                    decision=prob >= 0.5,
                    probability=prob,
                    rationale=f"ONNX NLI entailment inference (prob={prob:.2f})",
                ),
                True,
                None,
            )
        except Exception as exc:
            if self.fallback_to_heuristic:
                return (
                    self._heuristic.decide_noul(state, hypothesis, instructions),
                    False,
                    f"ONNX NLI inference error ({type(exc).__name__}): {exc}",
                )
            raise

    def _decide_noul_with_source(
        self,
        state: str,
        hypothesis: str,
        instructions: str | None = None,
    ) -> tuple[NoulDecision, bool]:
        decision, used_onnx, _ = self._decide_noul_detailed(state, hypothesis, instructions)
        return decision, used_onnx

    def _decide_score_detailed(
        self,
        state: str,
        rubric: list[str] | dict[str, Any],
        instructions: str | None = None,
    ) -> tuple[ScoreDecision, bool, str | None]:
        runtime, load_reason = self._resolve_runtime()
        rubric_list = rubric if isinstance(rubric, list) else list(rubric.keys())
        if runtime is None or not rubric_list:
            reason = load_reason or "Empty rubric criteria; fell back to heuristic engine"
            return self._heuristic.decide_score(state, rubric, instructions), False, reason

        session, tokenizer = runtime
        premise = f"{instructions}\n{state}" if instructions else state
        try:
            raw_scores: list[float] = []
            for level in rubric_list:
                logit_score, _ = self._score_pair(session, tokenizer, premise, f"Level: {level}")
                raw_scores.append(logit_score)

            probs = _softmax(raw_scores)
            best_idx = max(range(len(probs)), key=lambda i: probs[i])
            level_name = str(rubric_list[best_idx])
            return (
                ScoreDecision(
                    score=best_idx,
                    level=level_name,
                    confidence=round(probs[best_idx], 4),
                    rationale=f"ONNX NLI rubric scoring assigned '{level_name}'",
                ),
                True,
                None,
            )
        except Exception as exc:
            if self.fallback_to_heuristic:
                return (
                    self._heuristic.decide_score(state, rubric, instructions),
                    False,
                    f"ONNX NLI inference error ({type(exc).__name__}): {exc}",
                )
            raise

    def _decide_score_with_source(
        self,
        state: str,
        rubric: list[str] | dict[str, Any],
        instructions: str | None = None,
    ) -> tuple[ScoreDecision, bool]:
        decision, used_onnx, _ = self._decide_score_detailed(state, rubric, instructions)
        return decision, used_onnx

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
        import time

        start_time = time.perf_counter()
        choices: dict[str, ChoiceDecision] = {}
        nouls: dict[str, NoulDecision] = {}
        scores: dict[str, ScoreDecision] = {}

        suggested_agent: str | None = None
        risk_level = "LOW"
        requires_human_approval = False

        any_onnx = False
        any_fallback = False
        fallback_reasons: list[str] = []

        if not questions:
            runtime, load_reason = self._resolve_runtime()
            any_onnx = runtime is not None
            any_fallback = runtime is None
            if load_reason:
                fallback_reasons.append(load_reason)

        for q_name, q_config in questions.items():
            q_type = str(q_config.get("type", "")).lower()
            instructions = q_config.get("instructions")

            if q_type == "choice":
                crit = q_config.get("criteria", q_config.get("choices", []))
                dec, used_onnx, fb_reason = self._decide_choice_detailed(
                    state, crit, instructions=instructions
                )
                choices[q_name] = dec
                any_onnx = any_onnx or used_onnx
                any_fallback = any_fallback or (not used_onnx)
                if fb_reason:
                    fallback_reasons.append(fb_reason)
                if q_name in ["agent", "target_agent", "subagent"]:
                    suggested_agent = dec.choice

            elif q_type == "noul":
                hypo = q_config.get("hypothesis", instructions or q_name)
                noul_dec, used_onnx, fb_reason = self._decide_noul_detailed(
                    state, hypo, instructions=instructions
                )
                nouls[q_name] = noul_dec
                any_onnx = any_onnx or used_onnx
                any_fallback = any_fallback or (not used_onnx)
                if fb_reason:
                    fallback_reasons.append(fb_reason)
                if q_name in ["requires_approval", "human_approval"] and noul_dec.decision:
                    requires_human_approval = True

            elif q_type == "score":
                rubric = q_config.get("rubric", q_config.get("criteria", []))
                score_dec, used_onnx, fb_reason = self._decide_score_detailed(
                    state, rubric, instructions=instructions
                )
                scores[q_name] = score_dec
                any_onnx = any_onnx or used_onnx
                any_fallback = any_fallback or (not used_onnx)
                if fb_reason:
                    fallback_reasons.append(fb_reason)
                if q_name in ["risk", "risk_level"]:
                    if score_dec.score >= 2:
                        risk_level = "HIGH"
                    elif score_dec.score == 1:
                        risk_level = "MEDIUM"

        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
        is_real_onnx = any_onnx and not any_fallback
        engine_name = "onnx-nli" if is_real_onnx else "heuristic-fallback"
        fallback_reason: str | None = (
            None
            if is_real_onnx
            else (
                "; ".join(dict.fromkeys(fallback_reasons))
                or "ONNX NLI runtime unavailable; fell back to heuristic engine"
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
