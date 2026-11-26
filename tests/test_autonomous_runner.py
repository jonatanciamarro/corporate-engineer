"""
Testes unitários e de integração para o Autonomous End-to-End Engineering Runner (IMP-0019 / ADR-019).
Verificação de ciclo de vida completo FSM (PLANNING -> TDD -> IMPLEMENT -> AUDIT -> DELIVER),
geração de checkpoints, DTO contracts e modos de saída da CLI.
"""

from __future__ import annotations

import json
from pathlib import Path

from corporate_engineer.cli import main
from corporate_engineer.models import RunExecutionReport, TaskInput
from corporate_engineer.orchestrator.graph import AutonomousEngineeringGraph


def test_run_execution_report_model() -> None:
    """Valida o contrato DTO RunExecutionReport com Pydantic v2."""
    report = RunExecutionReport(
        ticket_id="CORP-101",
        task_description="Implementar novo endpoint",
        status="SUCCESS",
        final_phase="DELIVER",
        iterations=4,
        checkpoints_created=["cp_1.json", "cp_2.json"],
        refined_plan="Refined plan summary",
        test_files=["tests/test_endpoint.py"],
        code_changes_count=1,
        audit_passed=True,
        duration_seconds=1.23,
        dry_run=True,
    )
    assert report.ticket_id == "CORP-101"
    assert report.status == "SUCCESS"
    assert report.final_phase == "DELIVER"
    assert report.dry_run is True

    # Test serialization / deserialization roundtrip
    dumped = report.model_dump_json()
    loaded = RunExecutionReport.model_validate_json(dumped)
    assert loaded.ticket_id == report.ticket_id
    assert loaded.iterations == report.iterations


def test_graph_run_pipeline_dry_run(tmp_path: Path) -> None:
    """Executa o ciclo de vida completo em modo dry-run em workspace isolado."""
    task = TaskInput(
        ticket_id="CORP-101",
        description="Auditoria de segurança e auto-remediação de AST no repositório",
        workspace_path=str(tmp_path),
        max_iterations=10,
    )
    graph = AutonomousEngineeringGraph(task=task)

    report = graph.run_pipeline(dry_run=True, strict_audit=False)

    assert isinstance(report, RunExecutionReport)
    assert report.ticket_id == "CORP-101"
    assert report.status == "SUCCESS"
    assert report.final_phase == "DELIVER"
    assert report.iterations >= 4
    assert report.audit_passed is True
    assert report.dry_run is True
    assert len(report.checkpoints_created) >= 4

    # Verifica se os checkpoints foram persistidos no disco
    ckpt_dir = tmp_path / ".checkpoints"
    assert ckpt_dir.exists()
    checkpoints = list(ckpt_dir.glob("*.json"))
    assert len(checkpoints) >= 4


def test_graph_run_pipeline_audit_failure_handling(tmp_path: Path) -> None:
    """Verifica contenção quando a auditoria falha: ciclo não avança diretamente para DELIVER."""
    # Cria arquivo com segredo vazado para forçar falha no secret scanner
    bad_file = tmp_path / "leak.py"
    pfx = "AKIA"
    bad_file.write_text(f'AWS_KEY = "{pfx}IOSFODNN7EXAMPLE12"\n', encoding="utf-8")

    task = TaskInput(
        ticket_id="CORP-SEC-01",
        description="Tarefa que introduz segredo indevido",
        workspace_path=str(tmp_path),
        max_iterations=6,
    )
    graph = AutonomousEngineeringGraph(task=task)

    report = graph.run_pipeline(dry_run=True, strict_audit=False)

    assert report.status in ("FAILED", "AUDIT_FAILED")
    assert report.audit_passed is False
    assert report.final_phase != "DELIVER"


def test_cli_run_dry_run_text_output(capsys, tmp_path: Path) -> None:
    """Valida a execução de corporate-engineer run com --dry-run em formato text."""
    ret = main(
        [
            "run",
            "--ticket",
            "CORP-DOGFOOD-01",
            "--task",
            "Dogfooding do ciclo completo corporativo",
            "--workspace",
            str(tmp_path),
            "--dry-run",
        ]
    )
    captured = capsys.readouterr()
    assert ret == 0
    assert "CORP-DOGFOOD-01" in captured.out
    assert "PLANNING" in captured.out
    assert "DELIVER" in captured.out
    assert "SUCCESS" in captured.out
    assert "Checkpoints" in captured.out


def test_cli_run_json_output(capsys, tmp_path: Path) -> None:
    """Valida a execução de corporate-engineer run com --format json."""
    ret = main(
        [
            "run",
            "--ticket",
            "CORP-JSON-02",
            "--task",
            "Execução com saída estruturada JSON",
            "--workspace",
            str(tmp_path),
            "--dry-run",
            "--format",
            "json",
        ]
    )
    captured = capsys.readouterr()
    assert ret == 0
    data = json.loads(captured.out)
    assert data["ticket_id"] == "CORP-JSON-02"
    assert data["status"] == "SUCCESS"
    assert data["final_phase"] == "DELIVER"
    assert len(data["checkpoints_created"]) >= 4


def test_cli_run_markdown_output(capsys, tmp_path: Path) -> None:
    """Valida a execução de corporate-engineer run com --format markdown e exportação."""
    out_file = tmp_path / "dogfood_report.md"
    ret = main(
        [
            "run",
            "--ticket",
            "CORP-MD-03",
            "--task",
            "Execução com relatório Markdown",
            "--workspace",
            str(tmp_path),
            "--dry-run",
            "--format",
            "markdown",
            "--output",
            str(out_file),
        ]
    )
    _ = capsys.readouterr()
    assert ret == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "# Relatório de Execução de Engenharia Autônoma" in content
    assert "CORP-MD-03" in content
    assert "DELIVER" in content


def test_graph_run_pipeline_execution_mode_and_custom_executor(tmp_path: Path) -> None:
    """Verifica execution_mode determinístico por padrão e suporte a code_executor customizado."""
    from corporate_engineer.models import CodeDiff, RevisedPromptSpec

    task_det = TaskInput(
        ticket_id="CORP-EXEC-01",
        description="Implementar validação determinística no orchestrator",
        workspace_path=str(tmp_path),
        max_iterations=10,
    )
    graph_det = AutonomousEngineeringGraph(task=task_det)
    report_det = graph_det.run_pipeline(dry_run=True, strict_audit=False)

    assert report_det.status == "SUCCESS"
    assert report_det.details["execution_mode"] == "deterministic-pipeline"
    assert report_det.code_changes_count >= 1
    assert "determin" in graph_det.state.code_changes[0].explanation.lower()

    captured: list[tuple[str, RevisedPromptSpec]] = []

    def custom_diff_executor(target: str, spec: RevisedPromptSpec) -> list[CodeDiff]:
        captured.append((target, spec))
        return [
            CodeDiff(
                file_path="src/corporate_engineer/custom_feature.py",
                original_content=None,
                new_content="def run_custom() -> str:\n    return 'ok'\n",
                explanation="Custom code executor diff 1",
            ),
            CodeDiff(
                file_path="src/corporate_engineer/custom_helper.py",
                new_content="HELPER_FLAG = True\n",
                explanation="Custom code executor diff 2",
            ),
        ]

    task_custom = TaskInput(
        ticket_id="CORP-EXEC-02",
        description="Executar implementação plugável no orchestrator",
        workspace_path=str(tmp_path),
        max_iterations=10,
    )
    graph_custom = AutonomousEngineeringGraph(task=task_custom)
    report_custom = graph_custom.run_pipeline(
        dry_run=True,
        strict_audit=False,
        code_executor=custom_diff_executor,
    )

    assert report_custom.status == "SUCCESS"
    assert report_custom.details["execution_mode"] == "custom-code-executor"
    assert len(captured) == 1
    assert isinstance(captured[0][1], RevisedPromptSpec)
    assert report_custom.code_changes_count == 2
    assert (
        graph_custom.state.code_changes[0].file_path == "src/corporate_engineer/custom_feature.py"
    )
    assert graph_custom.state.code_changes[1].new_content == "HELPER_FLAG = True\n"

    graph_str = AutonomousEngineeringGraph(
        task=TaskInput(
            ticket_id="CORP-EXEC-03",
            description="Executar executor retornando string",
            workspace_path=str(tmp_path),
            max_iterations=10,
        )
    )
    report_str = graph_str.run_pipeline(
        dry_run=True,
        strict_audit=False,
        code_executor=lambda target, spec: f"# Generated for {target}\nVALUE = 123\n",
    )
    assert report_str.details["execution_mode"] == "custom-code-executor"
    assert report_str.code_changes_count == 1
    assert "VALUE = 123" in graph_str.state.code_changes[0].new_content
