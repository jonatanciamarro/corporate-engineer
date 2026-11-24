#!/usr/bin/env python3
"""
run_hook.py - Universal Resilient Lifecycle Hook Launcher for Corp-Pipeline (IMP-0028 / ADR-027).
Resolves repository workspace root, detects the dedicated virtual environment (.venv),
ensures src/ is in sys.path, and dispatches execution safely in-process or via subprocess.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def resolve_workspace_root() -> Path:
    """Resolve the repository workspace root unambiguously."""
    # 1. Check relative to this script: .agents/orchestration/hooks/run_hook.py -> root is 4 levels up
    script_root = Path(__file__).resolve().parent.parent.parent.parent
    if (script_root / "state.md").exists() or (script_root / ".git").exists():
        return script_root

    # 2. Check current working directory and its parents
    cwd = Path.cwd().resolve()
    for candidate in [cwd] + list(cwd.parents):
        if (candidate / "state.md").exists() or (candidate / ".git").exists():
            return candidate

    return script_root


def get_venv_python(workspace_root: Path) -> Path | None:
    """Locate the .venv Python executable if it exists."""
    if os.name == "nt":
        venv_py = workspace_root / ".venv" / "Scripts" / "python.exe"
    else:
        venv_py = workspace_root / ".venv" / "bin" / "python"

    if venv_py.exists():
        return venv_py
    return None


def run_in_process(hook_name: str, workspace_root: Path) -> int:
    """Execute the hook in-process if compatible Python is running."""
    # Ensure src and .agents are in sys.path
    src_dir = str(workspace_root / "src")
    agents_dir = str(workspace_root / ".agents")
    hooks_dir = str(workspace_root / ".agents" / "orchestration" / "hooks")

    for path_entry in [src_dir, agents_dir, hooks_dir]:
        if path_entry not in sys.path:
            sys.path.insert(0, path_entry)

    # Normalize hook name
    clean_name = hook_name.replace(".py", "").strip()

    if clean_name == "session_start":
        from session_start import run_session_start_hook

        run_session_start_hook()
        return 0
    elif clean_name == "proactive_advisor":
        from proactive_advisor import run_proactive_advisor_hook

        run_proactive_advisor_hook()
        return 0
    elif clean_name == "pre_tool_security_guard":
        from pre_tool_security_guard import run_pre_tool_security_guard_hook

        run_pre_tool_security_guard_hook()
        return 0
    elif clean_name == "post_tool_auto_healer":
        from post_tool_auto_healer import run_post_tool_auto_healer_hook

        run_post_tool_auto_healer_hook()
        return 0
    elif clean_name == "session_turnover_gate":
        from session_turnover_gate import run_session_turnover_gate_hook

        run_session_turnover_gate_hook()
        return 0
    else:
        sys.stderr.write(f"[run_hook.py] Unknown hook name: {clean_name}\n")
        return 1


def main() -> int:
    if len(sys.argv) < 2:
        sys.stderr.write("Usage: python run_hook.py <hook_name> [args...]\n")
        return 1

    hook_name = sys.argv[1]
    workspace_root = resolve_workspace_root()
    venv_python = get_venv_python(workspace_root)

    current_python = Path(sys.executable).resolve()

    # If already running inside .venv or no .venv found, execute in-process directly
    if venv_python is None or current_python == venv_python.resolve():
        return run_in_process(hook_name, workspace_root)

    # If running from a different Python (e.g., system Python 3.10), forward to .venv python
    hooks_dir = workspace_root / ".agents" / "orchestration" / "hooks"
    target_script = hooks_dir / f"{hook_name.replace('.py', '')}.py"
    if not target_script.exists():
        sys.stderr.write(f"[run_hook.py] Hook script not found: {target_script}\n")
        return 1

    try:
        proc = subprocess.run(
            [str(venv_python), str(target_script)] + sys.argv[2:],
            check=False,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
            cwd=str(workspace_root),
        )
        return proc.returncode
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"[run_hook.py] Subprocess forwarding error: {exc}\n")
        return run_in_process(hook_name, workspace_root)


if __name__ == "__main__":
    sys.exit(main())
