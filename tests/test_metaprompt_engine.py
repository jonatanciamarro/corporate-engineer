"""
Unit and integration tests for Context-Aware Metaprompt Engine (IMP-0018).
Shift-Left TDD: validates Fast-Path Bypass, domain detection, AST enrichment and CLI.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from corporate_engineer.models import RevisedPromptSpec
from corporate_engineer.prompt.refiner import ContextAwarePromptRefiner


class TestContextAwarePromptRefiner:
    """Test suite for ContextAwarePromptRefiner."""

    def test_operational_fast_path_bypass(self) -> None:
        """Operational commands and brief queries should trigger fast-path bypass."""
        refiner = ContextAwarePromptRefiner()

        operational_prompts = [
            "git status",
            "pytest tests/",
            "/preflight",
            "ruff check .",
            "mypy .",
            "status",
            "ajuda",
        ]

        for p in operational_prompts:
            spec = refiner.refine(p)
            assert isinstance(spec, RevisedPromptSpec)
            assert spec.is_bypassed is True, f"Prompt '{p}' should have been bypassed"
            assert spec.bypass_reason is not None
            assert spec.metaprompt == p
            assert spec.confidence_score == 1.0

    def test_bypass_gate_override(self) -> None:
        """Passing bypass_gate=True should force full refinement even for operational prompts."""
        refiner = ContextAwarePromptRefiner()
        prompt = "pytest tests/ -k test_cli"

        spec = refiner.refine(prompt, bypass_gate=True)
        assert spec.is_bypassed is False
        assert spec.core_intent != ""
        assert len(spec.functional_requirements) > 0
        assert "# Task Specification" in spec.metaprompt

    def test_domain_detection_and_module_mapping(self) -> None:
        """Should detect appropriate domain and affected modules based on prompt keywords."""
        refiner = ContextAwarePromptRefiner()

        cases = [
            ("implementar circuit breaker e pool no MCP Hub", "mcp", "mcp"),
            ("orquestrar nós na DAG em paralelo com rollback", "orchestrator", "orchestrator"),
            ("indexar classes e herança via AST e call graph", "rag", "rag"),
            (
                "executar benchmark de latência P95 e throughput no Sistema 1",
                "system_one",
                "system_one",
            ),
            ("limpeza segura de armazenamento e secret scanner", "quality", "quality"),
            ("adicionar novo subcomando e flags na CLI corporativa", "cli", "cli/"),
        ]

        for prompt_text, expected_domain, expected_module_substr in cases:
            spec = refiner.refine(prompt_text)
            assert spec.target_domain == expected_domain, f"Failed domain for: {prompt_text}"
            assert any(expected_module_substr in m for m in spec.affected_modules), (
                f"Expected '{expected_module_substr}' in modules: {spec.affected_modules}"
            )

    def test_full_refinement_structure(self) -> None:
        """Complex engineering prompt should generate complete structured specification."""
        refiner = ContextAwarePromptRefiner()
        prompt = (
            "Adicionar timeout exponencial e isolamento de falhas nas chamadas remotas de MCP SSE"
        )

        spec = refiner.refine(prompt)

        assert spec.is_bypassed is False
        assert spec.target_domain == "mcp"
        assert len(spec.functional_requirements) >= 2
        assert len(spec.non_functional_requirements) >= 3
        assert len(spec.out_of_scope) >= 1
        assert len(spec.tdd_test_scenarios) >= 2
        assert spec.confidence_score >= 0.70
        assert spec.timestamp != ""

        # Validate Markdown sections
        assert "# Task Specification" in spec.metaprompt
        assert "## Raw Request" in spec.metaprompt
        assert "## Target Architecture & Modules" in spec.metaprompt
        assert "## Functional Requirements" in spec.metaprompt
        assert "## Corporate Non-Functional Requirements" in spec.metaprompt
        assert "## Scope Guardrails" in spec.metaprompt
        assert "## TDD Verification Scenarios" in spec.metaprompt

    def test_ast_symbol_enrichment(self, tmp_path: Path) -> None:
        """Refiner should identify referenced codebase symbols when available."""
        # Create a mock source file
        src_dir = tmp_path / "src" / "corporate_engineer" / "mcp"
        src_dir.mkdir(parents=True)
        py_file = src_dir / "hub.py"
        py_file.write_text("class MCPEnterpriseHub:\n    pass\n", encoding="utf-8")

        refiner = ContextAwarePromptRefiner(workspace_path=tmp_path)
        prompt = "Adicionar suporte a circuit breaker na classe MCPEnterpriseHub"

        spec = refiner.refine(prompt)
        assert spec.is_bypassed is False
        assert "MCPEnterpriseHub" in spec.metaprompt or any(
            "hub.py" in m for m in spec.affected_modules
        )

    def test_format_helpers(self) -> None:
        """Prompt refiner and RevisedPromptSpec should support formatting utilities."""
        refiner = ContextAwarePromptRefiner()
        spec = refiner.refine("Adicionar novo filtro no quality gate")

        text_output = refiner.format_output(spec, format_type="text")
        json_output = refiner.format_output(spec, format_type="json")
        md_output = refiner.format_output(spec, format_type="markdown")

        assert "Target Domain:" in text_output
        assert "raw_prompt" in json_output
        parsed = json.loads(json_output)
        assert parsed["target_domain"] == "quality"
        assert "# Task Specification" in md_output


class TestPromptRefinerCLI:
    """Test CLI integration for prompt refine command."""

    def test_cli_prompt_refine_markdown(self, capsys: pytest.CaptureFixture[str]) -> None:
        from corporate_engineer.cli import handle_prompt

        args = MagicMock()
        args.prompt_subcommand = "refine"
        args.prompt = "adicionar novas regras de qualidade no gate"
        args.bypass_gate = False
        args.format = "markdown"
        args.workspace = "."
        args.output = None

        exit_code = handle_prompt(args)
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "# Task Specification" in captured.out

    def test_cli_prompt_refine_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        from corporate_engineer.cli import handle_prompt

        args = MagicMock()
        args.prompt_subcommand = "refine"
        args.prompt = "git status"
        args.bypass_gate = False
        args.format = "json"
        args.workspace = "."
        args.output = None

        exit_code = handle_prompt(args)
        assert exit_code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["is_bypassed"] is True

    def test_cli_prompt_refine_file_output(self, tmp_path: Path) -> None:
        from corporate_engineer.cli import handle_prompt

        out_file = tmp_path / "refined_spec.md"
        args = MagicMock()
        args.prompt_subcommand = "refine"
        args.prompt = "refatorar o parser AST para suportar type aliases"
        args.bypass_gate = False
        args.format = "markdown"
        args.workspace = "."
        args.output = str(out_file)

        exit_code = handle_prompt(args)
        assert exit_code == 0
        assert out_file.exists()
        content = out_file.read_text(encoding="utf-8")
        assert "# Task Specification" in content
