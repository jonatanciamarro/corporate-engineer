#!/usr/bin/env python3
"""
proactive_advisor.py - Antigravity PreInvocation Hook for Proactive Intelligence.
Executes before the model turn: short-circuits on invocationNum > 1 with {},
and on turn 1 delegates to hooks_runner for a concise (<= 300 chars) summary.
Contract: Reads JSON on stdin, outputs valid protojson on stdout.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def get_workspace_root(payload: dict[str, Any] | None = None) -> Path:
    """Resolve repository workspace root from payload, cwd, or script location."""
    if payload:
        for wp in payload.get("workspacePaths") or []:
            candidate = Path(str(wp)).resolve()
            if (candidate / "src").exists() or (candidate / "state.md").exists():
                return candidate

    current = Path.cwd().resolve()
    if current.name == ".agents" and (current.parent / "state.md").exists():
        return current.parent
    for parent in [current] + list(current.parents):
        if (parent / "state.md").exists() or (parent / ".git").exists():
            return parent

    script_root = Path(__file__).resolve().parents[3]
    if (script_root / "state.md").exists() or (script_root / "src").exists():
        return script_root
    return current


def _is_follow_up_invocation(payload: dict[str, Any]) -> bool:
    """Return True when invocationNum > 1 (subsequent turns within the same prompt)."""
    raw_num = payload.get("invocationNum", 1)
    try:
        return int(1 if raw_num is None else raw_num) > 1
    except (TypeError, ValueError):
        return False


def run_proactive_advisor_hook() -> None:
    """Antigravity PreInvocation hook entrypoint."""
    raw_input_data: dict[str, Any] = {}
    try:
        if not sys.stdin.isatty():
            content = sys.stdin.read()
            if content.strip():
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    raw_input_data = parsed
    except (json.JSONDecodeError, OSError):
        raw_input_data = {}

    if _is_follow_up_invocation(raw_input_data):
        sys.stdout.write("{}")
        sys.stdout.flush()
        return

    root = get_workspace_root(raw_input_data)
    src_dir = str(root / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    try:
        from corporate_engineer.orchestrator.hooks_runner import (
            generate_pre_invocation_hook_output,
        )

        output = generate_pre_invocation_hook_output(raw_input_data, workspace_root=root)
    except Exception as exc:  # noqa: BLE001
        msg = f"[CORP-PIPELINE / PROACTIVE INTELLIGENCE]: Active (fallback: {exc})"
        if len(msg) > 300:
            msg = msg[:297] + "..."
        output = {"injectSteps": [{"systemMessage": {"systemMessage": msg}}]}

    sys.stdout.write(json.dumps(output, ensure_ascii=False))
    sys.stdout.flush()


if __name__ == "__main__":
    run_proactive_advisor_hook()
