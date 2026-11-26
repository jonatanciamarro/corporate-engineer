"""
Prompt Intelligence and Context-Aware Metaprompt CLI Commands (prompt refine).
Modular domain command package decomposed according to ADR-026 / IMP-0023.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


def register_prompt_parser(subparsers: Any) -> argparse.ArgumentParser:
    """Register parser for `prompt` command."""
    prompt_parser = subparsers.add_parser(
        "prompt",
        help="Context-Aware Metaprompt Engine & Prompt Refiner (IMP-0018)",
    )
    prompt_sub = prompt_parser.add_subparsers(dest="prompt_subcommand", help="Prompt actions")
    refine_parser = prompt_sub.add_parser(
        "refine", help="Refine human prompt into context-aware metaprompt"
    )
    refine_parser.add_argument("prompt", help="Prompt text to refine")
    refine_parser.add_argument(
        "--bypass-gate",
        "-b",
        action="store_true",
        help="Force full refinement even for operational commands",
    )
    refine_parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="markdown",
        help="Output format: text, json, or markdown (default: markdown)",
    )
    refine_parser.add_argument(
        "--workspace",
        "-w",
        default=".",
        help="Workspace path for AST and code context (default: .)",
    )
    refine_parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Optional file path to write refined specification",
    )
    return prompt_parser


def handle_prompt(args: argparse.Namespace) -> int:
    """Handle prompt subcommands (refine)."""
    if getattr(args, "prompt_subcommand", None) != "refine":
        print("Usage: corporate-engineer prompt refine <prompt> [options]")
        return 1

    from corporate_engineer.prompt.refiner import ContextAwarePromptRefiner

    refiner = ContextAwarePromptRefiner(workspace_path=getattr(args, "workspace", "."))
    spec = refiner.refine(args.prompt, bypass_gate=getattr(args, "bypass_gate", False))

    fmt = getattr(args, "format", "markdown")
    output_str = refiner.format_output(spec, format_type=fmt)

    out_path = getattr(args, "output", None)
    if out_path:
        out_p = Path(out_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(output_str, encoding="utf-8")
        stream = sys.stderr if fmt == "json" else sys.stdout
        print(f"[✓] Refined prompt specification exported to {out_path}", file=stream)

    print(output_str)
    return 0
