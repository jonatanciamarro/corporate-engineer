"""
System-One Probabilistic Routing, Dataset & Benchmark CLI Commands (decide, dataset, benchmark).
Modular domain command package decomposed according to ADR-026 / IMP-0023.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any


def register_decide_parser(subparsers: Any) -> argparse.ArgumentParser:
    """Register parser for `decide` command."""
    decide_parser = subparsers.add_parser(
        "decide",
        help="Fast System-One probabilistic decisions, agent routing, and triage",
    )
    decide_parser.add_argument(
        "prompt",
        nargs="?",
        default="",
        help="Prompt, requirement, or state to evaluate",
    )
    decide_parser.add_argument(
        "--mode",
        choices=["route", "risk", "triage", "commit", "skip"],
        default="route",
        help="Decision mode: route agent, assess risk, full triage, commit type, or skip node (default: route)",
    )
    decide_parser.add_argument(
        "--diff",
        default="",
        help="Optional git diff content or file path for risk analysis",
    )
    decide_parser.add_argument(
        "--engine",
        choices=["heuristic", "outlines", "nli", "onnx", "auto"],
        default="auto",
        help="Decision engine backend (default: auto)",
    )
    decide_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    decide_parser.add_argument("--output", default=None, help="Optional file path to write output")
    return decide_parser


def register_dataset_parser(subparsers: Any) -> argparse.ArgumentParser:
    """Register parser for `dataset` command."""
    dataset_parser = subparsers.add_parser(
        "dataset",
        help="Synthetic dataset generation and Colab recipe for System-One SLM fine-tuning (IMP-0014)",
    )
    dataset_parser.add_argument(
        "action",
        choices=["generate", "recipe"],
        default="generate",
        nargs="?",
        help="Action: generate synthetic dataset or generate Colab training recipe (default: generate)",
    )
    dataset_parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Target output file path (default: data/system_one_dataset.jsonl or scripts/train_colab_recipe.py)",
    )
    dataset_parser.add_argument(
        "--samples",
        type=int,
        default=10,
        help="Samples per category for synthetic generation (default: 10)",
    )
    dataset_parser.add_argument(
        "--model",
        default="Qwen/Qwen2.5-0.5B-Instruct",
        help="Target SLM base model for Colab training recipe (default: Qwen/Qwen2.5-0.5B-Instruct)",
    )
    dataset_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    return dataset_parser


def register_benchmark_parser(subparsers: Any) -> argparse.ArgumentParser:
    """Register parser for `benchmark` command."""
    bench_parser = subparsers.add_parser(
        "benchmark",
        help="Autonomous Benchmark & Eval Harness for System-One decision engines (IMP-0015)",
    )
    bench_parser.add_argument(
        "--dataset",
        default="data/system_one_dataset.jsonl",
        help="Path to JSONL dataset (default: data/system_one_dataset.jsonl)",
    )
    bench_parser.add_argument(
        "--engines",
        nargs="+",
        default=["heuristic", "onnx"],
        help="Engines to benchmark: heuristic, onnx, outlines (default: heuristic onnx)",
    )
    bench_parser.add_argument(
        "--iterations",
        type=int,
        default=1,
        help="Number of iterations over the dataset (default: 1)",
    )
    bench_parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="Limit number of dataset samples to evaluate (default: all)",
    )
    bench_parser.add_argument(
        "--warmup",
        type=int,
        default=1,
        help="Warmup iterations before recording latencies (default: 1)",
    )
    bench_parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format: text, json, or markdown (default: text)",
    )
    bench_parser.add_argument(
        "--output",
        default=None,
        help="Optional file path to export benchmark report",
    )
    return bench_parser


def handle_decide(args: argparse.Namespace) -> int:
    from corporate_engineer.system_one.base import SystemOneEngine
    from corporate_engineer.system_one.heuristic_engine import HeuristicDecisionEngine
    from corporate_engineer.system_one.nli_engine import ONNXNLIDecisionEngine
    from corporate_engineer.system_one.outlines_engine import OutlinesDecisionEngine
    from corporate_engineer.system_one.router import SystemOneRouter

    engine: SystemOneEngine
    if args.engine == "outlines":
        engine = OutlinesDecisionEngine(fallback_to_heuristic=True)
    elif args.engine in ("nli", "onnx"):
        engine = ONNXNLIDecisionEngine(fallback_to_heuristic=True)
    else:
        engine = HeuristicDecisionEngine()

    router = SystemOneRouter(engine=engine)
    prompt = args.prompt or ""

    diff_content = args.diff or ""
    if diff_content and os.path.exists(diff_content) and os.path.isfile(diff_content):
        try:
            diff_content = Path(diff_content).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            pass

    if args.mode == "route":
        decision = router.route_agent(prompt)
        if args.format == "json":
            output_str = decision.model_dump_json(indent=2)
        else:
            output_str = (
                f"\n{'=' * 60}\n"
                f"⚡ SYSTEM-ONE AGENT ROUTING (IMP-0013)\n"
                f"{'=' * 60}\n"
                f"🎯 Target Agent  : {decision.choice}\n"
                f"📊 Confidence    : {decision.confidence:.2%}\n"
                f"💡 Rationale     : {decision.rationale}\n"
                f"⚙️  Engine        : {args.engine}\n"
            )
            if decision.probabilities:
                output_str += "📈 Distribution  :\n"
                for opt, prob in sorted(
                    decision.probabilities.items(), key=lambda x: x[1], reverse=True
                )[:5]:
                    output_str += f"   • {opt:<22}: {prob:.2%}\n"
            output_str += f"{'=' * 60}\n"

    elif args.mode == "risk":
        noul = router.assess_risk(diff_content or prompt)
        if args.format == "json":
            output_str = noul.model_dump_json(indent=2)
        else:
            risk_label = "🚨 HIGH RISK / CRITICAL" if noul.decision else "✅ LOW / MODERATE"
            output_str = (
                f"\n{'=' * 60}\n"
                f"🛡️  SYSTEM-ONE RISK ASSESSMENT (IMP-0013)\n"
                f"{'=' * 60}\n"
                f"⚖️  High Risk      : {noul.decision} ({risk_label})\n"
                f"📊 Probability    : {noul.probability:.2%}\n"
                f"💡 Rationale      : {noul.rationale}\n"
                f"{'=' * 60}\n"
            )

    elif args.mode == "commit":
        decision = router.classify_commit(diff_content or prompt)
        if args.format == "json":
            output_str = decision.model_dump_json(indent=2)
        else:
            output_str = (
                f"\n{'=' * 60}\n"
                f"🏷️  SYSTEM-ONE COMMIT CLASSIFICATION (IMP-0014)\n"
                f"{'=' * 60}\n"
                f"🎯 Commit Type   : {decision.choice}\n"
                f"📊 Confidence    : {decision.confidence:.2%}\n"
                f"💡 Rationale     : {decision.rationale}\n"
                f"{'=' * 60}\n"
            )

    elif args.mode == "skip":
        node_name = prompt or "security_scan"
        noul = router.should_skip_node(node_name=node_name, context=diff_content or prompt)
        if args.format == "json":
            output_str = noul.model_dump_json(indent=2)
        else:
            status_label = "⏭️  SKIP (DISPENSÁVEL)" if noul.decision else "▶️  EXECUTE (MANDATÓRIO)"
            output_str = (
                f"\n{'=' * 60}\n"
                f"⚡ SYSTEM-ONE DAG NODE SKIP EVALUATION (IMP-0014)\n"
                f"{'=' * 60}\n"
                f"📌 Target Node   : {node_name}\n"
                f"⚖️  Should Skip   : {noul.decision} ({status_label})\n"
                f"📊 Probability   : {noul.probability:.2%}\n"
                f"💡 Rationale     : {noul.rationale}\n"
                f"{'=' * 60}\n"
            )

    else:  # triage
        report = router.triage_quality_gate(prompt=prompt, diff=diff_content)
        if args.format == "json":
            output_str = report.model_dump_json(indent=2)
        else:
            output_str = (
                f"\n{'=' * 60}\n"
                f"🔬 SYSTEM-ONE QUALITY GATE TRIAGE (IMP-0013 / IMP-0014)\n"
                f"{'=' * 60}\n"
                f"🎯 Suggested Agent       : {report.suggested_agent or 'N/A'}\n"
                f"🚨 Risk Level             : {report.risk_level}\n"
                f"🛑 Requires Human Approval: {report.requires_human_approval}\n"
                f"⏱️  Duration               : {report.duration_ms:.2f} ms\n"
                f"⚙️  Engine                 : {report.engine_name}\n"
                f"{'=' * 60}\n"
            )

    if args.output:
        out_p = Path(args.output).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(output_str, encoding="utf-8")
        print(f"✅ Relatório salvo em: {out_p}")
    else:
        print(output_str)

    return 0


def handle_dataset(args: argparse.Namespace) -> int:
    from corporate_engineer.system_one.dataset import SystemOneDatasetGenerator
    from corporate_engineer.system_one.trainer import SystemOneTrainer

    if args.action == "recipe":
        trainer = SystemOneTrainer(model_id=args.model)
        out_path = Path(args.output or "scripts/train_system_one_colab.py").resolve()
        trainer.save_recipe(out_path)
        print(
            f"\n{'=' * 60}\n"
            f"🚀 SYSTEM-ONE COLAB 1-CLICK RECIPE GERADA (IMP-0014)\n"
            f"{'=' * 60}\n"
            f"📄 Arquivo Salvo : {out_path}\n"
            f"🤖 Modelo Alvo   : {args.model}\n"
            f"💡 Instruções    : Abra no Google Colab (GPU T4 grátis), faça upload do dataset JSONL e execute!\n"
            f"{'=' * 60}\n"
        )
        return 0

    generator = SystemOneDatasetGenerator()
    out_file = Path(args.output or "data/system_one_dataset.jsonl").resolve()
    report = generator.export_dataset(
        output_path=out_file,
        agent_samples=args.samples,
        risk_samples=args.samples,
        commit_samples=args.samples,
        skip_samples=args.samples,
    )

    if args.format == "json":
        print(report.model_dump_json(indent=2))
    else:
        print(
            f"\n{'=' * 60}\n"
            f"📦 SYSTEM-ONE SYNTHETIC DATASET GERADO (IMP-0014)\n"
            f"{'=' * 60}\n"
            f"📊 Total de Amostras : {report.total_samples}\n"
            f"📁 Arquivo de Saída  : {report.export_path}\n"
            f"🔒 Checksum SHA-256  : {report.hash_sha256[:16]}...\n"
            f"📈 Distribuição      :\n"
        )
        for cat, count in report.task_distribution.items():
            print(f"   • {cat:<22}: {count} amostras")
        print(f"{'=' * 60}\n")

    return 0


def handle_benchmark(args: argparse.Namespace) -> int:
    from corporate_engineer.system_one.benchmark import SystemOneBenchmark

    bench = SystemOneBenchmark(dataset_path=args.dataset)
    report = bench.run(
        engines=args.engines,
        dataset_path=args.dataset,
        max_samples=args.max_samples,
        iterations=args.iterations,
        warmup=args.warmup,
    )

    if args.format == "json":
        output_str = report.model_dump_json(indent=2)
    elif args.format == "markdown":
        lines = [
            f"# System-One Benchmark Report ({report.timestamp})",
            f"- **Dataset**: `{report.dataset_path}` ({report.sample_count} samples)",
            f"- **Iterations**: {report.iterations}",
            f"- **Winner Latência**: 🏆 `{report.winner_latency}`",
            f"- **Winner Acurácia**: 🎯 `{report.winner_accuracy}`",
            "",
            "| Motor | Acurácia (%) | P50 (ms) | P95 (ms) | P99 (ms) | Média (ms) | Throughput (RPS) |",
            "|---|---|---|---|---|---|---|",
        ]
        for name, res in report.engines.items():
            lines.append(
                f"| `{name}` | {res.accuracy_percent}% | {res.latency.p50_ms} | "
                f"{res.latency.p95_ms} | {res.latency.p99_ms} | {res.latency.mean_ms} | "
                f"{res.throughput_rps} |"
            )
        lines.append("")
        lines.append("### Recomendações:")
        for rec in report.recommendations:
            lines.append(f"- {rec}")
        output_str = "\n".join(lines)
    else:
        lines = [
            f"\n{'=' * 75}",
            "⚡  SYSTEM-ONE AUTONOMOUS BENCHMARK & EVAL HARNESS (IMP-0015)",
            f"{'=' * 75}",
            f"📁 Dataset           : {report.dataset_path} ({report.sample_count} amostras)",
            f"🔄 Iterações         : {report.iterations}",
            f"🏆 Vencedor Latência : {report.winner_latency}",
            f"🎯 Vencedor Acurácia : {report.winner_accuracy}",
            f"{'-' * 75}",
            f"{'MOTOR':<12} {'ACURÁCIA':<12} {'P50 (ms)':<10} {'P95 (ms)':<10} {'P99 (ms)':<10} {'THROUGHPUT':<12}",
            f"{'-' * 75}",
        ]
        for name, res in report.engines.items():
            acc_str = f"{res.accuracy_percent}%"
            p50_str = f"{res.latency.p50_ms:.3f}"
            p95_str = f"{res.latency.p95_ms:.3f}"
            p99_str = f"{res.latency.p99_ms:.3f}"
            rps_str = f"{res.throughput_rps:.1f} rps"
            lines.append(
                f"{name:<12} {acc_str:<12} {p50_str:<10} {p95_str:<10} {p99_str:<10} {rps_str:<12}"
            )
        lines.append(f"{'-' * 75}")
        lines.append("💡 Recomendações:")
        for rec in report.recommendations:
            lines.append(f"   • {rec}")
        lines.append(f"{'=' * 75}\n")
        output_str = "\n".join(lines)

    if args.output:
        out_p = Path(args.output)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(output_str, encoding="utf-8")
        print(f"[✓] Benchmark report exported to {args.output}")

    print(output_str)
    return 0
