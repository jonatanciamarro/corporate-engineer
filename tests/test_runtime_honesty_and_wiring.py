"""
tests/test_runtime_honesty_and_wiring.py - Shift-Left TDD Suite for IMP-0042 Pillars 2 & 3 (ADR-036).

Validates:
1. hooks_runner.py: invocationNum > 1 returns {} and turn-1 output <= 300 chars keeping
   CORP-PIPELINE & PROACTIVE INTELLIGENCE; session_start.py reads live metrics from state.md
   within <= 600 chars without failing on broken git output.
2. AutonomousEngineeringGraph.run_pipeline(dry_run=False, code_executor=None) returns
   SIMULATED_NO_EXECUTOR (audit_passed=False, is_simulated=True, blocks DELIVER, CLI exit 1),
   while dry_run=True preserves SUCCESS with is_simulated=True and explicit warning, and
   DELIVER never fabricates https://github.com/org/repo/... PR URLs on exception.
3. SwarmCoordinator marks unimplemented roles without role_executor or MCP tools as
   SKIPPED / skipped_tasks instead of OK, and run_consensus rejects APPROVED if skipped_tasks > 0.
4. SystemOneReport.fallback_reason is populated on ONNXNLI / Outlines heuristic fallbacks.
5. AdversarialRedTeam / AdversarialLoopCoordinator annotate heuristic-pattern-matcher mode.
6. CapabilityWiringAuditor validates cli/parser.py + cli/main.py registration and
   ContextAwarePromptRefiner.DOMAIN_KEYWORDS module paths.
7. SurgicalTestRunner handles git status dubious ownership (exit 128) cleanly without
   cascading to git diff (exit 129) or noisy raw git usage logs.
"""

from __future__ import annotations

import importlib.util
import io
import json
import logging
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
SESSION_START_PATH = WORKSPACE_ROOT / ".agents" / "orchestration" / "hooks" / "session_start.py"


def _load_module(name: str, file_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, file_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _create_mini_repo_with_cli_and_refiner(
    root: Path,
    *,
    register_in_cli: bool = True,
    refiner_module_path: str = "src/corporate_engineer/sample_engine.py",
) -> None:
    """Build a minimal isolated repository layout for CapabilityWiringAuditor tests."""
    src_pkg = root / "src" / "corporate_engineer"
    cli_pkg = src_pkg / "cli"
    cmd_pkg = cli_pkg / "commands"
    prompt_pkg = src_pkg / "prompt"
    tests_dir = root / "tests"

    for directory in (cmd_pkg, prompt_pkg, tests_dir):
        directory.mkdir(parents=True, exist_ok=True)

    (src_pkg / "__init__.py").write_text(
        "from corporate_engineer.prompt.refiner import ContextAwarePromptRefiner\n"
        "from corporate_engineer.sample_engine import SampleEngine\n\n"
        '__all__ = ["ContextAwarePromptRefiner", "SampleEngine"]\n',
        encoding="utf-8",
    )
    (src_pkg / "sample_engine.py").write_text(
        "class SampleEngine:\n    def run(self) -> int:\n        return 1\n",
        encoding="utf-8",
    )

    (cli_pkg / "__init__.py").write_text(
        "from corporate_engineer.cli.main import main\n"
        "from corporate_engineer.cli.parser import build_parser\n\n"
        '__all__ = ["build_parser", "main"]\n',
        encoding="utf-8",
    )
    (cmd_pkg / "__init__.py").write_text("", encoding="utf-8")
    (cmd_pkg / "sample.py").write_text(
        "def register_sample_parser(subparsers: object) -> None:\n"
        "    pass\n\n\n"
        "def handle_sample(args: object) -> int:\n"
        "    return 0\n",
        encoding="utf-8",
    )

    if register_in_cli:
        (cli_pkg / "parser.py").write_text(
            "import argparse\n"
            "from corporate_engineer.cli.commands.sample import register_sample_parser\n\n\n"
            "def build_parser() -> argparse.ArgumentParser:\n"
            "    parser = argparse.ArgumentParser()\n"
            "    subparsers = parser.add_subparsers(dest='command')\n"
            "    register_sample_parser(subparsers)\n"
            "    return parser\n",
            encoding="utf-8",
        )
        (cli_pkg / "main.py").write_text(
            "from corporate_engineer.cli.commands.sample import handle_sample\n\n"
            '_DISPATCH_MAP = {"sample": handle_sample}\n\n\n'
            "def main() -> int:\n"
            "    return 0\n",
            encoding="utf-8",
        )
    else:
        (cli_pkg / "parser.py").write_text(
            "import argparse\n\n\n"
            "def build_parser() -> argparse.ArgumentParser:\n"
            "    return argparse.ArgumentParser()\n",
            encoding="utf-8",
        )
        (cli_pkg / "main.py").write_text(
            "_DISPATCH_MAP = {}\n\n\ndef main() -> int:\n    return 0\n",
            encoding="utf-8",
        )

    (prompt_pkg / "__init__.py").write_text(
        "from corporate_engineer.prompt.refiner import ContextAwarePromptRefiner\n\n"
        '__all__ = ["ContextAwarePromptRefiner"]\n',
        encoding="utf-8",
    )
    (prompt_pkg / "refiner.py").write_text(
        "class ContextAwarePromptRefiner:\n"
        "    DOMAIN_KEYWORDS = {\n"
        '        "sample": {\n'
        '            "keywords": ["sample"],\n'
        f'            "modules": ["{refiner_module_path}"],\n'
        "        }\n"
        "    }\n",
        encoding="utf-8",
    )

    (tests_dir / "test_sample.py").write_text(
        "from corporate_engineer import ContextAwarePromptRefiner, SampleEngine\n"
        "from corporate_engineer.cli import build_parser, main\n"
        "from corporate_engineer.cli.commands.sample import handle_sample, register_sample_parser\n\n\n"
        "def test_smoke() -> None:\n"
        "    assert SampleEngine().run() == 1\n"
        "    assert ContextAwarePromptRefiner is not None\n"
        "    assert build_parser is not None and main is not None\n"
        "    assert register_sample_parser is not None and handle_sample is not None\n",
        encoding="utf-8",
    )


# =============================================================================
# 1. Hooks Runner & SessionStart Efficiency / Live Metrics
# =============================================================================


def test_hooks_runner_invocation_num_gt_1_returns_empty_dict(tmp_path: Path) -> None:
    """PreInvocation hook must return {} when invocationNum > 1 to avoid context spam."""
    from corporate_engineer.orchestrator.hooks_runner import generate_pre_invocation_hook_output

    output_turn2 = generate_pre_invocation_hook_output(
        {"lastUserInput": "Refatorar orquestrador", "invocationNum": 2},
        workspace_root=tmp_path,
    )
    assert output_turn2 == {}

    output_turn5 = generate_pre_invocation_hook_output(
        {"lastUserInput": "Executar auditoria", "invocationNum": 5},
        workspace_root=tmp_path,
    )
    assert output_turn5 == {}


def test_hooks_runner_turn_one_compact_no_pr_body_bloat(tmp_path: Path) -> None:
    """Turn-1 output must be <= 300 chars and preserve CORP-PIPELINE & PROACTIVE INTELLIGENCE."""
    from corporate_engineer.orchestrator.hooks_runner import generate_pre_invocation_hook_output

    pr_dir = tmp_path / "docs" / "pull_requests"
    pr_dir.mkdir(parents=True)
    (pr_dir / "PR-CORP-999.md").write_text(
        "# Pull Request: Giant PR\n\n" + ("Detalhes extensos do PR.\n" * 200),
        encoding="utf-8",
    )

    with patch(
        "corporate_engineer.git_utils.get_current_branch",
        return_value="feat/IMP-9999-test",
    ):
        output = generate_pre_invocation_hook_output(
            {
                "lastUserInput": "Criar novo servidor MCP stdio",
                "invocationNum": 1,
                "workspacePaths": [str(tmp_path)],
            },
            workspace_root=tmp_path,
        )

    assert "injectSteps" in output
    sys_msg = output["injectSteps"][0]["systemMessage"]["systemMessage"]
    assert "CORP-PIPELINE" in sys_msg
    assert "PROACTIVE INTELLIGENCE" in sys_msg
    assert len(sys_msg) <= 300
    assert "quick_pull=1" not in sys_msg


def test_session_start_reads_live_state_metrics_under_600_chars(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """session_start.py must inject live metrics from state.md within <= 600 chars."""
    (tmp_path / "state.md").write_text(
        "# Estado Atual do Projeto (`state.md`)\n\n"
        "| Métrica / Aspecto | Status Atual | Detalhes |\n"
        "|---|---|---|\n"
        "| **Branch Ativa** | `feat/IMP-0042-runtime` | Em progresso |\n"
        "| **Testes (Pytest + Hypothesis)** | 412/412 PASS | Suite completa |\n"
        "| **Wiring & Scorecard EDD** | 100% Wired | Scorecard 92.5/100 |\n",
        encoding="utf-8",
    )

    session_start_mod = _load_module("session_start_under_test", SESSION_START_PATH)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "stdin", io.StringIO("{}"))

    session_start_mod.run_session_start_hook()
    captured = capsys.readouterr()

    data = json.loads(captured.out)
    assert "injectSteps" in data
    sys_msg = data["injectSteps"][0]["systemMessage"]["systemMessage"]
    assert len(sys_msg) <= 600
    assert "412/412" in sys_msg
    assert "dubious ownership" not in sys_msg.lower()


# =============================================================================
# 2. Pipeline Honesty: run_pipeline() & CLI `run`
# =============================================================================


def test_run_pipeline_live_without_executor_blocks_delivery(tmp_path: Path) -> None:
    """run_pipeline(dry_run=False, code_executor=None) must return SIMULATED_NO_EXECUTOR."""
    from corporate_engineer.models import TaskInput
    from corporate_engineer.orchestrator.graph import AutonomousEngineeringGraph

    task = TaskInput(
        ticket_id="CORP-HONEST-01",
        description="Alterar lógica sem executor conectado",
        workspace_path=str(tmp_path),
        max_iterations=10,
    )
    graph = AutonomousEngineeringGraph(task=task)
    report = graph.run_pipeline(dry_run=False, strict_audit=False, code_executor=None)

    assert report.status == "SIMULATED_NO_EXECUTOR"
    assert report.audit_passed is False
    assert report.is_simulated is True
    assert report.final_phase != "DELIVER"
    assert len(report.warnings) >= 1


def test_cli_run_without_dry_run_exits_one(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """`corporate-engineer run` without --dry-run (no executor) must return exit code 1."""
    from corporate_engineer.cli import main

    ret = main(
        [
            "run",
            "--ticket",
            "CORP-CLI-HONEST",
            "--task",
            "Execução sem dry-run e sem executor",
            "--workspace",
            str(tmp_path),
        ]
    )
    captured = capsys.readouterr()
    assert ret == 1
    assert "SIMULATED_NO_EXECUTOR" in captured.out


def test_run_pipeline_dry_run_marks_is_simulated_and_warns(tmp_path: Path) -> None:
    """dry_run=True keeps SUCCESS & DELIVER for compatibility but sets is_simulated=True + warning."""
    from corporate_engineer.models import TaskInput
    from corporate_engineer.orchestrator.graph import AutonomousEngineeringGraph

    task = TaskInput(
        ticket_id="CORP-DRY-01",
        description="Simulação explícita em modo dry-run",
        workspace_path=str(tmp_path),
        max_iterations=10,
    )
    graph = AutonomousEngineeringGraph(task=task)
    report = graph.run_pipeline(dry_run=True, strict_audit=False)

    assert report.status == "SUCCESS"
    assert report.final_phase == "DELIVER"
    assert report.dry_run is True
    assert report.is_simulated is True
    assert len(report.warnings) >= 1


def test_run_pipeline_live_with_executor_and_git_error_never_fabricates_pr_url(
    tmp_path: Path,
) -> None:
    """Live run with real code_executor sets is_simulated=False; git failure sets pr_url=None."""
    from corporate_engineer.models import CodeDiff, RevisedPromptSpec, TaskInput
    from corporate_engineer.orchestrator.graph import AutonomousEngineeringGraph

    def real_executor(target: str, spec: RevisedPromptSpec) -> list[CodeDiff]:
        return [
            CodeDiff(
                file_path="src/corporate_engineer/generated.py",
                new_content="VALUE = 42\n",
                explanation="Generated by real executor",
            )
        ]

    task = TaskInput(
        ticket_id="CORP-LIVE-01",
        description="Implementar módulo via executor real",
        workspace_path=str(tmp_path),
        max_iterations=10,
    )
    graph = AutonomousEngineeringGraph(task=task)

    with patch(
        "corporate_engineer.git_utils.generate_pr_url",
        side_effect=RuntimeError("no git remote configured"),
    ):
        report = graph.run_pipeline(
            dry_run=False,
            strict_audit=False,
            code_executor=real_executor,
        )

    assert report.status == "SUCCESS"
    assert report.is_simulated is False
    assert report.final_phase == "DELIVER"
    assert report.details.get("pr_url") is None
    assert "https://github.com/org/repo" not in json.dumps(report.details)
    assert len(report.warnings) >= 1


# =============================================================================
# 3. SwarmCoordinator Honest Skipped-Role Contract
# =============================================================================


def test_swarm_coordinator_marks_unimplemented_role_skipped_not_ok(tmp_path: Path) -> None:
    """Roles without deterministic analyzer, role_executor, or MCP tools must be SKIPPED."""
    from corporate_engineer.models import SwarmMember
    from corporate_engineer.orchestrator.swarm import SwarmCoordinator

    src_pkg = tmp_path / "src" / "corporate_engineer"
    src_pkg.mkdir(parents=True)
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir(parents=True)
    (src_pkg / "__init__.py").write_text('__all__ = ["CleanMod"]\n', encoding="utf-8")
    (src_pkg / "clean_mod.py").write_text("class CleanMod:\n    pass\n", encoding="utf-8")
    (tests_dir / "test_clean_mod.py").write_text(
        "from corporate_engineer.clean_mod import CleanMod\n"
        "def test_clean() -> None:\n    assert CleanMod() is not None\n",
        encoding="utf-8",
    )

    coordinator = SwarmCoordinator(workspace_path=tmp_path)

    skipped_member = SwarmMember(
        agent_id="tdd-01",
        role="tdd-guide",
        task_prompt="Escrever testes unitários",
        allowed_tools=[],
    )
    skipped_res = coordinator.dispatch_task(skipped_member, "Escrever testes para CleanMod")
    assert skipped_res.success is False
    assert skipped_res.status == "SKIPPED"
    assert skipped_res.error is not None
    assert "No role_executor or deterministic analyzer" in skipped_res.error

    sec_res = coordinator.dispatch_task(
        SwarmMember(agent_id="sec-01", role="security-reviewer", allowed_tools=[]),
        "Auditar segredos",
    )
    assert sec_res.success is True
    assert sec_res.status == "COMPLETED"

    fanout_report = coordinator.run_fan_out(
        goal="Mixed fan-out honesty test",
        subtasks=[
            {"role": "security-reviewer", "task": "Auditar segredos"},
            {"role": "tdd-guide", "task": "Gerar testes"},
        ],
    )
    assert fanout_report.successful_tasks == 1
    assert fanout_report.skipped_tasks == 1
    assert fanout_report.execution_mode == "deterministic-analyzer"
    assert not fanout_report.aggregated_consensus.startswith("APPROVED")

    consensus_report = coordinator.run_consensus(
        target_description="Revisão com papel não implementado",
        reviewer_roles=["architect", "tdd-guide"],
    )
    assert consensus_report.skipped_tasks >= 1
    assert "APPROVED" not in consensus_report.aggregated_consensus


# =============================================================================
# 4. System-One fallback_reason & Adversarial Heuristic Transparency
# =============================================================================


def test_system_one_engines_populate_fallback_reason_on_heuristic_fallback(
    tmp_path: Path,
) -> None:
    """ONNXNLIDecisionEngine and OutlinesDecisionEngine must set fallback_reason on fallback."""
    from corporate_engineer.system_one.nli_engine import ONNXNLIDecisionEngine
    from corporate_engineer.system_one.outlines_engine import OutlinesDecisionEngine

    nli_fb = ONNXNLIDecisionEngine(
        model_path=tmp_path / "missing_model.onnx",
        fallback_to_heuristic=True,
    )
    nli_report = nli_fb.evaluate(
        state="Revisar arquitetura",
        questions={"agent": {"type": "choice", "choices": ["architect", "tdd-guide"]}},
    )
    assert nli_report.engine_name == "heuristic-fallback"
    assert nli_report.fallback_reason is not None and len(nli_report.fallback_reason.strip()) > 0

    with patch.dict("sys.modules", {"outlines": None}):
        outlines_fb = OutlinesDecisionEngine(fallback_to_heuristic=True)
        outlines_report = outlines_fb.evaluate(
            state="Revisar arquitetura",
            questions={"agent": {"type": "choice", "choices": ["architect", "tdd-guide"]}},
        )
    assert outlines_report.engine_name == "heuristic-fallback"
    assert (
        outlines_report.fallback_reason is not None
        and len(outlines_report.fallback_reason.strip()) > 0
    )

    outlines_real = OutlinesDecisionEngine(generator_override=MagicMock(return_value="architect"))
    real_report = outlines_real.evaluate(
        state="Desenhar ADR",
        questions={"agent": {"type": "choice", "choices": ["architect", "tdd-guide"]}},
    )
    assert real_report.engine_name == "outlines"
    assert real_report.fallback_reason is None


def test_adversarial_engine_annotates_heuristic_pattern_matcher_mode() -> None:
    """Adversarial loop must transparently tag heuristic-pattern-matcher analysis mode."""
    from corporate_engineer.orchestrator.adversarial import AdversarialLoopCoordinator

    coord = AdversarialLoopCoordinator()
    bypassed = coord.run_dialectical_loop(
        plan_id="ADV-LOW",
        plan_text="pytest",
        risk_level="LOW",
    )
    assert "heuristic-pattern-matcher" in bypassed.verdict.bypass_reason

    attacked = coord.run_dialectical_loop(
        plan_id="ADV-HIGH",
        plan_text="Implementar pool de threads sem controle de lock e sem timeout",
        risk_level="HIGH",
        force_attack=True,
    )
    assert "heuristic-pattern-matcher" in attacked.initial_attack.attack_narrative


# =============================================================================
# 5. CapabilityWiringAuditor CLI Registration & DOMAIN_KEYWORDS Validation
# =============================================================================


def test_capability_wiring_auditor_checks_cli_registration_and_domain_keywords(
    tmp_path: Path,
) -> None:
    """CapabilityWiringAuditor must fail on unwired cli/commands or broken DOMAIN_KEYWORDS."""
    from corporate_engineer.quality.wiring_auditor import CapabilityWiringAuditor

    clean_ws = tmp_path / "clean_ws"
    _create_mini_repo_with_cli_and_refiner(clean_ws, register_in_cli=True)
    clean_report = CapabilityWiringAuditor(workspace_root=clean_ws).audit()
    assert clean_report.passed is True

    unregistered_cli_ws = tmp_path / "unregistered_cli_ws"
    _create_mini_repo_with_cli_and_refiner(unregistered_cli_ws, register_in_cli=False)
    cli_fail_report = CapabilityWiringAuditor(workspace_root=unregistered_cli_ws).audit()
    assert cli_fail_report.passed is False
    assert any("cli/commands/sample.py" in item for item in cli_fail_report.unwired_modules)

    broken_refiner_ws = tmp_path / "broken_refiner_ws"
    _create_mini_repo_with_cli_and_refiner(
        broken_refiner_ws,
        register_in_cli=True,
        refiner_module_path="src/corporate_engineer/ghost_missing_module.py",
    )
    refiner_fail_report = CapabilityWiringAuditor(workspace_root=broken_refiner_ws).audit()
    assert refiner_fail_report.passed is False
    combined_messages = " ".join(
        [*refiner_fail_report.unwired_modules, *refiner_fail_report.remediation_actions]
    )
    assert "ghost_missing_module.py" in combined_messages


# =============================================================================
# 6. SurgicalTestRunner & git_utils Dubious Ownership Resilience
# =============================================================================


def test_surgical_runner_dubious_ownership_aborts_diff_cascade(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """git status exit 128 (dubious ownership) must return [] cleanly without running git diff."""
    from corporate_engineer.quality.surgical_runner import SurgicalTestRunner

    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(list(cmd))
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=128,
            stdout="",
            stderr="fatal: detected dubious ownership in repository at '/repo'",
        )

    runner = SurgicalTestRunner(root_path=tmp_path)
    with (
        caplog.at_level(logging.WARNING),
        patch(
            "corporate_engineer.quality.surgical_runner.subprocess.run",
            side_effect=fake_run,
        ),
    ):
        changed = runner.collect_changed_files(base_branch="main")

    assert changed == []
    assert len(calls) == 1
    assert calls[0][:2] == ["git", "status"]
    assert "usage:" not in caplog.text.lower()


def test_git_utils_dubious_ownership_handles_cleanly(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """git_utils.is_branch_pushed must detect dubious ownership cleanly on exit 128."""
    from corporate_engineer.git_utils import is_branch_pushed

    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        calls.append(list(cmd))
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=128,
            stdout="",
            stderr="fatal: detected dubious ownership in repository at '/repo'",
        )

    with (
        caplog.at_level(logging.WARNING),
        patch("corporate_engineer.git_utils.subprocess.run", side_effect=fake_run),
    ):
        pushed = is_branch_pushed(repo_path=tmp_path, branch="feat/IMP-0042-test")

    assert pushed is False
    assert len(calls) == 1
    assert "dubious ownership" in caplog.text.lower()
