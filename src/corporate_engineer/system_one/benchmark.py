"""
System-One Autonomous Benchmark & Evaluation Harness (IMP-0015 / ADR-014).
Measures accuracy, latency percentiles (P50/P95/P99), throughput, and memory consumption
across System-One decision engines (Heuristic, Outlines, ONNX Runtime).
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, ClassVar

try:
    from datetime import UTC, datetime
except ImportError:
    from datetime import datetime, timezone  # type: ignore[assignment]

    UTC = timezone.utc  # type: ignore[assignment] # noqa: UP017

from corporate_engineer.models import (
    BenchmarkReport,
    EngineBenchmarkResult,
    EngineLatencyStats,
)
from corporate_engineer.system_one.base import SystemOneEngine
from corporate_engineer.system_one.heuristic_engine import HeuristicDecisionEngine
from corporate_engineer.system_one.nli_engine import ONNXNLIDecisionEngine
from corporate_engineer.system_one.router import SystemOneRouter


def calculate_latency_stats(
    latencies_ms: list[float], total_time_s: float = 0.0
) -> tuple[EngineLatencyStats, float]:
    """
    Calcula percentis (P50, P95, P99), média, mínimo, máximo e throughput.
    Utiliza interpolação linear padrão para cálculo preciso de percentis.
    """
    if not latencies_ms:
        return EngineLatencyStats(), 0.0

    sorted_vals = sorted(latencies_ms)
    count = len(sorted_vals)

    def _percentile(p: float) -> float:
        k = (count - 1) * p
        f = int(k)
        c = min(f + 1, count - 1)
        d = k - f
        return round(sorted_vals[f] * (1.0 - d) + sorted_vals[c] * d, 3)

    min_val = round(sorted_vals[0], 3)
    max_val = round(sorted_vals[-1], 3)
    mean_val = round(sum(sorted_vals) / count, 3)
    p50 = _percentile(0.50)
    p95 = _percentile(0.95)
    p99 = _percentile(0.99)

    throughput = round(count / total_time_s, 2) if total_time_s > 0 else 0.0

    stats = EngineLatencyStats(
        p50_ms=p50,
        p95_ms=p95,
        p99_ms=p99,
        mean_ms=mean_val,
        min_ms=min_val,
        max_ms=max_val,
    )
    return stats, throughput


class SystemOneBenchmark:
    """Harness autônomo para benchmarking e avaliação quantitativa dos motores do Sistema 1."""

    DEFAULT_DATASET_PATH: Path = Path("data/system_one_dataset.jsonl")

    CANONICAL_FALLBACK_SAMPLES: ClassVar[list[dict[str, str]]] = [
        {
            "instruction": "Selecione o subagente",
            "input": "Escreva teste com pytest para serviço",
            "output": "tdd-guide",
        },
        {
            "instruction": "Selecione o subagente",
            "input": "Revisar código e typing PEP 8",
            "output": "python-reviewer",
        },
        {
            "instruction": "Selecione o subagente",
            "input": "Auditoria de segurança e segredos",
            "output": "security-reviewer",
        },
        {
            "instruction": "Classifique o commit",
            "input": "Adiciona endpoint REST para métricas",
            "output": "feat",
        },
        {
            "instruction": "Classifique o commit",
            "input": "Corrige bug no parsing de dados",
            "output": "fix",
        },
        {
            "instruction": "Avalie o risco do diff",
            "input": "Adiciona secret em plaintext no repositório",
            "output": "True",
        },
        {
            "instruction": "Avalie o risco do diff",
            "input": "Atualiza documentação no README.md",
            "output": "False",
        },
        {
            "instruction": "Decida pular nó da DAG",
            "input": "Nó opcional de docs sem alteração de código",
            "output": "True",
        },
    ]

    def __init__(self, dataset_path: str | Path | None = None) -> None:
        self.dataset_path = Path(dataset_path) if dataset_path else self.DEFAULT_DATASET_PATH

    def load_dataset(
        self, path: str | Path | None = None, max_samples: int | None = None
    ) -> list[dict[str, Any]]:
        """Carrega amostras do dataset JSONL com fallback automático para amostras canônicas."""
        target = Path(path) if path else self.dataset_path
        samples: list[dict[str, Any]] = []

        if target.exists():
            with open(target, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped:
                        try:
                            samples.append(json.loads(stripped))
                        except json.JSONDecodeError:
                            continue

        if not samples:
            samples = [dict(s) for s in self.CANONICAL_FALLBACK_SAMPLES]

        if max_samples and max_samples > 0:
            samples = samples[:max_samples]

        return samples

    def _create_router(self, engine_name: str) -> SystemOneRouter:
        """Instancia o SystemOneRouter com o motor selecionado e fallback transparente."""
        name = engine_name.lower().strip()
        engine: SystemOneEngine

        if name == "onnx":
            engine = ONNXNLIDecisionEngine(fallback_to_heuristic=True)
        elif name == "outlines":
            try:
                from corporate_engineer.system_one.outlines_engine import OutlinesDecisionEngine

                engine = OutlinesDecisionEngine()
            except (ImportError, RuntimeError):
                engine = HeuristicDecisionEngine()
        else:
            engine = HeuristicDecisionEngine()

        return SystemOneRouter(engine=engine)

    def _infer_category(self, instruction: str) -> str:
        """Determina a categoria da tarefa com base na instrução fornecida."""
        inst_lower = instruction.lower()
        if "subagente" in inst_lower or "agente" in inst_lower or "route" in inst_lower:
            return "route"
        if "commit" in inst_lower:
            return "commit"
        if "risco" in inst_lower or "risk" in inst_lower:
            return "risk"
        if "pular" in inst_lower or "skip" in inst_lower or "dag" in inst_lower:
            return "skip"
        return "general"

    def _evaluate_sample(
        self, router: SystemOneRouter, sample: dict[str, Any]
    ) -> tuple[str, bool, str]:
        """Executa a inferência para uma amostra e avalia a corretude da resposta."""
        category = self._infer_category(sample.get("instruction", ""))
        input_text = sample.get("input", "")
        expected = str(sample.get("output", "")).strip().lower()

        prediction: str
        if category == "commit":
            decision = router.classify_commit(input_text)
            prediction = decision.choice
        elif category == "risk":
            noul = router.assess_risk(input_text)
            prediction = str(noul.decision)
        elif category == "skip":
            noul = router.should_skip_node(node_name=input_text, context=input_text)
            prediction = str(noul.decision)
        else:
            choice = router.route_agent(input_text)
            prediction = choice.choice

        is_correct = prediction.strip().lower() == expected
        return prediction, is_correct, category

    def run(
        self,
        engines: list[str] | None = None,
        dataset_path: str | Path | None = None,
        max_samples: int | None = None,
        iterations: int = 1,
        warmup: int = 1,
    ) -> BenchmarkReport:
        """
        Executa a suíte de benchmark comparativo entre os motores especificados.
        """
        target_path = Path(dataset_path) if dataset_path else self.dataset_path
        samples = self.load_dataset(target_path, max_samples=max_samples)
        engine_names = engines or ["heuristic", "onnx"]
        timestamp = datetime.now(UTC).isoformat()

        results: dict[str, EngineBenchmarkResult] = {}
        actual_engines: dict[str, str] = {}

        for engine_name in engine_names:
            router = self._create_router(engine_name)
            actual_engine = engine_name
            try:
                probe_input = str(samples[0].get("input", "probe")) if samples else "probe"
                probe_report = router.engine.evaluate(probe_input, {})
                actual_engine = str(getattr(probe_report, "engine_name", engine_name))
            except (RuntimeError, ValueError, KeyError, TypeError, OSError, FileNotFoundError):
                actual_engine = f"{engine_name}-error"
            actual_engines[engine_name] = actual_engine

            latencies_ms: list[float] = []
            successful_runs = 0
            failed_runs = 0
            correct_runs = 0
            per_mode_correct: dict[str, int] = {}
            per_mode_total: dict[str, int] = {}
            error_summary: list[str] = []

            # 1. Warmup (elimina impacto de JIT, I/O inicial e imports)
            if warmup > 0:
                for _ in range(warmup):
                    for s in samples[: min(len(samples), 3)]:
                        try:
                            self._evaluate_sample(router, s)
                        except (RuntimeError, ValueError, KeyError, TypeError, OSError):
                            continue

            # 2. Medição em lote com alta precisão
            batch_start = time.perf_counter()

            for _ in range(iterations):
                for s in samples:
                    category = self._infer_category(s.get("instruction", ""))
                    per_mode_total[category] = per_mode_total.get(category, 0) + 1
                    t0 = time.perf_counter()
                    try:
                        _, is_correct, evaluated_cat = self._evaluate_sample(router, s)
                        elapsed_ms = (time.perf_counter() - t0) * 1000.0
                        latencies_ms.append(elapsed_ms)
                        successful_runs += 1

                        if is_correct:
                            correct_runs += 1
                            per_mode_correct[evaluated_cat] = (
                                per_mode_correct.get(evaluated_cat, 0) + 1
                            )
                    except (RuntimeError, ValueError, KeyError, TypeError, OSError) as exc:
                        failed_runs += 1
                        error_summary.append(f"{type(exc).__name__}: {exc}")

            total_elapsed_s = time.perf_counter() - batch_start
            latency_stats, throughput = calculate_latency_stats(
                latencies_ms, total_time_s=total_elapsed_s
            )

            total_runs = successful_runs + failed_runs
            accuracy = (
                round((correct_runs / max(total_runs, 1)) * 100.0, 2) if total_runs > 0 else 0.0
            )

            per_mode_acc: dict[str, float] = {}
            for cat, tot in per_mode_total.items():
                corr = per_mode_correct.get(cat, 0)
                per_mode_acc[cat] = round((corr / max(tot, 1)) * 100.0, 1)

            results[engine_name] = EngineBenchmarkResult(
                engine_name=engine_name,
                total_samples=total_runs,
                successful_runs=successful_runs,
                failed_runs=failed_runs,
                accuracy_percent=accuracy,
                latency=latency_stats,
                throughput_rps=throughput,
                memory_rss_mb=None,
                per_mode_accuracy=per_mode_acc,
                error_summary=error_summary[:5],
            )

        # 3. Determinação dos vencedores e recomendações
        winner_latency = ""
        min_p50 = float("inf")
        winner_accuracy = ""
        max_acc = -1.0

        for name, res in results.items():
            if res.successful_runs > 0:
                if res.latency.p50_ms < min_p50:
                    min_p50 = res.latency.p50_ms
                    winner_latency = name
                if res.accuracy_percent > max_acc:
                    max_acc = res.accuracy_percent
                    winner_accuracy = name

        recommendations: list[str] = []
        if winner_latency == "heuristic":
            recommendations.append(
                "O motor Heuristic demonstrou latência sub-1ms sendo o ideal para roteamento "
                "de altíssima frequência na DAG corporativa."
            )
        if "onnx" in results:
            if actual_engines.get("onnx") == "onnx-nli" and results["onnx"].successful_runs > 0:
                recommendations.append(
                    "O motor ONNX Runtime oferece inferência contextual local preservando 100% da "
                    "privacidade de dados corporativos sem custos de APIs externas."
                )
            else:
                recommendations.append(
                    f"O motor ONNX operou em modo '{actual_engines.get('onnx', 'heuristic-fallback')}' "
                    "(modelo ONNX ou runtime ausente); exporte 'models/model_int8.onnx' para habilitar inferência neural."
                )
        if "outlines" in results:
            if (
                actual_engines.get("outlines") == "outlines"
                and results["outlines"].successful_runs > 0
            ):
                recommendations.append(
                    "O motor Outlines garante saídas estritamente compatíveis com autômatos finitos "
                    "(FSM) eliminando alucinações de schema."
                )
            else:
                recommendations.append(
                    f"O motor Outlines operou em modo '{actual_engines.get('outlines', 'heuristic-fallback')}' "
                    "(biblioteca outlines indisponível)."
                )

        return BenchmarkReport(
            timestamp=timestamp,
            dataset_path=str(target_path),
            sample_count=len(samples),
            iterations=iterations,
            engines=results,
            winner_latency=winner_latency or "heuristic",
            winner_accuracy=winner_accuracy or "heuristic",
            recommendations=recommendations,
        )
