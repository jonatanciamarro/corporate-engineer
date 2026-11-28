"""
Hooks Runner & Pipeline Injection Bridge (IMP-0025).
Connects Antigravity lifecycle events (SessionStart, PreInvocation, Stop)
to the Corp-Pipeline Master Orchestrator, Proactive Anticipator, and Quality Gates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from corporate_engineer import git_utils
from corporate_engineer.orchestrator.anticipator import ProactiveAnticipator

_MAX_TURN1_HOOK_CHARS = 300


def _parse_invocation_num(payload: dict[str, Any]) -> int:
    raw = payload.get("invocationNum", 1)
    if isinstance(raw, bool):
        return 1
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 1


def _truncate_hook_message(message: str, limit: int = _MAX_TURN1_HOOK_CHARS) -> str:
    if len(message) <= limit:
        return message
    return message[: limit - 3].rstrip() + "..."


def generate_pre_invocation_hook_output(
    payload: dict[str, Any],
    workspace_root: Path | str | None = None,
) -> dict[str, Any]:
    """
    Gera a carga útil de injeção protojson para o evento PreInvocation do Antigravity.
    No turno 1 injeta resumo compacto (<=300 chars); nos turnos seguintes retorna {}.
    """
    if _parse_invocation_num(payload) > 1:
        return {}

    root = Path(workspace_root).resolve() if workspace_root else Path.cwd().resolve()
    last_user_input = str(payload.get("lastUserInput", "")).strip()

    branch_suffix = ""
    try:
        branch = git_utils.get_current_branch(root)
        if branch.startswith(("feat/", "fix/", "chore/", "refactor/")):
            branch_suffix = f" [{branch}]"
    except Exception:  # noqa: BLE001, S110
        pass

    header = f"[CORP-PIPELINE / PROACTIVE INTELLIGENCE]{branch_suffix}"
    if last_user_input:
        try:
            anticipator = ProactiveAnticipator(workspace_path=root)
            plan = anticipator.anticipate(last_user_input)
            agents = ",".join(plan.recommended_agents[:2]) or "architect"
            action = " ".join(plan.step_immediate_1.action.split())
            summary = (
                f"{header} {plan.target_domain.upper()}({plan.risk_level})[{agents}]: {action}"
            )
        except Exception as exc:  # noqa: BLE001
            summary = f"{header} Active (fallback: {exc})"
    else:
        summary = f"{header} Ready."

    compact_message = _truncate_hook_message(summary)
    return {"injectSteps": [{"systemMessage": {"systemMessage": compact_message}}]}
