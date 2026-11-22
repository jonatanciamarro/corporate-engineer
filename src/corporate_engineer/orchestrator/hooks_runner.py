"""
Hooks Runner & Pipeline Injection Bridge (IMP-0025).
Connects Antigravity lifecycle events (SessionStart, PreInvocation, Stop)
to the Corp-Pipeline Master Orchestrator, Proactive Anticipator, and Quality Gates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from corporate_engineer.git_utils import generate_pr_url, get_current_branch
from corporate_engineer.orchestrator.anticipator import ProactiveAnticipator


def generate_pre_invocation_hook_output(
    payload: dict[str, Any],
    workspace_root: Path | str | None = None,
) -> dict[str, Any]:
    """
    Gera a carga útil de injeção protojson para o evento PreInvocation do Antigravity.
    Injeta o plano proativo 2 passos à frente e a URL de PR 1-clique (se em feature branch).
    """
    root = Path(workspace_root).resolve() if workspace_root else Path.cwd().resolve()
    last_user_input = payload.get("lastUserInput", "").strip()

    messages: list[str] = []

    # 1. Inteligência Proativa Antecipatória (2 Passos à Frente)
    if last_user_input:
        try:
            anticipator = ProactiveAnticipator(workspace_path=root)
            plan = anticipator.anticipate(last_user_input)
            messages.append(anticipator.format_markdown(plan))
        except Exception as e:  # noqa: BLE001
            messages.append(
                f"🧠 **[CORP-PIPELINE / PROACTIVE INTELLIGENCE]**: Ativo (análise preliminar: {e})"
            )

    # 2. Injeção de 1-Click PR Link se em branch de desenvolvimento
    try:
        branch = get_current_branch(root)
        if branch.startswith(("feat/", "fix/", "chore/", "refactor/")):
            pr_info = generate_pr_url(repo_path=root, branch=branch, ensure_pushed=False)
            push_status = (
                "✅ Sincronizado no origin"
                if pr_info.get("pushed")
                else "⚠️ Local apenas (push pendente)"
            )
            pr_block = (
                "\n🔗 **[1-CLICK GITHUB PR LINK ACTIVE]**:\n"
                f"• Branch: `{pr_info['branch']}` ➔ `{pr_info['base']}` | Ticket: `{pr_info['ticket_id']}`\n"
                f"• Push Status: {push_status}\n"
                f"• URL Pré-Preenchida: {pr_info['url']}\n"
                "• *Invariante Mandatória: Efetuar `git push -u origin <branch>` antes de fornecer a URL final ao usuário.*"
            )
            messages.append(pr_block)
    except Exception:  # noqa: BLE001, S110
        pass

    full_system_message = (
        "\n\n".join(messages) if messages else "🟢 Corp-Pipeline Master Orchestrator: READY"
    )

    return {"injectSteps": [{"systemMessage": {"systemMessage": full_system_message}}]}
