"""
Git Hooks Installer (IMP-0025).
Installs pre-commit and pre-push hooks in .git/hooks/ to enforce zero secret leaks,
linter conformity, and pre-flight quality verification before any git commit or push.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

PRE_COMMIT_SCRIPT = """#!/usr/bin/env sh
# Corp-Pipeline Git Hook: pre-commit
# Enforces Zero-Secret Guard, Ruff Linting and Surgical Quality Checks

echo "🔒 [CORP-PIPELINE PRE-COMMIT] Running Zero-Secret Scanner..."
if [ -f ".venv/Scripts/python" ]; then
    PYTHON_CMD=".venv/Scripts/python"
elif [ -f ".venv/bin/python" ]; then
    PYTHON_CMD=".venv/bin/python"
else
    PYTHON_CMD="python"
fi

$PYTHON_CMD .agents/skills/corp-pipeline/scripts/secret_scanner.py .
if [ $? -ne 0 ]; then
    echo "❌ [PRE-COMMIT REJECTED] Secret scanner detected credentials! Commit aborted."
    exit 1
fi

echo "🔍 [CORP-PIPELINE PRE-COMMIT] Running Ruff linter..."
if [ -f ".venv/Scripts/ruff" ]; then
    RUFF_CMD=".venv/Scripts/ruff"
elif [ -f ".venv/bin/ruff" ]; then
    RUFF_CMD=".venv/bin/ruff"
else
    RUFF_CMD="ruff"
fi

$RUFF_CMD check .
if [ $? -ne 0 ]; then
    echo "❌ [PRE-COMMIT REJECTED] Ruff lint errors detected! Run 'ruff check --fix .' before committing."
    exit 1
fi

echo "✅ [CORP-PIPELINE PRE-COMMIT] All local checks passed."
exit 0
"""

PRE_PUSH_SCRIPT = """#!/usr/bin/env sh
# Corp-Pipeline Git Hook: pre-push
# Enforces Strict Pre-Flight Audit before code is pushed to remote origin

echo "🚀 [CORP-PIPELINE PRE-PUSH] Running Strict Pre-Flight Audit..."
if [ -f ".venv/Scripts/python" ]; then
    PYTHON_CMD=".venv/Scripts/python"
elif [ -f ".venv/bin/python" ]; then
    PYTHON_CMD=".venv/bin/python"
else
    PYTHON_CMD="python"
fi

$PYTHON_CMD -m corporate_engineer.cli audit --strict
if [ $? -ne 0 ]; then
    echo "❌ [PRE-PUSH REJECTED] Pre-Flight Audit failed! Fix all errors before pushing."
    exit 1
fi

echo "✅ [CORP-PIPELINE PRE-PUSH] Strict Pre-Flight Audit PASS. Pushing to origin..."
exit 0
"""


def install_git_hooks(workspace_root: Path | str | None = None) -> bool:
    """Instala os hooks corporativos pre-commit e pre-push no diretório .git/hooks/."""
    root = Path(workspace_root).resolve() if workspace_root else Path.cwd().resolve()
    git_dir = root / ".git"

    if not git_dir.exists():
        return False

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    pre_commit_path = hooks_dir / "pre-commit"
    pre_push_path = hooks_dir / "pre-push"

    pre_commit_path.write_text(PRE_COMMIT_SCRIPT, encoding="utf-8")
    pre_push_path.write_text(PRE_PUSH_SCRIPT, encoding="utf-8")

    # Tornar executável em sistemas unix-like se aplicável
    try:
        for p in (pre_commit_path, pre_push_path):
            current_mode = os.stat(p).st_mode
            os.chmod(p, current_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        pass

    return True
