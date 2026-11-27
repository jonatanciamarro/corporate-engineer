"""
Shift-Left TDD tests for Wave P3 (ADR-035):
- IMP-0040: Strict immutability (ConfigDict(frozen=True)) on Pydantic v2 DTOs
- IMP-0041: Curated .agents/skills/ (DAILY) vs .agents/skills-library/ (LIBRARY)
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import BaseModel, ValidationError

import corporate_engineer.models as models_mod
from corporate_engineer.lora.validator import LoraSyntaxValidator
from corporate_engineer.models import (
    AgentSpan,
    AgentState,
    EvaluationAxisScore,
    LoraDomain,
    LoraTrainingSample,
    SemanticEvaluationReport,
    SwarmGoalReport,
    SwarmMember,
    SystemOneReport,
    TaskInput,
)
from corporate_engineer.orchestrator.graph import AutonomousEngineeringGraph
from corporate_engineer.orchestrator.swarm import SwarmCoordinator
from corporate_engineer.system_one.router import SystemOneRouter

REPO_ROOT = Path(__file__).resolve().parents[1]

MUTABLE_RUNTIME_HANDLES = frozenset({"SwarmMember", "AgentSpan"})

CURATED_DAILY_SKILLS = frozenset(
    {
        "agent-sort",
        "agentic-engineering",
        "api-design",
        "architecture-decision-records",
        "content-hash-cache-pattern",
        "conventional-commit-review",
        "corp-pipeline",
        "ecc-guide",
        "grill-me_v2",
        "mcp-server-patterns",
        "orch-add-feature",
        "orch-change-feature",
        "orch-fix-defect",
        "orch-refine-code",
        "plan_v2",
        "python-patterns",
        "python-testing",
        "security-review",
        "security-scan",
        "tdd-workflow",
        "verification-loop",
    }
)


def test_imp0040_all_contract_and_report_dtos_are_frozen() -> None:
    """All contract, state, and report DTOs in models.py must configure frozen=True."""
    dto_classes = [
        (name, obj)
        for name, obj in vars(models_mod).items()
        if isinstance(obj, type)
        and issubclass(obj, BaseModel)
        and obj is not BaseModel
        and name not in MUTABLE_RUNTIME_HANDLES
    ]
    assert len(dto_classes) >= 50
    unfrozen = [name for name, cls in dto_classes if cls.model_config.get("frozen") is not True]
    assert unfrozen == [], f"Expected all DTOs to be frozen=True, unfrozen: {unfrozen}"
    # Confirm intentional runtime handle design remains explicit
    assert SwarmMember.model_config.get("frozen") is not True
    assert AgentSpan.model_config.get("frozen") is not True


def test_imp0040_frozen_dtos_reject_in_place_mutation_and_support_model_copy() -> None:
    """Direct attribute reassignment must fail with ValidationError; model_copy must work."""
    task = TaskInput(
        ticket_id="IMP-0040",
        description="Enforce strict DTO immutability",
        workspace_path=".",
    )
    with pytest.raises(ValidationError):
        task.ticket_id = "MUTATED"  # type: ignore[misc]

    copied_task = task.model_copy(update={"ticket_id": "IMP-0040-V2"})
    assert copied_task.ticket_id == "IMP-0040-V2"
    assert task.ticket_id == "IMP-0040"

    state = AgentState(task=task)
    with pytest.raises(ValidationError):
        state.phase = "DELIVER"  # type: ignore[misc]

    report = SwarmGoalReport(goal="g", swarm_name="s")
    with pytest.raises(ValidationError):
        report.aggregated_consensus = "APPROVED"  # type: ignore[misc]


def test_imp0040_semantic_evaluation_report_computes_scores_when_frozen() -> None:
    """SemanticEvaluationReport.model_post_init must populate derived metrics while frozen."""
    axes = [
        EvaluationAxisScore(axis_name="Immutability", score=100.0, weight=0.5, violations=[]),
        EvaluationAxisScore(
            axis_name="Typing", score=80.0, weight=0.5, violations=["missing annotation"]
        ),
    ]
    eval_report = SemanticEvaluationReport(
        target_path="src",
        axes=axes,
        total_files_evaluated=2,
        total_functions_evaluated=4,
    )
    assert eval_report.composite_score == 90.0
    assert eval_report.letter_grade == "A"
    assert eval_report.total_violations == 1
    assert eval_report.passed_gate is True
    with pytest.raises(ValidationError):
        eval_report.composite_score = 10.0  # type: ignore[misc]


def test_imp0040_graph_router_swarm_and_validator_preserve_immutability(tmp_path: Path) -> None:
    """Consumers (graph, router, swarm, lora validator) must operate on frozen DTOs."""
    task = TaskInput(ticket_id="P3-01", description="Test FSM", workspace_path=str(tmp_path))
    graph = AutonomousEngineeringGraph(task=task)
    initial_state = graph.state
    next_state = graph.step_plan("Plan text")
    assert next_state is not initial_state
    assert initial_state.phase == "PLANNING"
    assert next_state.phase == "TDD"

    router = SystemOneRouter()
    sys_report = router.triage_quality_gate(prompt="Audit security tokens", diff="")
    assert isinstance(sys_report, SystemOneReport)
    assert sys_report.suggested_agent is not None
    with pytest.raises(ValidationError):
        sys_report.risk_level = "CRITICAL"  # type: ignore[misc]

    swarm = SwarmCoordinator(workspace_path=tmp_path)
    consensus = swarm.run_consensus(
        target_description="P3 immutability check",
        reviewer_roles=["architect", "code-reviewer"],
    )
    assert isinstance(consensus, SwarmGoalReport)
    assert "APPROVED" in consensus.aggregated_consensus
    with pytest.raises(ValidationError):
        consensus.aggregated_consensus = "TAMPERED"  # type: ignore[misc]

    validator = LoraSyntaxValidator()
    sample = LoraTrainingSample(
        id="s-01",
        domain=LoraDomain.MOTION_BLENDER,
        user_prompt="Create cube",
        target_response="def broken(:",
    )
    is_valid, errs = validator.validate_sample(sample)
    assert is_valid is False
    assert len(errs) >= 1
    # Sample itself was not mutated in-place; validate_sample_model returns frozen copy
    validated_sample = validator.validate_sample_model(sample)
    assert validated_sample.is_valid is False
    assert len(validated_sample.syntax_errors) >= 1
    assert sample.is_valid is True


def test_imp0041_skills_directory_curated_to_daily_core_only() -> None:
    """Active .agents/skills/ must only retain curated DAILY skills, moving bloat to library."""
    skills_dir = REPO_ROOT / ".agents" / "skills"
    library_dir = REPO_ROOT / ".agents" / "skills-library"

    active_skills = {d.name for d in skills_dir.iterdir() if d.is_dir()}
    assert active_skills == CURATED_DAILY_SKILLS

    # Critical corp-pipeline scripts remain intact
    assert (skills_dir / "corp-pipeline" / "scripts" / "secret_scanner.py").is_file()
    assert (skills_dir / "corp-pipeline" / "scripts" / "stack_detector.py").is_file()

    # Off-stack skills were relocated to skills-library (not deleted)
    assert library_dir.is_dir()
    library_skills = {d.name for d in library_dir.iterdir() if d.is_dir()}
    for off_stack in (
        "perl-patterns",
        "yoruba-localization-testing",
        "cisco-ios-patterns",
        "laravel-patterns",
        "swiftui-patterns",
    ):
        assert off_stack not in active_skills
        assert (library_dir / off_stack / "SKILL.md").is_file()
    assert len(active_skills) + len(library_skills) == 331


def test_imp0041_skills_registry_and_install_state_synchronized() -> None:
    """skills-registry.md and ecc-install-state.json must reflect the curated DAILY/LIBRARY split."""
    install_state = json.loads(
        (REPO_ROOT / ".agents" / "ecc-install-state.json").read_text(encoding="utf-8")
    )
    daily_list = install_state["components"]["daily_skills"]
    assert set(daily_list) == CURATED_DAILY_SKILLS
    assert install_state["components"]["library_skills_count"] == 310

    registry_text = (REPO_ROOT / ".agents" / "orchestration" / "skills-registry.md").read_text(
        encoding="utf-8"
    )
    assert ".agents/skills-library/" in registry_text
    assert "310" in registry_text
