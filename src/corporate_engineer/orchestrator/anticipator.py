"""
Proactive Anticipation Engine (IMP-0025).
Synthesizes 2-steps-ahead tactical intelligence and execution plans
anchored in codebase AST, System-One fast routing, and corporate quality gates.
"""

from __future__ import annotations

from pathlib import Path

from corporate_engineer.models import AnticipationPlan, AnticipationStep
from corporate_engineer.prompt.refiner import ContextAwarePromptRefiner
from corporate_engineer.system_one.router import SystemOneRouter


class ProactiveAnticipator:
    """Orquestrador de inteligência antecipatória proativa (2 passos à frente)."""

    def __init__(self, workspace_path: Path | str | None = None) -> None:
        self.workspace_path = Path(workspace_path) if workspace_path else Path.cwd()
        self.refiner = ContextAwarePromptRefiner(workspace_path=self.workspace_path)
        self.router = SystemOneRouter()

    def anticipate(self, prompt: str) -> AnticipationPlan:
        """Analisa a intenção e gera um plano antecipatório completo de 2 passos."""
        # 1. Refinamento de contexto semântico e extração de AST
        spec = self.refiner.refine(prompt)
        domain = spec.target_domain

        # Suporte a domínios especializados como lora
        prompt_lower = prompt.lower()
        if any(k in prompt_lower for k in ["lora", "sft", "remotion", "manim", "darkfactory"]):
            domain = "lora"

        # 2. Roteamento de agentes pelo Sistema 1
        primary_decision = self.router.route_agent(prompt)
        primary_agent = primary_decision.choice

        recommended_agents = [primary_agent]
        if primary_agent == "architect":
            recommended_agents.extend(["tdd-guide", "code-reviewer"])
        elif primary_agent == "tdd-guide":
            recommended_agents.extend(["code-reviewer", "python-reviewer"])
        elif primary_agent == "security-reviewer":
            recommended_agents.extend(["architect", "code-reviewer"])
        else:
            recommended_agents.extend(["tdd-guide", "code-reviewer"])

        # Deduplicação preservando ordem
        seen: set[str] = set()
        dedup_agents: list[str] = []
        for a in recommended_agents:
            if a not in seen:
                seen.add(a)
                dedup_agents.append(a)

        # 3. Estimativa de Risco
        risk_level = "LOW"
        if spec.is_bypassed:
            risk_level = "LOW"
        elif any(
            k in prompt_lower for k in ["auth", "security", "token", "delete", "drop", "mutation"]
        ):
            risk_level = "HIGH"
        elif len(spec.affected_modules) > 1 or domain in ["orchestrator", "mcp"]:
            risk_level = "MEDIUM"

        # 4. Síntese dos Passos
        target_impl_files = spec.affected_modules
        if not target_impl_files:
            target_impl_files = [f"src/corporate_engineer/{domain}/core.py"]

        if spec.is_bypassed:
            step1 = AnticipationStep(
                step_index=1,
                phase="QUALITY",
                action=f"Executar comando operacional de verificação rápida: {prompt.strip()}",
                rationale="Fast-path operacional sem necessidade de novo ciclo TDD.",
                target_files=[],
                tdd_scenario="Verificar saída do comando no terminal.",
            )
            step2 = AnticipationStep(
                step_index=2,
                phase="MONITORING",
                action="Avaliar status do ambiente e prosseguir com a próxima etapa do roadmap.",
                rationale="Manter conformidade contínua do workspace.",
                target_files=["state.md"],
            )
        else:
            suggested_test_file = f"tests/test_{domain}.py"
            tdd_scenario = (
                spec.tdd_test_scenarios[0]
                if spec.tdd_test_scenarios
                else f"Escrever teste automatizado comprovando falha (RED) para {spec.core_intent}."
            )

            step1 = AnticipationStep(
                step_index=1,
                phase="CONTRACT/TDD",
                action=(
                    f"Definir modelos DTO Pydantic v2 e escrever cenário TDD RED em {suggested_test_file}"
                ),
                rationale=(
                    "Shift-Left TDD mandatório: nenhum código de produção em src/ deve ser alterado "
                    "sem teste prévio comprovando a falha."
                ),
                target_files=["src/corporate_engineer/models.py", suggested_test_file],
                tdd_scenario=tdd_scenario,
            )

            # 5. Síntese do Passo 2 (Subsequente)
            step2 = AnticipationStep(
                step_index=2,
                phase="IMPLEMENT/AUDIT",
                action=(
                    f"Implementar lógica em {', '.join(target_impl_files)}, auto-remediar AST e "
                    "executar Pre-Flight completo (Ruff, Mypy, Pytest, Zero-Secret)"
                ),
                rationale=(
                    "Completar ciclo até GREEN, garantir 0 erros nos 4 gates de qualidade e "
                    "manter branch sincronizada no remote origin."
                ),
                target_files=target_impl_files,
                tdd_scenario="Aprovação de 100% dos testes e verificação de blast radius.",
            )

        blast_radius = spec.affected_modules if spec.affected_modules else target_impl_files

        return AnticipationPlan(
            raw_prompt=prompt,
            target_domain=domain,
            risk_level=risk_level,
            recommended_agents=dedup_agents,
            step_immediate_1=step1,
            step_subsequent_2=step2,
            blast_radius_estimate=blast_radius,
            structured_metaprompt=spec.metaprompt,
        )

    def format_markdown(self, plan: AnticipationPlan) -> str:
        """Formata o plano antecipatório em um bloco markdown executivo e sagaz."""
        agents_str = ", ".join(f"`{a}`" for a in plan.recommended_agents)
        blast_str = (
            ", ".join(f"`{f}`" for f in plan.blast_radius_estimate)
            if plan.blast_radius_estimate
            else "`Nenhum`"
        )

        lines = [
            "🧠 **[CORP-PIPELINE / PROACTIVE INTELLIGENCE: 2 PASSOS À FRENTE]**",
            f"• **Domínio Detectado**: `{plan.target_domain.upper()}` | **Nível de Risco**: `{plan.risk_level}`",
            f"• **Subagentes Recomendados**: {agents_str}",
            f"• **Estimativa de Blast Radius**: {blast_str}",
            "",
            f"📍 **Passo 1 (Imediato)** [{plan.step_immediate_1.phase}]:",
            f"  - **Ação**: {plan.step_immediate_1.action}",
            f"  - **Justificativa**: {plan.step_immediate_1.rationale}",
        ]

        if plan.step_immediate_1.target_files:
            targets = ", ".join(f"`{f}`" for f in plan.step_immediate_1.target_files)
            lines.append(f"  - **Arquivos-Alvo**: {targets}")
        if plan.step_immediate_1.tdd_scenario:
            lines.append(f"  - **Cenário TDD**: {plan.step_immediate_1.tdd_scenario}")

        lines.extend(
            [
                "",
                f"🚀 **Passo 2 (Subsequente)** [{plan.step_subsequent_2.phase}]:",
                f"  - **Ação**: {plan.step_subsequent_2.action}",
                f"  - **Justificativa**: {plan.step_subsequent_2.rationale}",
            ]
        )

        if plan.step_subsequent_2.target_files:
            targets2 = ", ".join(f"`{f}`" for f in plan.step_subsequent_2.target_files)
            lines.append(f"  - **Arquivos-Alvo**: {targets2}")

        return "\n".join(lines)
