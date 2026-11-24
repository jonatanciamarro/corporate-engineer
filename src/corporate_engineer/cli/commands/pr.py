"""
Git Pull Request & 1-Click PR URL CLI Commands (pr-link).
Modular domain command package decomposed according to ADR-026 / IMP-0023.
"""

from __future__ import annotations

import argparse
import json
from typing import Any

from corporate_engineer.git_utils import generate_pr_url


def register_pr_parser(subparsers: Any) -> argparse.ArgumentParser:
    """Register parser for `pr-link` command."""
    pr_parser = subparsers.add_parser(
        "pr-link", help="Generate 1-click pre-filled GitHub Pull Request URL"
    )
    pr_parser.add_argument(
        "--branch", default=None, help="Target branch name (default: active branch)"
    )
    pr_parser.add_argument("--base", default="main", help="Base branch (default: main)")
    pr_parser.add_argument("--doc", default=None, help="Path to specific PR markdown file")
    pr_parser.add_argument(
        "--format", choices=["text", "json"], default="text", help="Output format"
    )
    pr_parser.add_argument(
        "--no-push",
        dest="push",
        action="store_false",
        default=True,
        help="Skip pushing branch to origin remote before generating URL (default: push is always-on)",
    )
    return pr_parser


def handle_pr_link(args: argparse.Namespace) -> int:
    info = generate_pr_url(
        repo_path=".",
        branch=args.branch,
        base=args.base,
        pr_doc_path=args.doc,
        ensure_pushed=args.push,
    )
    if args.format == "json":
        print(json.dumps(info, indent=2))
    else:
        print(f"🔗 Pre-Filled GitHub PR Link [{info['branch']} -> {info['base']}]:")
        print(f"  - Ticket: {info['ticket_id']}")
        print(f"  - Título: {info['title']}")
        push_label = "✅ Sincronizado no origin" if info.get("pushed") else "⚠️  Local apenas"
        print(f"  - Push Status: {push_label}")
        print(f"  - URL: {info['url']}")
    return 0
