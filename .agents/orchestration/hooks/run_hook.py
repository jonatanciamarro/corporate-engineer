#!/usr/bin/env python3
"""
run_hook.py - Universal Resilient Lifecycle Hook Launcher for Corp-Pipeline (IMP-0028 / ADR-027).
Resolves repository workspace root, detects the dedicated virtual environment (.venv),
ensures src/ is in sys.path, and dispatches execution safely in-process or via subprocess.
"""

from __future__ import annotations

import importlib.util
import os
import re
import runpy
import subprocess
import sys
from pathlib import Path

_HOOK_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")


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


def _resolve_hook_script(hook_name: str, workspace_root: Path) -> tuple[str, Path] | None:
    """Validate hook_name strictly and resolve its script path inside hooks dir."""
    clean_name = hook_name.strip().removesuffix(".py")
    if not _HOOK_NAME_PATTERN.fullmatch(clean_name):
        sys.stderr.write(f"[run_hook.py] Invalid hook name (blocked): {hook_name}\n")
        return None

    hooks_dir = (workspace_root / ".agents" / "orchestration" / "hooks").resolve()
    target_script = (hooks_dir / f"{clean_name}.py").resolve()
    if target_script.parent != hooks_dir or not target_script.is_file():
        sys.stderr.write(f"[run_hook.py] Hook script not found: {target_script}\n")
        return None

    return clean_name, target_script


def run_in_process(hook_name: str, workspace_root: Path) -> int:
    """Execute the hook in-process via dynamic discovery and importlib/runpy."""
    resolved = _resolve_hook_script(hook_name, workspace_root)
    if resolved is None:
        return 1
    clean_name, target_script = resolved

    src_dir = str(workspace_root / "src")
    agents_dir = str(workspace_root / ".agents")
    hooks_dir = str(workspace_root / ".agents" / "orchestration" / "hooks")

    for path_entry in [src_dir, agents_dir, hooks_dir]:
        if path_entry not in sys.path:
            sys.path.insert(0, path_entry)

    spec = importlib.util.spec_from_file_location(clean_name, target_script)
    if spec is None or spec.loader is None:
        sys.stderr.write(f"[run_hook.py] Unable to load hook spec: {target_script}\n")
        return 1

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    hook_fn = getattr(module, f"run_{clean_name}_hook", None)
    if callable(hook_fn):
        result = hook_fn()
        return result if isinstance(result, int) else 0

    try:
        runpy.run_path(str(target_script), run_name="__main__")
    except SystemExit as exc:
        if exc.code is None:
            return 0
        return exc.code if isinstance(exc.code, int) else 1
    return 0


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
    resolved = _resolve_hook_script(hook_name, workspace_root)
    if resolved is None:
        return 1
    _, target_script = resolved

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
