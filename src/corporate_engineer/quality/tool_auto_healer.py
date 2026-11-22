"""
PostToolUse Auto-Healer & Blast Radius Reflex (IMP-0025).
Executes immediately after write_file or edit_file to auto-repair AST violations,
format modified code with Ruff, and compute blast radius and impacted test suites.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from corporate_engineer.eval.fixer import ASTSelfHealingFixer
from corporate_engineer.rag.impact import BlastRadiusAnalyzer


def handle_post_tool_use(
    payload: dict[str, Any],
    workspace_root: Path | str | None = None,
) -> dict[str, Any]:
    """
    Manipula evento PostToolUse para ferramentas write_file e edit_file.
    Aplica auto-remediação de AST, formatação e cálculo de impacto.
    Retorna {} conforme o contrato protojson de PostToolUse.
    """
    root = Path(workspace_root).resolve() if workspace_root else Path.cwd().resolve()
    tool_call = payload.get("toolCall", {})
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args", {})

    if tool_name not in ("write_file", "edit_file"):
        return {}

    target_path_str = args.get("Path")
    if not target_path_str:
        return {}

    target_path = Path(target_path_str)
    if not target_path.is_absolute():
        target_path = (root / target_path).resolve()

    # Operar apenas sobre arquivos Python existentes
    if not target_path.exists() or target_path.suffix != ".py":
        return {}

    # 1. Auto-remediação de AST via ASTSelfHealingFixer
    try:
        source_code = target_path.read_text(encoding="utf-8", errors="ignore")
        fixer = ASTSelfHealingFixer()
        fixed_code, fixes = fixer.fix_code(source_code, file_path=str(target_path))

        if fixes and fixed_code != source_code:
            target_path.write_text(fixed_code, encoding="utf-8")
            fix_summaries = ", ".join(f"{f.rule_name} (L{f.line_number})" for f in fixes)
            sys.stderr.write(
                f"\n⚡ [AUTO-HEAL]: {len(fixes)} anti-padrão(ões) AST corrigido(s) em `{target_path.name}`: {fix_summaries}\n"
            )
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"\n⚠️ [AUTO-HEAL WARNING]: Falha na análise AST: {e}\n")

    # 2. Formatação via Ruff se disponível
    try:
        ruff_cmd = "ruff"
        venv_ruff = root / ".venv" / "Scripts" / "ruff.exe"
        if venv_ruff.exists():
            ruff_cmd = str(venv_ruff)

        subprocess.run(
            [ruff_cmd, "format", str(target_path)],
            check=False,
            capture_output=True,
            cwd=str(root),
        )
    except Exception:  # noqa: BLE001, S110
        pass

    # 3. Cálculo de Blast Radius e Testes Afetados
    try:
        analyzer = BlastRadiusAnalyzer(workspace_root=root)
        report = analyzer.analyze_file(target_path, max_depth=2)
        if report.affected_tests:
            tests_str = ", ".join(f"`{t}`" for t in report.affected_tests[:4])
            sys.stderr.write(
                f"🎯 [BLAST RADIUS]: {len(report.affected_tests)} teste(s) impactado(s): {tests_str}\n"
            )
    except Exception:  # noqa: BLE001, S110
        pass

    return {}
