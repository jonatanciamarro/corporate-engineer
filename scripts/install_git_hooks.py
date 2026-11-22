#!/usr/bin/env python3
"""
CLI script to install corporate pre-commit and pre-push hooks into .git/hooks/.
Usage: python scripts/install_git_hooks.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src is in python path
root = Path(__file__).resolve().parent.parent
src_dir = str(root / "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from corporate_engineer.quality.git_hooks_installer import install_git_hooks


def main() -> int:
    print(f"📦 [CORP-PIPELINE] Instalando Git Hooks corporativos em: {root / '.git' / 'hooks'} ...")
    success = install_git_hooks(workspace_root=root)
    if success:
        print("✅ [CORP-PIPELINE] Git hooks `pre-commit` e `pre-push` instalados com sucesso!")
        return 0
    else:
        print("❌ [CORP-PIPELINE] Diretório .git não encontrado.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
