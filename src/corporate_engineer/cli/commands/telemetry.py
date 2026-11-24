"""
OpenTelemetry and Distributed Tracing CLI Commands (telemetry).
Modular domain command package decomposed according to ADR-026 / IMP-0023.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any


def register_telemetry_parser(subparsers: Any) -> argparse.ArgumentParser:
    """Register parser for `telemetry` command."""
    tel_parser = subparsers.add_parser(
        "telemetry", help="Inspect and visualize OpenTelemetry agent traces"
    )
    tel_parser.add_argument("--file", default=None, help="Path to JSON trace file")
    tel_parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format (default: text)"
    )
    tel_parser.add_argument("--output", default=None, help="Optional file path to export report")
    return tel_parser


def _print_trace_report(
    report: Any, format_type: str = "text", output_path: str | None = None
) -> None:
    if format_type == "json":
        output_str = report.model_dump_json(indent=2)
    else:
        lines = [
            "\n" + "=" * 60,
            f"🛰️  OpenTelemetry Trace Report: {report.trace_id}",
            "=" * 60,
            f"• Root Operation: {report.root_span_name}",
            f"• Total Spans: {report.total_spans}",
            f"• Total Duration: {report.total_duration_ms:.2f} ms",
            f"• Total Tokens: {report.total_tokens}",
            f"• Global Status: {'✅ OK' if report.status == 'OK' else '❌ ERROR'}",
            "\n--- Spans Waterfall ---",
        ]
        for s in report.spans:
            status_icon = "✓" if s.status == "OK" else "✗"
            parent_info = f" (parent: {s.parent_span_id})" if s.parent_span_id else " (ROOT)"
            lines.append(f"  [{status_icon}] {s.name:<32} {s.duration_ms:8.2f} ms {parent_info}")
            if s.attributes:
                for k, v in list(s.attributes.items())[:3]:
                    lines.append(f"      • {k} = {v}")
            if s.error_message:
                lines.append(f"      ⚠️ Error: {s.error_message}")
        lines.append("=" * 60 + "\n")
        output_str = "\n".join(lines)

    if output_path:
        out_p = Path(output_path).resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(output_str, encoding="utf-8")
        print(f"✅ Relatório de telemetria salvo em: {out_p}")
    else:
        print(output_str)


def handle_telemetry(args: argparse.Namespace) -> int:
    from corporate_engineer.models import TraceReport
    from corporate_engineer.telemetry.tracer import AgentTracer

    if args.file:
        p = Path(args.file).resolve()
        if not p.exists():
            print(f"❌ Arquivo de trace não encontrado: {p}")
            return 1
        content = p.read_text(encoding="utf-8")
        report = TraceReport.model_validate_json(content)
    else:
        tracer = AgentTracer()
        with tracer.span("telemetry.sample", attributes={"sample": True}):
            pass
        report = tracer.export_trace()

    _print_trace_report(report, format_type=args.format, output_path=args.output)
    return 0
