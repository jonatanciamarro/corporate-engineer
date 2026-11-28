#!/usr/bin/env python3
"""
session_start.py - Antigravity Lifecycle Hook for Corp-Pipeline Initialization.
Executes on SessionStart event, extracts a concise live summary from state.md
(<= 600 chars) without relying on broken git subprocesses, installs git hooks,
and injects valid protojson on stdout.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any


def get_workspace_root(payload: dict[str, Any] | None = None) -> Path:
    """Resolve repository workspace root from payload, cwd, or script location."""
    if payload:
        for wp in payload.get("workspacePaths") or []:
            candidate = Path(str(wp)).resolve()
            if (candidate / "state.md").exists() or (candidate / "src").exists():
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


def _clean_cell(text: str) -> str:
    """Strip markdown bold/code markers and status emojis from table cells."""
    cleaned = re.sub(r"[*_`]", "", text)
    cleaned = re.sub(r"[🟢🟡🔴⚠️✅❌]", "", cleaned)
    return " ".join(cleaned.split()).strip()


def _extract_state_metrics(state_file: Path) -> dict[str, str]:
    """Extract key Section 1 health metrics from state.md without external calls."""
    metrics: dict[str, str] = {}
    if not state_file.exists():
        return metrics

    try:
        content = state_file.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return metrics

    key_map = (
        ("Testes (Pytest", "tests"),
        ("Linter", "ruff"),
        ("Tipagem", "mypy"),
        ("Scanner de Segredos", "secrets"),
        ("Wiring", "wiring"),
        ("Branch Ativa", "branch"),
    )
    for line in content.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        label, status_val = cells[0], _clean_cell(cells[1])
        for needle, metric_key in key_map:
            if needle in label and metric_key not in metrics and status_val:
                metrics[metric_key] = status_val
    return metrics


def _read_git_head_branch(root: Path) -> str | None:
    """Read current branch directly from .git/HEAD without invoking git subprocess."""
    head_file = root / ".git" / "HEAD"
    if not head_file.is_file():
        return None
    try:
        content = head_file.read_text(encoding="utf-8", errors="ignore").strip()
    except OSError:
        return None
    if content.startswith("ref: refs/heads/"):
        return content.removeprefix("ref: refs/heads/").strip()
    return None


def build_session_summary(root: Path) -> str:
    """Build concise live SessionStart summary strictly within 600 characters."""
    state_file = root / "state.md"
    metrics = _extract_state_metrics(state_file)
    branch = _read_git_head_branch(root) or metrics.get("branch") or "unknown"

    disk_part = ""
    try:
        _, _, free = shutil.disk_usage(root)
        disk_part = f" | Disk: {free / (1024**3):.1f}GB free"
    except OSError:
        pass

    parts = [f"Corp-Pipeline Active | Branch: {branch}{disk_part}"]
    metric_bits: list[str] = []
    if "tests" in metrics:
        metric_bits.append(f"Tests: {metrics['tests']}")
    if "ruff" in metrics:
        metric_bits.append(f"Ruff: {metrics['ruff']}")
    if "mypy" in metrics:
        metric_bits.append(f"Mypy: {metrics['mypy']}")
    if "secrets" in metrics:
        metric_bits.append(f"Secrets: {metrics['secrets']}")
    if "wiring" in metrics:
        metric_bits.append(f"Wiring: {metrics['wiring']}")

    if metric_bits:
        parts.append("State: " + " | ".join(metric_bits))
    elif state_file.exists():
        parts.append("State: state.md synced")
    else:
        parts.append("State: state.md missing")

    parts.append(
        "Protocol: read state.md first; use Shift-Left TDD, registries in .agents/orchestration/, "
        "and corporate-engineer MCP/CLI before commit."
    )

    summary = "\n".join(parts)
    if len(summary) > 600:
        summary = summary[:597] + "..."
    return summary


def run_session_start_hook() -> None:
    """Antigravity SessionStart hook entrypoint."""
    raw_input_data: dict[str, Any] = {}
    try:
        if not sys.stdin.isatty():
            raw_input = sys.stdin.read()
            if raw_input.strip():
                parsed = json.loads(raw_input)
                if isinstance(parsed, dict):
                    raw_input_data = parsed
    except (json.JSONDecodeError, OSError):
        raw_input_data = {}

    root = get_workspace_root(raw_input_data)

    src_dir = str(root / "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

    # Best-effort silent installation of local git hooks without invoking git CLI
    try:
        from corporate_engineer.quality.git_hooks_installer import install_git_hooks

        install_git_hooks(workspace_root=root)
    except Exception:  # noqa: BLE001, S110
        pass

    welcome_msg = build_session_summary(root)
    output = {"injectSteps": [{"systemMessage": {"systemMessage": welcome_msg}}]}

    sys.stdout.write(json.dumps(output, ensure_ascii=False))
    sys.stdout.flush()


if __name__ == "__main__":
    run_session_start_hook()
