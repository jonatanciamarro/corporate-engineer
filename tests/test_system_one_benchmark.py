"""
Testes unitários e de integração para o Autonomous Benchmark & Eval Harness (IMP-0015 / ADR-014).
Validação de modelos DTO, cálculo estatístico de latência (P50/P95/P99), harness de avaliação e CLI.
"""

from __future__ import annotations

import json
from pathlib import Path

from corporate_engineer.models import (
    BenchmarkReport,
    EngineBenchmarkResult,
    EngineLatencyStats,
)
from corporate_engineer.system_one.benchmark import (
    SystemOneBenchmark,
    calculate_latency_stats,
)


def test_benchmark_models_validation() -> None:
    """Verifica a validação e integridade dos modelos DTO Pydantic v2 do benchmark."""
    latency = EngineLatencyStats(
        p50_ms=0.45,
        p95_ms=0.85,
        p99_ms=1.10,
        mean_ms=0.50,
        min_ms=0.20,
        max_ms=1.20,
    )
    assert latency.p50_ms == 0.45
    assert latency.p95_ms == 0.85

    result = EngineBenchmarkResult(
        engine_name="heuristic",
        total_samples=20,
        successful_runs=20,
        failed_runs=0,
        accuracy_percent=95.0,
        latency=latency,
        throughput_rps=2000.0,
        per_mode_accuracy={"route": 100.0, "risk": 90.0},
    )
    assert result.engine_name == "heuristic"
    assert result.accuracy_percent == 95.0

    report = BenchmarkReport(
        timestamp="2026-11-22T10:00:00Z",
        dataset_path="data/system_one_dataset.jsonl",
        sample_count=20,
        iterations=1,
        engines={"heuristic": result},
        winner_latency="heuristic",
        winner_accuracy="heuristic",
        recommendations=["Heuristic engine is ideal for sub-1ms routing."],
    )
    dumped = report.model_dump_json()
    loaded = BenchmarkReport.model_validate_json(dumped)
    assert loaded.winner_latency == "heuristic"
    assert loaded.engines["heuristic"].throughput_rps == 2000.0


def test_calculate_latency_stats_empty() -> None:
    """Verifica o cálculo de estatísticas de latência com lista vazia."""
    stats, throughput = calculate_latency_stats([], total_time_s=0.0)
    assert stats.p50_ms == 0.0
    assert stats.mean_ms == 0.0
    assert throughput == 0.0


def test_calculate_latency_stats_values() -> None:
    """Verifica cálculo correto de P50, P95, P99 e throughput."""
    # 100 latências de 1.0ms a 100.0ms
    latencies_ms = [float(i) for i in range(1, 101)]
    stats, throughput = calculate_latency_stats(latencies_ms, total_time_s=1.0)

    assert stats.min_ms == 1.0
    assert stats.max_ms == 100.0
    assert stats.p50_ms == 50.5
    assert stats.p95_ms == 95.05
    assert stats.p99_ms == 99.01
    assert stats.mean_ms == 50.5
    assert throughput == 100.0


def test_system_one_benchmark_load_samples(tmp_path: Path) -> None:
    """Verifica o carregamento de dataset a partir de arquivo JSONL e fallback seguro."""
    dataset_file = tmp_path / "custom_samples.jsonl"
    sample_data = [
        {
            "instruction": "Selecione o subagente",
            "input": "Escreva teste com pytest",
            "output": "tdd-guide",
        },
        {"instruction": "Classifique o commit", "input": "Novo endpoint", "output": "feat"},
    ]
    with open(dataset_file, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(s) + "\n" for s in sample_data)

    benchmark = SystemOneBenchmark()
    samples = benchmark.load_dataset(dataset_file)
    assert len(samples) == 2
    assert samples[0]["output"] == "tdd-guide"

    # Fallback quando o arquivo não existe
    fallback_samples = benchmark.load_dataset(tmp_path / "nao_existe.jsonl")
    assert len(fallback_samples) > 0


def test_system_one_benchmark_run_heuristic(tmp_path: Path) -> None:
    """Verifica a execução do benchmark isolado para o motor heurístico."""
    dataset_file = tmp_path / "samples.jsonl"
    sample_data = [
        {
            "instruction": "Selecione o subagente",
            "input": "Escreva teste com pytest",
            "output": "tdd-guide",
        },
        {
            "instruction": "Selecione o subagente",
            "input": "Revisar código e typing",
            "output": "code-reviewer",
        },
        {"instruction": "Classifique o commit", "input": "Nova funcionalidade", "output": "feat"},
        {
            "instruction": "Avalie o risco do diff",
            "input": "Adiciona secret em plaintext",
            "output": "True",
        },
        {
            "instruction": "Decida pular nó da DAG",
            "input": "Nó opcional de docs sem alteração",
            "output": "True",
        },
    ]
    with open(dataset_file, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(s) + "\n" for s in sample_data)

    benchmark = SystemOneBenchmark()
    report = benchmark.run(
        engines=["heuristic"],
        dataset_path=dataset_file,
        iterations=2,
        warmup=1,
    )

    assert isinstance(report, BenchmarkReport)
    assert "heuristic" in report.engines
    heur_res = report.engines["heuristic"]
    assert heur_res.successful_runs == 10  # 5 samples * 2 iterações
    assert heur_res.failed_runs == 0
    assert heur_res.accuracy_percent > 0.0
    assert heur_res.latency.p50_ms >= 0.0
    assert heur_res.throughput_rps > 0.0
    assert report.winner_latency == "heuristic"
    assert len(report.recommendations) > 0


def test_system_one_benchmark_run_multiple_engines(tmp_path: Path) -> None:
    """Verifica benchmark comparativo entre heuristic e onnx."""
    benchmark = SystemOneBenchmark()
    report = benchmark.run(
        engines=["heuristic", "onnx"],
        max_samples=5,
        iterations=1,
        warmup=0,
    )

    assert "heuristic" in report.engines
    assert "onnx" in report.engines
    assert report.winner_latency in ["heuristic", "onnx"]
    assert report.winner_accuracy in ["heuristic", "onnx"]


def test_benchmark_cli_execution() -> None:
    """Verifica a invocação do subcomando corporate-engineer benchmark via CLI."""
    import subprocess
    import sys

    cmd = [
        sys.executable,
        "-m",
        "corporate_engineer.cli",
        "benchmark",
        "--engines",
        "heuristic",
        "--max-samples",
        "4",
        "--iterations",
        "1",
        "--format",
        "json",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert result.returncode == 0, f"Falha na CLI: {result.stderr}"
    data = json.loads(result.stdout)
    assert "engines" in data
    assert "heuristic" in data["engines"]
    assert data["winner_latency"] == "heuristic"
