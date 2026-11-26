"""
Tests for Gemini LoRA Modular Pipeline for DarkFactory (ADR-020 / IMP-0020).

Covers:
- DTO models: LoraDomain, LoraTrainingSample, LoraDatasetConfig, LoraValidationReport, LoraExportResult
- LoraDatasetGenerator: synthetic samples for Remotion, Manim, Blender, and Tool-Calling (DarkFactory aesthetic)
- LoraSyntaxValidator: AST validation (Python), TS/JSX validation (Remotion), JSON schema (Tool-Calling), batch validation
- LoraVertexExporter: Vertex AI SFT format, secret sanitization, token estimation, train/validation split
- CLI subcommands: corporate-engineer lora generate, validate, export via CliRunner
"""

import contextlib
import io
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from corporate_engineer.cli import main
from corporate_engineer.lora.exporter import LoraVertexExporter
from corporate_engineer.lora.generator import LoraDatasetGenerator
from corporate_engineer.lora.validator import LoraSyntaxValidator
from corporate_engineer.models import (
    LoraDatasetConfig,
    LoraDomain,
    LoraExportResult,
    LoraTrainingSample,
    LoraValidationReport,
)


class CliResult:
    """Encapsulates execution result from CliRunner."""

    def __init__(self, exit_code: int, output: str) -> None:
        self.exit_code = exit_code
        self.output = output


class CliRunner:
    """Lightweight test runner executing corporate-engineer CLI commands."""

    def invoke(self, args: list[str]) -> CliResult:
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()
        with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
            try:
                code = main(args)
            except SystemExit as exc:
                code = exc.code if isinstance(exc.code, int) else 0
            except Exception as exc:  # noqa: BLE001
                output = f"{stdout_buf.getvalue()}\n{stderr_buf.getvalue()}\nException: {exc}"
                return CliResult(1, output)
        output = stdout_buf.getvalue() + stderr_buf.getvalue()
        return CliResult(code, output)


# ==============================================================================
# 1. DTO Model Tests
# ==============================================================================


def test_lora_domain_enum() -> None:
    """Verifies that all 4 required LoRA domains are defined in LoraDomain enum."""
    assert LoraDomain.MOTION_REMOTION.value == "MOTION_REMOTION"
    assert LoraDomain.MOTION_MANIM.value == "MOTION_MANIM"
    assert LoraDomain.MOTION_BLENDER.value == "MOTION_BLENDER"
    assert LoraDomain.TOOL_CALLING.value == "TOOL_CALLING"


def test_lora_training_sample_model() -> None:
    """Verifies instantiation, defaults, and validation of LoraTrainingSample."""
    sample = LoraTrainingSample(
        id="sample-001",
        domain=LoraDomain.MOTION_REMOTION,
        system_instruction="You are a DarkFactory Motion Graphics Architect.",
        user_prompt="Create a cyber-industrial lower third.",
        target_response="export const LowerThird = () => { return <div>DarkFactory</div>; };",
        metadata={"author": "DarkFactory", "tier": "elite"},
    )
    assert sample.id == "sample-001"
    assert sample.domain == LoraDomain.MOTION_REMOTION
    assert sample.is_valid is True
    assert sample.syntax_errors == []
    assert sample.metadata["tier"] == "elite"

    # Pydantic v2 dump
    dump = sample.model_dump()
    assert dump["domain"] == "MOTION_REMOTION"

    # ValidationError on missing required fields
    with pytest.raises(ValidationError):
        LoraTrainingSample.model_validate({"id": "sample-002"})


def test_lora_dataset_config_defaults_and_validation() -> None:
    """Verifies LoraDatasetConfig defaults, constraints, and custom parameters."""
    config = LoraDatasetConfig()
    assert len(config.domains) == 4
    assert LoraDomain.MOTION_REMOTION in config.domains
    assert config.samples_per_domain == 10
    assert config.train_split_ratio == 0.8
    assert config.seed == 42
    assert config.sanitize_secrets is True
    assert config.darkfactory_aesthetic is True

    # Custom configuration
    custom = LoraDatasetConfig(
        domains=[LoraDomain.TOOL_CALLING],
        samples_per_domain=5,
        train_split_ratio=0.75,
        seed=100,
        sanitize_secrets=False,
    )
    assert len(custom.domains) == 1
    assert custom.samples_per_domain == 5
    assert custom.train_split_ratio == 0.75

    # Split ratio must be within (0.0, 1.0)
    with pytest.raises(ValidationError):
        LoraDatasetConfig(train_split_ratio=1.5)


def test_lora_validation_report_model() -> None:
    """Verifies fields and behavior of LoraValidationReport."""
    report = LoraValidationReport(
        total_samples=20,
        valid_samples=18,
        invalid_samples=2,
        domain_breakdown={"MOTION_REMOTION": 10, "MOTION_MANIM": 10},
        errors=["Syntax error in sample-003", "Missing tool parameter in sample-012"],
        is_approved=False,
    )
    assert report.total_samples == 20
    assert report.valid_samples == 18
    assert report.invalid_samples == 2
    assert report.is_approved is False
    assert len(report.errors) == 2


def test_lora_export_result_model() -> None:
    """Verifies fields and serialization of LoraExportResult."""
    result = LoraExportResult(
        train_file="/exports/train.jsonl",
        validation_file="/exports/validation.jsonl",
        train_count=16,
        validation_count=4,
        estimated_tokens=8500,
        success=True,
        sanitized_secrets_count=1,
    )
    assert result.train_count == 16
    assert result.validation_count == 4
    assert result.estimated_tokens == 8500
    assert result.sanitized_secrets_count == 1
    assert result.success is True


# ==============================================================================
# 2. LoraDatasetGenerator Tests
# ==============================================================================


def test_generator_initialization() -> None:
    """Checks generator creation with default and custom configs."""
    gen_default = LoraDatasetGenerator()
    assert gen_default.config.samples_per_domain == 10

    cfg = LoraDatasetConfig(samples_per_domain=3)
    gen_custom = LoraDatasetGenerator(config=cfg)
    assert gen_custom.config.samples_per_domain == 3


def test_generator_remotion_domain() -> None:
    """Verifies that Remotion sample generation produces React/TS motion code with DarkFactory aesthetic."""
    generator = LoraDatasetGenerator()
    sample = generator.generate_sample(LoraDomain.MOTION_REMOTION)

    assert sample.domain == LoraDomain.MOTION_REMOTION
    assert (
        "remotion" in sample.target_response.lower()
        or "usecurrentframe" in sample.target_response.lower()
    )
    # DarkFactory aesthetic check: cyber/industrial keywords or dark theme colors
    assert any(
        color in sample.target_response.lower()
        for color in ["#0a0a0c", "#000", "#111", "0x", "spring", "interpolate"]
    )


def test_generator_manim_domain() -> None:
    """Verifies that Manim sample generation produces valid Scene-based Python animation code."""
    generator = LoraDatasetGenerator()
    sample = generator.generate_sample(LoraDomain.MOTION_MANIM)

    assert sample.domain == LoraDomain.MOTION_MANIM
    assert "scene" in sample.target_response.lower()
    assert "self.play" in sample.target_response
    assert "class " in sample.target_response


def test_generator_blender_domain() -> None:
    """Verifies that Blender sample generation produces bpy-based procedural Python code."""
    generator = LoraDatasetGenerator()
    sample = generator.generate_sample(LoraDomain.MOTION_BLENDER)

    assert sample.domain == LoraDomain.MOTION_BLENDER
    assert "bpy" in sample.target_response
    assert (
        "camera" in sample.target_response.lower() or "material" in sample.target_response.lower()
    )


def test_generator_tool_calling_domain() -> None:
    """Verifies that Tool-Calling sample generation produces structured JSON function calling schemas."""
    generator = LoraDatasetGenerator()
    sample = generator.generate_sample(LoraDomain.TOOL_CALLING)

    assert sample.domain == LoraDomain.TOOL_CALLING
    parsed = json.loads(sample.target_response)
    assert "name" in parsed or "tool" in parsed or "tool_calls" in parsed or "function" in parsed


def test_generator_batch_generation() -> None:
    """Verifies batch generation produces exact total samples across configured domains."""
    cfg = LoraDatasetConfig(
        domains=[LoraDomain.MOTION_REMOTION, LoraDomain.MOTION_MANIM],
        samples_per_domain=3,
        seed=42,
    )
    generator = LoraDatasetGenerator(config=cfg)
    dataset = generator.generate_dataset()

    assert len(dataset) == 6
    remotion_samples = [s for s in dataset if s.domain == LoraDomain.MOTION_REMOTION]
    manim_samples = [s for s in dataset if s.domain == LoraDomain.MOTION_MANIM]
    assert len(remotion_samples) == 3
    assert len(manim_samples) == 3


def test_generator_seed_reproducibility() -> None:
    """Verifies identical seed yields identical synthetic samples."""
    cfg1 = LoraDatasetConfig(samples_per_domain=2, seed=999)
    cfg2 = LoraDatasetConfig(samples_per_domain=2, seed=999)

    ds1 = LoraDatasetGenerator(config=cfg1).generate_dataset()
    ds2 = LoraDatasetGenerator(config=cfg2).generate_dataset()

    assert len(ds1) == len(ds2)
    for s1, s2 in zip(ds1, ds2):
        assert s1.id == s2.id
        assert s1.user_prompt == s2.user_prompt
        assert s1.target_response == s2.target_response


# ==============================================================================
# 3. LoraSyntaxValidator Tests
# ==============================================================================


def test_validator_python_ast_valid() -> None:
    """Checks that valid Python code passes AST validation."""
    validator = LoraSyntaxValidator()
    code = "import bpy\ndef setup_scene():\n    bpy.ops.mesh.primitive_cube_add(size=2.0)\n"
    is_valid, errors = validator.validate_python_ast(code)
    assert is_valid is True
    assert errors == []


def test_validator_python_ast_syntax_error() -> None:
    """Checks that broken Python syntax is flagged as invalid."""
    validator = LoraSyntaxValidator()
    broken_code = "def broken_scene(:\n    pass\n"
    is_valid, errors = validator.validate_python_ast(broken_code)
    assert is_valid is False
    assert len(errors) > 0
    assert "SyntaxError" in errors[0]


def test_validator_remotion_syntax_valid() -> None:
    """Checks that well-formed Remotion TSX code passes validation."""
    validator = LoraSyntaxValidator()
    code = (
        "import { useCurrentFrame, interpolate } from 'remotion';\n"
        "export const MyMotion = () => {\n"
        "    const frame = useCurrentFrame();\n"
        "    const opacity = interpolate(frame, [0, 30], [0, 1]);\n"
        "    return <div style={{ opacity }}>DarkFactory</div>;\n"
        "};"
    )
    is_valid, errors = validator.validate_remotion_syntax(code)
    assert is_valid is True
    assert errors == []


def test_validator_remotion_syntax_invalid() -> None:
    """Checks that malformed TSX (unbalanced brackets / unclosed tags) is detected."""
    validator = LoraSyntaxValidator()
    broken_code = "export const Broken = () => {\n    return <div><span>Unclosed span</div>;\n};"
    is_valid, errors = validator.validate_remotion_syntax(broken_code)
    assert is_valid is False
    assert len(errors) > 0


def test_validator_remotion_syntax_typescript_generics_valid() -> None:
    """IMP-0033: TypeScript generics must not be confused with unclosed JSX tags."""
    validator = LoraSyntaxValidator()
    tsx_with_generics = """
import React, { useState } from 'react';

interface Props {
    title: string;
}

const identity = <T,>(value: T): T => value;
const mergeMeta = <T extends Record<string, unknown>>(obj: T): Promise<Array<string>> => {
    return Promise.resolve(Object.keys(obj));
};

export const DarkFactoryPanel: React.FC<Props> = ({ title }) => {
    const [count, setCount] = useState<number>(0);
    const items: Array<string> = identity<Array<string>>(['a', 'b']);
    const meta: Record<string, unknown> = { count };
    const asyncTask = async (): Promise<void> => {
        await mergeMeta<Record<string, unknown>>(meta);
    };

    return (
        <div style={{ opacity: count > 0 ? 1 : 0 }}>
            <span>{title}</span>
            <button onClick={() => setCount((c) => c + 1)} />
            <List<string> items={items} />
            <img src="hud.png" />
        </div>
    );
};
"""
    is_valid, errors = validator.validate_remotion_syntax(tsx_with_generics)
    assert is_valid is True, f"Unexpected errors: {errors}"
    assert errors == []


def test_validator_remotion_syntax_generics_with_invalid_jsx_still_fails() -> None:
    """IMP-0033: Real unclosed or mismatched JSX tags must still fail when TS generics exist."""
    validator = LoraSyntaxValidator()
    broken_tsx = """
import React, { useState } from 'react';

export const BrokenPanel: React.FC<Props> = () => {
    const [count] = useState<number>(0);
    const items: Array<string> = [];
    return (
        <div>
            <span>{count}
        </div>
    );
};
"""
    is_valid, errors = validator.validate_remotion_syntax(broken_tsx)
    assert is_valid is False
    assert any("Mismatched JSX tag" in err or "Unclosed JSX tag" in err for err in errors)


def test_validator_tool_call_schema_valid() -> None:
    """Checks that valid tool call JSON parses and passes validation."""
    validator = LoraSyntaxValidator()
    payload = json.dumps(
        {
            "name": "render_motion_shot",
            "arguments": {
                "fps": 60,
                "resolution": "4K",
                "theme": "darkfactory",
            },
        }
    )
    is_valid, errors = validator.validate_tool_call_schema(payload)
    assert is_valid is True
    assert errors == []


def test_validator_tool_call_schema_invalid() -> None:
    """Checks that invalid JSON or missing tool attributes are rejected."""
    validator = LoraSyntaxValidator()

    # Malformed JSON
    is_valid, errors = validator.validate_tool_call_schema("{broken json:")
    assert is_valid is False
    assert len(errors) > 0

    # JSON without name/function
    empty_payload = json.dumps({"unknown_field": 123})
    is_valid, errors = validator.validate_tool_call_schema(empty_payload)
    assert is_valid is False
    assert any("tool" in err.lower() or "name" in err.lower() for err in errors)


def test_validator_validate_sample_dispatch() -> None:
    """Verifies validator.validate_sample dispatches by domain and sets sample status."""
    validator = LoraSyntaxValidator()

    sample_good = LoraTrainingSample(
        id="sample-good",
        domain=LoraDomain.MOTION_BLENDER,
        system_instruction="sys",
        user_prompt="Create scene",
        target_response="import bpy\nbpy.ops.object.select_all(action='DESELECT')",
    )
    is_valid, errors = validator.validate_sample(sample_good)
    assert is_valid is True
    assert errors == []

    sample_bad = LoraTrainingSample(
        id="sample-bad",
        domain=LoraDomain.MOTION_BLENDER,
        system_instruction="sys",
        user_prompt="Create scene",
        target_response="import bpy\ndef broken_func(: pass",
    )
    is_valid, errors = validator.validate_sample(sample_bad)
    assert is_valid is False
    assert len(errors) > 0


def test_validator_batch_report() -> None:
    """Verifies validate_batch generates a correct LoraValidationReport."""
    validator = LoraSyntaxValidator()

    samples = [
        LoraTrainingSample(
            id="s1",
            domain=LoraDomain.MOTION_MANIM,
            system_instruction="sys",
            user_prompt="prompt 1",
            target_response="from manim import *\nclass S1(Scene):\n    def construct(self): pass",
        ),
        LoraTrainingSample(
            id="s2",
            domain=LoraDomain.MOTION_MANIM,
            system_instruction="sys",
            user_prompt="prompt 2",
            target_response="broken code (::: syntax error",
        ),
        LoraTrainingSample(
            id="s3",
            domain=LoraDomain.TOOL_CALLING,
            system_instruction="sys",
            user_prompt="call tool",
            target_response=json.dumps({"name": "inspect_asset", "arguments": {"id": "asset-1"}}),
        ),
    ]

    report = validator.validate_batch(samples)
    assert report.total_samples == 3
    assert report.valid_samples == 2
    assert report.invalid_samples == 1
    assert report.is_approved is False
    assert len(report.errors) == 1


# ==============================================================================
# 4. LoraVertexExporter Tests
# ==============================================================================


def test_exporter_format_vertex_entry() -> None:
    """Verifies that format_vertex_entry formats a sample according to Vertex AI JSONL SFT schema."""
    exporter = LoraVertexExporter()
    sample = LoraTrainingSample(
        id="sample-sft-01",
        domain=LoraDomain.MOTION_REMOTION,
        system_instruction="You are a motion expert.",
        user_prompt="Animate glowing logo.",
        target_response="export const Logo = () => <div className='glow'>DarkFactory</div>;",
    )

    entry = exporter.format_vertex_entry(sample)
    assert "contents" in entry
    assert len(entry["contents"]) == 2
    assert entry["contents"][0]["role"] == "user"
    assert entry["contents"][0]["parts"][0]["text"] == "Animate glowing logo."
    assert entry["contents"][1]["role"] == "model"
    assert entry["contents"][1]["parts"][0]["text"] == sample.target_response

    # Verify optional systemInstruction
    if "systemInstruction" in entry:
        assert entry["systemInstruction"]["parts"][0]["text"] == "You are a motion expert."


def test_exporter_token_estimation() -> None:
    """Verifies token estimation heuristic returns positive integer proportional to text length."""
    exporter = LoraVertexExporter()
    text = "DarkFactory high aesthetic motion graphics pipeline for Gemini Flash."
    tokens = exporter.estimate_tokens(text)
    assert tokens > 0
    assert tokens <= len(text)


def test_exporter_secret_sanitization() -> None:
    """Verifies sensitive credentials and keys are scrubbed from exported text."""
    exporter = LoraVertexExporter()

    # Construct dummy secret to avoid static secret scanner false positives
    prefix_aws = "AKIA"
    simulated_key = prefix_aws + "DUMMYKEY1234567890"
    raw_text = f"const config = {{ apiKey: '{simulated_key}', project: 'darkfactory' }};"

    sanitized, count = exporter.sanitize_text(raw_text)
    assert simulated_key not in sanitized
    assert "[REDACTED_SECRET]" in sanitized
    assert count == 1


def test_exporter_redacts_modern_openai_and_anthropic_secrets() -> None:
    """IMP-0034: Ensures modern OpenAI (sk-proj/svcacct/live) and Anthropic keys are redacted."""
    exporter = LoraVertexExporter()

    # Dynamic construction to prevent static secret scanner false positives in test source
    tokens = [
        "sk-" + "proj-" + ("aB3_cD4-eF5_gH6-" * 3),
        "sk-" + "svcacct-" + ("xY9_zW8-uV7_tS6-" * 3),
        "sk-" + "live-" + ("kL2_mN3-pQ4_rS5-" * 3),
        "sk-" + "ant-" + "api03-" + ("mN8_pQ9-rS0_tU1-" * 3),
    ]

    for secret in tokens:
        raw_text = f'{{"api_key": "{secret}", "env": "prod"}}'
        sanitized, count = exporter.sanitize_text(raw_text)
        assert secret not in sanitized, f"Secret was not redacted: {secret[:12]}..."
        assert "[REDACTED_SECRET]" in sanitized
        assert count >= 1


def test_exporter_export_dataset_split(tmp_path: Path) -> None:
    """Verifies export_dataset creates train.jsonl and validation.jsonl with exact split ratio."""
    exporter = LoraVertexExporter()

    # Create 10 dummy samples
    samples = [
        LoraTrainingSample(
            id=f"sample-{i:02d}",
            domain=LoraDomain.MOTION_REMOTION,
            system_instruction="sys",
            user_prompt=f"prompt {i}",
            target_response=f"<div>Motion {i}</div>",
        )
        for i in range(10)
    ]

    config = LoraDatasetConfig(train_split_ratio=0.8, seed=42)
    export_result = exporter.export_dataset(samples, output_dir=tmp_path, config=config)

    assert export_result.success is True
    assert export_result.train_count == 8
    assert export_result.validation_count == 2
    assert export_result.estimated_tokens > 0

    train_path = Path(export_result.train_file)
    val_path = Path(export_result.validation_file)
    assert train_path.exists()
    assert val_path.exists()

    # Verify line count and JSON validity of exported lines
    train_lines = [
        json.loads(line)
        for line in train_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    val_lines = [
        json.loads(line)
        for line in val_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert len(train_lines) == 8
    assert len(val_lines) == 2
    assert "contents" in train_lines[0]


def test_exporter_blocks_or_sanitizes_leaked_secrets_in_export(tmp_path: Path) -> None:
    """Ensures raw secrets are never leaked into exported JSONL files."""
    exporter = LoraVertexExporter()

    prefix_aws = "AKIA"
    simulated_key = prefix_aws + "LEAKEDKEY9876543210"
    sample_with_secret = LoraTrainingSample(
        id="leaked-01",
        domain=LoraDomain.TOOL_CALLING,
        system_instruction="sys",
        user_prompt="Run rendering with secret",
        target_response=f'{{"auth": "{simulated_key}", "action": "render"}}',
    )

    config = LoraDatasetConfig(train_split_ratio=0.5, sanitize_secrets=True)
    export_result = exporter.export_dataset(
        [sample_with_secret], output_dir=tmp_path, config=config
    )

    assert export_result.sanitized_secrets_count >= 1

    train_content = Path(export_result.train_file).read_text(encoding="utf-8")
    val_content = ""
    if Path(export_result.validation_file).exists():
        val_content = Path(export_result.validation_file).read_text(encoding="utf-8")

    all_exported = train_content + val_content
    assert simulated_key not in all_exported
    assert "[REDACTED_SECRET]" in all_exported


# ==============================================================================
# 5. CLI Tests (corporate-engineer lora generate, validate, export via CliRunner)
# ==============================================================================


def test_cli_lora_help() -> None:
    """Verifies corporate-engineer lora --help shows available subcommands."""
    runner = CliRunner()
    result = runner.invoke(["lora", "--help"])
    assert result.exit_code == 0
    assert "generate" in result.output
    assert "validate" in result.output
    assert "export" in result.output


def test_cli_lora_generate(tmp_path: Path) -> None:
    """Verifies corporate-engineer lora generate creates dataset output."""
    output_file = tmp_path / "synthetic_dataset.json"
    runner = CliRunner()
    result = runner.invoke(
        [
            "lora",
            "generate",
            "--domains",
            "MOTION_REMOTION,MOTION_MANIM",
            "--samples",
            "2",
            "--output",
            str(output_file),
        ]
    )

    assert result.exit_code == 0
    assert output_file.exists()
    dataset = json.loads(output_file.read_text(encoding="utf-8"))
    assert len(dataset) == 4


def test_cli_lora_validate(tmp_path: Path) -> None:
    """Verifies corporate-engineer lora validate verifies dataset syntax."""
    dataset_file = tmp_path / "dataset_to_validate.json"
    samples_data = [
        {
            "id": "s1",
            "domain": "MOTION_MANIM",
            "system_instruction": "sys",
            "user_prompt": "prompt 1",
            "target_response": "from manim import *\nclass S(Scene):\n    def construct(self): pass",
            "metadata": {},
            "is_valid": True,
            "syntax_errors": [],
        }
    ]
    dataset_file.write_text(json.dumps(samples_data), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(["lora", "validate", "--input", str(dataset_file)])

    assert result.exit_code == 0
    assert "1" in result.output or "Valid" in result.output or "approved" in result.output.lower()


def test_cli_lora_export(tmp_path: Path) -> None:
    """Verifies corporate-engineer lora export splits dataset into train and validation JSONL files."""
    dataset_file = tmp_path / "dataset_to_export.json"
    samples_data = [
        {
            "id": f"s-{i}",
            "domain": "MOTION_REMOTION",
            "system_instruction": "sys",
            "user_prompt": f"prompt {i}",
            "target_response": f"<div>Motion {i}</div>",
            "metadata": {},
            "is_valid": True,
            "syntax_errors": [],
        }
        for i in range(4)
    ]
    dataset_file.write_text(json.dumps(samples_data), encoding="utf-8")

    export_dir = tmp_path / "vertex_export"
    runner = CliRunner()
    result = runner.invoke(
        [
            "lora",
            "export",
            "--input",
            str(dataset_file),
            "--output-dir",
            str(export_dir),
            "--split",
            "0.75",
        ]
    )

    assert result.exit_code == 0
    assert (export_dir / "train.jsonl").exists()
    assert (export_dir / "validation.jsonl").exists()
