"""
RAG and Code Intelligence CLI Commands (index, blast-radius, eval).
Modular domain command package decomposed according to ADR-026 / IMP-0023.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from corporate_engineer.rag.ast_indexer import ASTCodebaseIndexer


def register_index_parser(subparsers: Any) -> argparse.ArgumentParser:
    """Register parser for `index` command."""
    index_parser = subparsers.add_parser("index", help="Index codebase using AST")
    index_parser.add_argument("--path", default=".", help="Path to index")
    index_parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )
    index_parser.add_argument("--output", default=None, help="Optional file path to write output")
    index_parser.add_argument(
        "--impact-of", default=None, help="Calculate blast radius for target symbol or file"
    )
    index_parser.add_argument(
        "--depth", type=int, default=3, help="Max propagation depth for impact analysis"
    )
    return index_parser


def register_blast_radius_parser(subparsers: Any) -> argparse.ArgumentParser:
    """Register parser for `blast-radius` command."""
    blast_parser = subparsers.add_parser(
        "blast-radius", help="Calculate blast radius and affected tests for a code change"
    )
    blast_parser.add_argument("target", help="Target function, class name or file path")
    blast_parser.add_argument(
        "--depth", type=int, default=3, help="Max transitive propagation depth (default: 3)"
    )
    blast_parser.add_argument("--workspace", default=".", help="Workspace path (default: .)")
    blast_parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format (default: text)"
    )
    blast_parser.add_argument("--output", default=None, help="Optional file path to write output")
    return blast_parser


def register_eval_parser(subparsers: Any) -> argparse.ArgumentParser:
    """Register parser for `eval` command."""
    eval_parser = subparsers.add_parser(
        "eval", help="Evaluate code quality using semantic corporate scorecard (EDD)"
    )
    eval_parser.add_argument(
        "path", nargs="?", default="src", help="Path to file or directory to evaluate"
    )
    eval_parser.add_argument(
        "--min-score",
        type=float,
        default=80.0,
        help="Minimum composite score to pass gate (default: 80.0)",
    )
    eval_parser.add_argument(
        "--strict", action="store_true", help="Fail if any axis fails or any violation occurs"
    )
    eval_parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format (default: text)"
    )
    return eval_parser


def _run_blast_radius_analysis(
    target_val: str,
    workspace: str = ".",
    depth: int = 3,
    format_type: str = "text",
    output_path: str | None = None,
) -> int:
    from corporate_engineer.models import BlastRadiusReport
    from corporate_engineer.rag.impact import BlastRadiusAnalyzer

    is_file = target_val.endswith(".py") or "/" in target_val or "\\" in target_val
    analyzer = BlastRadiusAnalyzer(workspace_root=workspace)
    report: BlastRadiusReport = analyzer.analyze_impact(
        target_file=target_val if is_file else None,
        target_symbol=target_val if not is_file else None,
        max_depth=depth,
    )

    if format_type == "json":
        output_str = report.model_dump_json(indent=2)
    else:
        lines = [
            "\n" + "=" * 60,
            f"💥 Blast Radius Analysis: {report.target} [{report.target_type}]",
            "=" * 60,
            f"• Total Impacted Files: {report.total_impacted_files}",
            f"• Total Impacted Symbols: {report.total_impacted_symbols}",
            f"• Impacted Test Suites: {len(report.affected_tests)}",
            f"• Recommended Surgical Test Command:\n  👉 {report.recommended_test_command}",
            "\n--- Impact Propagation Tree ---",
        ]
        if not report.impacted_nodes:
            lines.append("  (No external callers or importers detected - localized component)")
        else:
            nodes_by_depth: dict[int, list[Any]] = {}
            for n in report.impacted_nodes:
                nodes_by_depth.setdefault(n.depth, []).append(n)

            for d in sorted(nodes_by_depth.keys()):
                tag = "DIRECT IMPACT" if d == 1 else f"TRANSITIVE IMPACT (Depth {d})"
                lines.append(f"\n📂 [{tag}]")
                for n in nodes_by_depth[d]:
                    lines.append(f"  • {n.file_path} :: {n.symbol} ({n.relationship})")

        if report.affected_tests:
            lines.append("\n🧪 [AFFECTED TESTS]")
            for t in report.affected_tests:
                lines.append(f"  ✓ {t}")

        lines.append("=" * 60 + "\n")
        output_str = "\n".join(lines)

    if output_path:
        out_p = Path(output_path).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(output_str, encoding="utf-8")
        print(f"✅ Análise de Blast Radius salva em: {out_p}")
    else:
        print(output_str)

    return 0


def handle_index(args: argparse.Namespace) -> int:
    target = Path(args.path).resolve()

    if getattr(args, "impact_of", None):
        return _run_blast_radius_analysis(
            target_val=args.impact_of,
            workspace=str(target),
            depth=getattr(args, "depth", 3),
            format_type=args.format,
            output_path=args.output,
        )

    indexer = ASTCodebaseIndexer(root_path=target)

    if args.format == "json":
        indexed_files: list[dict[str, Any]] = []
        for root, dirs, files in os.walk(target):
            dirs[:] = [
                d
                for d in dirs
                if not d.startswith(".") and d not in {"venv", ".venv", "__pycache__"}
            ]
            for f in sorted(files):
                if f.endswith(".py"):
                    full_p = Path(root) / f
                    rel_p = str(full_p.relative_to(target))
                    symbols = indexer.index_file(full_p)
                    indexed_files.append({"file": rel_p, "symbols": symbols})
        payload = {"root": str(target), "files": indexed_files}
        output_str = json.dumps(payload, indent=2)
    else:
        output_str = indexer.build_codebase_outline()

    if args.output:
        out_p = Path(args.output).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(output_str, encoding="utf-8")
        print(f"✅ Índice AST salvo com sucesso em: {out_p}")
    else:
        print(output_str)

    return 0


def handle_blast_radius(args: argparse.Namespace) -> int:
    return _run_blast_radius_analysis(
        target_val=args.target,
        workspace=args.workspace,
        depth=args.depth,
        format_type=args.format,
        output_path=getattr(args, "output", None),
    )


def handle_eval(args: argparse.Namespace) -> int:
    from corporate_engineer.eval.scorecard import SemanticCodeEvaluator

    evaluator = SemanticCodeEvaluator()
    target = Path(args.path)
    if target.is_file():
        content = target.read_text(encoding="utf-8", errors="ignore")
        report = evaluator.evaluate_source(
            content, file_path=str(target), min_passing_score=args.min_score
        )
    else:
        report = evaluator.evaluate_directory(target, min_passing_score=args.min_score)

    if args.format == "json":
        print(report.model_dump_json(indent=2))
    else:
        print("\n" + "=" * 60)
        print(f"📊 Corporate Scorecard (EDD) - Target: {report.target_path}")
        print("=" * 60)
        print(
            f"• Composite Score: {report.composite_score:.1f} / 100.0  [Grade: {report.letter_grade}]"
        )
        print(
            f"• Gate Status: {'✅ PASS' if report.passed_gate else '❌ FAIL'} "
            f"(Min required: {report.min_passing_score:.1f})"
        )
        print(f"• Total Files Evaluated: {report.total_files_evaluated}")
        print(f"• Total Functions Evaluated: {report.total_functions_evaluated}")
        print(f"• Total Violations: {report.total_violations}")
        print("\n--- Corporate Axes Breakdown ---")
        for ax in report.axes:
            status = "✅ PASS" if ax.passed else "❌ FAIL"
            bar_len = int(ax.score // 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            print(f"[{bar}] {ax.score:5.1f}% (Weight: {ax.weight:.2f}) {status} - {ax.axis_name}")
            if ax.violations:
                for v in ax.violations[:3]:
                    print(f"    ⚠️  {v}")
                if len(ax.violations) > 3:
                    print(f"    ... e mais {len(ax.violations) - 3} violação(ões)")
        print("=" * 60 + "\n")

    if args.strict and (not report.passed_gate or report.total_violations > 0):
        return 1
    return 0 if report.passed_gate else 1
