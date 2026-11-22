"""
Tests for Proactive Anticipation Engine & Full E2E Lifecycle Hooks (IMP-0025).
Follows Shift-Left TDD standard.
"""

from __future__ import annotations

from pathlib import Path

from corporate_engineer.models import AnticipationPlan, AnticipationStep

# ============================================================================
# 1. Models & DTO Tests
# ============================================================================


def test_anticipation_step_model_valid():
    step = AnticipationStep(
        step_index=1,
        phase="TDD",
        action="Escrever teste unitário RED",
        rationale="Shift-Left TDD obrigatório",
        target_files=["tests/test_feature.py"],
        tdd_scenario="Verificar comportamento esperado antes da implementação",
    )
    assert step.step_index == 1
    assert step.phase == "TDD"
    assert "test_feature.py" in step.target_files[0]


def test_anticipation_plan_model_valid():
    step1 = AnticipationStep(
        step_index=1,
        phase="CONTRACT/TDD",
        action="Definir modelos Pydantic v2 e teste RED",
        rationale="Garantir invariantes e tipagem estrita",
        target_files=["src/corporate_engineer/models.py", "tests/test_feature.py"],
    )
    step2 = AnticipationStep(
        step_index=2,
        phase="IMPLEMENT/AUDIT",
        action="Implementar lógica de negócio e validar Pre-Flight",
        rationale="Garantir 0 erros Ruff/Mypy e 0 segredos",
        target_files=["src/corporate_engineer/feature.py"],
    )
    plan = AnticipationPlan(
        raw_prompt="Implementar novo endpoint SSE no cliente MCP",
        target_domain="mcp",
        risk_level="MEDIUM",
        recommended_agents=["architect", "tdd-guide", "code-reviewer"],
        step_immediate_1=step1,
        step_subsequent_2=step2,
        blast_radius_estimate=["src/corporate_engineer/mcp/client.py"],
    )
    assert plan.target_domain == "mcp"
    assert plan.risk_level == "MEDIUM"
    assert plan.step_immediate_1.step_index == 1
    assert plan.step_subsequent_2.step_index == 2
    assert "architect" in plan.recommended_agents


def test_anticipation_plan_serialization():
    step1 = AnticipationStep(
        step_index=1,
        phase="PLANNING",
        action="Analisar arquitetura",
        rationale="Requisitos formais",
    )
    step2 = AnticipationStep(
        step_index=2,
        phase="IMPLEMENT",
        action="Construir funcionalidade",
        rationale="Código de produção",
    )
    plan = AnticipationPlan(
        raw_prompt="Criar novo plugin",
        target_domain="orchestrator",
        risk_level="LOW",
        recommended_agents=["architect"],
        step_immediate_1=step1,
        step_subsequent_2=step2,
    )
    dumped = plan.model_dump_json()
    loaded = AnticipationPlan.model_validate_json(dumped)
    assert loaded.raw_prompt == plan.raw_prompt
    assert loaded.step_immediate_1.action == step1.action


# ============================================================================
# 2. ProactiveAnticipator Engine Tests
# ============================================================================


def test_proactive_anticipator_domain_and_steps(tmp_path: Path):
    from corporate_engineer.orchestrator.anticipator import ProactiveAnticipator

    anticipator = ProactiveAnticipator(workspace_path=tmp_path)
    plan = anticipator.anticipate("Implementar novo cliente MCP com suporte a SSE e reconexão")

    assert plan.target_domain == "mcp"
    assert plan.step_immediate_1.phase in ["CONTRACT/TDD", "PLANNING", "TDD"]
    assert plan.step_subsequent_2.phase in ["IMPLEMENT", "IMPLEMENT/AUDIT", "AUDIT"]
    assert len(plan.recommended_agents) > 0
    assert "mcp" in plan.blast_radius_estimate[0].lower() or len(plan.blast_radius_estimate) > 0


def test_proactive_anticipator_fast_path_bypass(tmp_path: Path):
    from corporate_engineer.orchestrator.anticipator import ProactiveAnticipator

    anticipator = ProactiveAnticipator(workspace_path=tmp_path)
    plan = anticipator.anticipate("pytest")

    assert plan.target_domain in ["operational", "quality"]
    assert plan.risk_level == "LOW"
    assert (
        "pytest" in plan.step_immediate_1.action.lower()
        or "executar" in plan.step_immediate_1.action.lower()
    )


def test_proactive_anticipator_format_markdown(tmp_path: Path):
    from corporate_engineer.orchestrator.anticipator import ProactiveAnticipator

    anticipator = ProactiveAnticipator(workspace_path=tmp_path)
    plan = anticipator.anticipate("Adicionar validação AST no gerador de dataset LoRA")
    md = anticipator.format_markdown(plan)

    assert "CORP-PIPELINE" in md
    assert "PROACTIVE INTELLIGENCE" in md
    assert "Passo 1 (Imediato)" in md
    assert "Passo 2 (Subsequente)" in md
    assert plan.target_domain in md.lower() or "lora" in md.lower()


# ============================================================================
# 3. PreToolUse Zero-Secret Guard Hook Tests
# ============================================================================


def test_pre_tool_security_guard_allows_clean_code(tmp_path: Path):
    from corporate_engineer.quality.tool_security_guard import evaluate_tool_security

    clean_payload = {
        "toolCall": {
            "name": "write_file",
            "args": {
                "Path": str(tmp_path / "clean.py"),
                "Content": "def hello():\n    return 'Hello World'\n",
            },
        }
    }
    decision = evaluate_tool_security(clean_payload)
    assert decision["decision"] == "allow"


def test_pre_tool_security_guard_denies_secret_in_write_file(tmp_path: Path):
    from corporate_engineer.quality.tool_security_guard import evaluate_tool_security

    # Construct AWS key dynamically so secret scanner doesn't flag test file itself
    raw_key = "AKIA" + "1234567890ABCDEF"
    leaked_payload = {
        "toolCall": {
            "name": "write_file",
            "args": {
                "Path": str(tmp_path / "secret.py"),
                "Content": f"AWS_KEY = '{raw_key}'\n",
            },
        }
    }
    decision = evaluate_tool_security(leaked_payload)
    assert decision["decision"] == "deny"
    assert "Zero-Secret Guard" in decision["reason"] or "Secret" in decision["reason"]


def test_pre_tool_security_guard_denies_secret_in_edit_file(tmp_path: Path):
    from corporate_engineer.quality.tool_security_guard import evaluate_tool_security

    # Construct token dynamically so secret scanner doesn't flag test file itself
    raw_token = "ghp_" + "A" * 36
    leaked_payload = {
        "toolCall": {
            "name": "edit_file",
            "args": {
                "Path": str(tmp_path / "config.py"),
                "Replacement": f"GITHUB_TOKEN = '{raw_token}'\n",
            },
        }
    }
    decision = evaluate_tool_security(leaked_payload)
    assert decision["decision"] == "deny"


# ============================================================================
# 4. PostToolUse Auto-Healer Hook Tests
# ============================================================================


def test_post_tool_auto_healer_repairs_ast_and_formats(tmp_path: Path):
    from corporate_engineer.quality.tool_auto_healer import handle_post_tool_use

    src_dir = tmp_path / "src" / "corporate_engineer"
    src_dir.mkdir(parents=True)
    target_file = src_dir / "broken_sample.py"
    # AST anti-pattern: __init__ without -> None and redundant pass
    target_file.write_text(
        "class Sample:\n    def __init__(self):\n        pass\n        self.x = 1\n",
        encoding="utf-8",
    )

    payload = {
        "toolCall": {
            "name": "write_file",
            "args": {
                "Path": str(target_file),
            },
        },
        "cwd": str(tmp_path),
    }

    result = handle_post_tool_use(payload, workspace_root=tmp_path)
    assert isinstance(result, dict)

    # File should be fixed: -> None should be added to __init__
    repaired_code = target_file.read_text(encoding="utf-8")
    assert "-> None" in repaired_code


# ============================================================================
# 5. Git Hooks Installer Tests
# ============================================================================


def test_install_git_hooks_creates_files(tmp_path: Path):
    from corporate_engineer.quality.git_hooks_installer import install_git_hooks

    git_hooks_dir = tmp_path / ".git" / "hooks"
    git_hooks_dir.mkdir(parents=True)

    installed = install_git_hooks(workspace_root=tmp_path)
    assert installed is True

    pre_commit = git_hooks_dir / "pre-commit"
    pre_push = git_hooks_dir / "pre-push"

    assert pre_commit.exists()
    assert pre_push.exists()

    content_commit = pre_commit.read_text(encoding="utf-8", errors="ignore")
    assert "secret_scanner.py" in content_commit or "secret" in content_commit.lower()

    content_push = pre_push.read_text(encoding="utf-8", errors="ignore")
    assert "audit" in content_push


# ============================================================================
# 6. Proactive Pre-Invocation Hook Script Interface Tests
# ============================================================================


def test_proactive_pre_invocation_hook_output_format(tmp_path: Path):
    from corporate_engineer.orchestrator.hooks_runner import generate_pre_invocation_hook_output

    hook_input = {
        "lastUserInput": "Criar novo DAG de automação",
        "workspacePaths": [str(tmp_path)],
    }
    output = generate_pre_invocation_hook_output(hook_input, workspace_root=tmp_path)

    assert "injectSteps" in output
    inject_steps = output["injectSteps"]
    assert len(inject_steps) > 0
    sys_msg = inject_steps[0]["systemMessage"]["systemMessage"]
    assert "CORP-PIPELINE" in sys_msg
    assert "PROACTIVE INTELLIGENCE" in sys_msg
