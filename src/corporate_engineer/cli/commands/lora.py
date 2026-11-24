"""
LoRA Fine-Tuning & Synthetic Dataset Generation CLI Commands (lora generate, validate, export).
Modular domain command package decomposed according to ADR-026 / IMP-0023.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def register_lora_parser(subparsers: Any) -> argparse.ArgumentParser:
    """Register parser for `lora` command."""
    lora_parser = subparsers.add_parser(
        "lora",
        help="Gemini LoRA Modular Pipeline for DarkFactory (ADR-020)",
    )
    lora_sub = lora_parser.add_subparsers(dest="lora_subcommand", help="LoRA actions")

    # lora generate
    gen_parser = lora_sub.add_parser("generate", help="Generate synthetic DarkFactory LoRA dataset")
    gen_parser.add_argument(
        "--domains",
        default=None,
        help="Comma-separated domains (e.g. MOTION_REMOTION,MOTION_MANIM)",
    )
    gen_parser.add_argument(
        "--samples",
        type=int,
        default=10,
        help="Samples per domain (default: 10)",
    )
    gen_parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for generation (default: 42)",
    )
    gen_parser.add_argument(
        "--output",
        "-o",
        default="dataset.json",
        help="Output file path (default: dataset.json)",
    )

    # lora validate
    val_parser = lora_sub.add_parser("validate", help="Validate syntax and AST of LoRA dataset")
    val_parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Path to dataset JSON file to validate",
    )
    val_parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )

    # lora export
    exp_parser = lora_sub.add_parser(
        "export", help="Export dataset into Vertex AI JSONL train/validation splits"
    )
    exp_parser.add_argument(
        "--input",
        "-i",
        required=True,
        help="Path to dataset JSON file to export",
    )
    exp_parser.add_argument(
        "--output-dir",
        default="export",
        help="Output directory for train.jsonl and validation.jsonl (default: export)",
    )
    exp_parser.add_argument(
        "--split",
        type=float,
        default=0.8,
        help="Train split ratio (default: 0.8)",
    )
    exp_parser.add_argument(
        "--no-sanitize",
        action="store_true",
        help="Disable credential sanitization",
    )

    return lora_parser


def handle_lora(args: argparse.Namespace) -> int:
    """Handle LoRA pipeline subcommands (generate, validate, export)."""
    sub = getattr(args, "lora_subcommand", None)

    if sub == "generate":
        from corporate_engineer.lora.generator import LoraDatasetGenerator
        from corporate_engineer.models import LoraDatasetConfig, LoraDomain

        domains = None
        if getattr(args, "domains", None):
            domains = [LoraDomain(d.strip().upper()) for d in args.domains.split(",") if d.strip()]
        config = LoraDatasetConfig(
            domains=domains or list(LoraDomain),
            samples_per_domain=getattr(args, "samples", 10),
            seed=getattr(args, "seed", 42),
        )
        generator = LoraDatasetGenerator(config=config)
        dataset = generator.generate_dataset()
        data = [s.model_dump() for s in dataset]
        out_path = Path(getattr(args, "output", "dataset.json"))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print(
            f"[✓] Generated {len(dataset)} samples across {len(config.domains)} "
            f"domains to {out_path}"
        )
        return 0

    elif sub == "validate":
        from corporate_engineer.lora.validator import LoraSyntaxValidator
        from corporate_engineer.models import LoraTrainingSample

        in_path = Path(args.input)
        if not in_path.exists():
            print(f"[✗] File not found: {in_path}", file=sys.stderr)
            return 1
        data = json.loads(in_path.read_text(encoding="utf-8"))
        samples = [LoraTrainingSample.model_validate(item) for item in data]
        validator = LoraSyntaxValidator()
        report = validator.validate_batch(samples)
        fmt = getattr(args, "format", "text")
        if fmt == "json":
            print(report.model_dump_json(indent=2))
        else:
            print(
                f"[✓] Validation Report: Total: {report.total_samples}, "
                f"Valid: {report.valid_samples}, Invalid: {report.invalid_samples}, "
                f"Approved: {report.is_approved}"
            )
            if report.errors:
                print("Errors:")
                for err in report.errors:
                    print(f"  - {err}")
        return 0 if report.is_approved else 1

    elif sub == "export":
        from corporate_engineer.lora.exporter import LoraVertexExporter
        from corporate_engineer.models import LoraDatasetConfig, LoraTrainingSample

        in_path = Path(args.input)
        if not in_path.exists():
            print(f"[✗] File not found: {in_path}", file=sys.stderr)
            return 1
        data = json.loads(in_path.read_text(encoding="utf-8"))
        samples = [LoraTrainingSample.model_validate(item) for item in data]
        split = getattr(args, "split", 0.8)
        sanitize = not getattr(args, "no_sanitize", False)
        config = LoraDatasetConfig(train_split_ratio=split, sanitize_secrets=sanitize)
        exporter = LoraVertexExporter()
        result = exporter.export_dataset(samples, output_dir=args.output_dir, config=config)
        print(f"[✓] Exported {result.train_count} train samples to {result.train_file}")
        print(
            f"[✓] Exported {result.validation_count} validation samples to {result.validation_file}"
        )
        print(
            f"[✓] Estimated Tokens: {result.estimated_tokens}, "
            f"Sanitized Secrets: {result.sanitized_secrets_count}"
        )
        return 0

    else:
        from corporate_engineer.cli.parser import build_parser

        parser = build_parser()
        for action in parser._actions:
            if isinstance(action, argparse._SubParsersAction) and "lora" in action.choices:
                action.choices["lora"].print_help()
                return 0
        parser.print_help()
        return 0
