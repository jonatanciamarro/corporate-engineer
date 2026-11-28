"""
Tests for Corporate Autonomous Engineer CLI.
"""

import json
from pathlib import Path

import pytest

from corporate_engineer.cli import main


def test_cli_no_args(capsys):
    ret = main([])
    captured = capsys.readouterr()
    assert ret == 0
    assert (
        "usage:" in captured.out or "usage:" in captured.err or "corporate-engineer" in captured.out
    )


def test_cli_help(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "Autonomous Corporate Software Engineer" in captured.out


def test_cli_run(capsys, tmp_path):
    ret = main(
        [
            "run",
            "--ticket",
            "CORP-999",
            "--task",
            "Test task execution",
            "--workspace",
            str(tmp_path),
            "--dry-run",
        ]
    )
    captured = capsys.readouterr()
    assert ret == 0
    assert "CORP-999" in captured.out
    assert "Test task execution" in captured.out
    assert "PLANNING" in captured.out


def test_cli_audit_clean_text(capsys, tmp_path):
    (tmp_path / "hello.py").write_text("print('hello')", encoding="utf-8")
    ret = main(["audit", "--path", str(tmp_path)])
    captured = capsys.readouterr()
    assert ret == 0
    assert "PASS" in captured.out


def test_cli_audit_clean_json(capsys, tmp_path):
    (tmp_path / "hello.py").write_text("print('hello')", encoding="utf-8")
    ret = main(["audit", "--path", str(tmp_path), "--format", "json"])
    captured = capsys.readouterr()
    assert ret == 0
    data = json.loads(captured.out)
    assert data["passed"] is True
    assert data["secret_scan"]["passed"] is True
    assert data["findings"] == []


def test_cli_audit_with_secret_failure(capsys, tmp_path):
    secret_file = tmp_path / "leaked.py"
    prefix = "AKIA"
    secret_file.write_text(f'AWS_KEY = "{prefix}IOSFODNN7EXAMPLE12"\n', encoding="utf-8")
    ret = main(["audit", "--path", str(tmp_path)])
    captured = capsys.readouterr()
    assert ret == 1
    assert "Segredos encontrados" in captured.out or "findings" in captured.out


def test_cli_audit_strict_mode(capsys, tmp_path, monkeypatch):
    (tmp_path / "sample.py").write_text("def add(a, b): return a + b\n", encoding="utf-8")
    ret = main(["audit", "--path", str(tmp_path), "--strict"])
    captured = capsys.readouterr()
    # In strict mode, runs secret scan and pytest verification
    assert ret in (0, 1)
    assert "Secret Scan PASS" in captured.out or "Strict" in captured.out


def test_cli_index_text(capsys, tmp_path):
    code = "class Calculator:\n    def add(self, a, b):\n        return a + b\n"
    (tmp_path / "calc.py").write_text(code, encoding="utf-8")
    ret = main(["index", "--path", str(tmp_path)])
    captured = capsys.readouterr()
    assert ret == 0
    assert "Codebase Outline" in captured.out
    assert "Calculator" in captured.out
    assert "add" in captured.out


def test_cli_index_json(capsys, tmp_path):
    code = "class Greeter:\n    def greet(self, name):\n        return f'Hello {name}'\n"
    (tmp_path / "greeter.py").write_text(code, encoding="utf-8")
    ret = main(["index", "--path", str(tmp_path), "--format", "json"])
    captured = capsys.readouterr()
    assert ret == 0
    data = json.loads(captured.out)
    assert "files" in data
    assert any("greeter.py" in f["file"] for f in data["files"])


def test_cli_index_output_file(capsys, tmp_path):
    code = "def standalone_func(): pass\n"
    (tmp_path / "mod.py").write_text(code, encoding="utf-8")
    out_file = tmp_path / "ast_output.txt"
    ret = main(["index", "--path", str(tmp_path), "--output", str(out_file)])
    assert ret == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "standalone_func" in content


def test_cli_dag_phases(capsys):
    ret = main(["dag", "--show-phases"])
    captured = capsys.readouterr()
    assert ret == 0
    assert "PLANNING" in captured.out
    assert "TDD" in captured.out
    assert "IMPLEMENT" in captured.out
    assert "AUDIT" in captured.out
    assert "DELIVER" in captured.out


def test_cli_dag_phases_json(capsys):
    ret = main(["dag", "--show-phases", "--format", "json"])
    captured = capsys.readouterr()
    assert ret == 0
    data = json.loads(captured.out)
    assert "phases" in data
    assert "PLANNING" in data["phases"]
    assert "DELIVER" in data["phases"]


def test_cli_mcp_ping_local(capsys, tmp_path):
    ret = main(["mcp", "ping", "--server", "local", "--workspace", str(tmp_path)])
    captured = capsys.readouterr()
    assert ret == 0
    assert "ok" in captured.out.lower()


def test_cli_mcp_list_tools_json(capsys, tmp_path):
    ret = main(
        [
            "mcp",
            "list-tools",
            "--server",
            "local",
            "--workspace",
            str(tmp_path),
            "--format",
            "json",
        ]
    )
    captured = capsys.readouterr()
    assert ret == 0
    data = json.loads(captured.out)
    assert "tools" in data
    tool_names = [t["name"] for t in data["tools"]]
    assert "read_file" in tool_names
    assert "write_file" in tool_names


def test_cli_mcp_call_local(capsys, tmp_path):
    args_json = json.dumps({"path": "created_by_cli.txt", "content": "MCP CLI rocks"})
    ret = main(
        [
            "mcp",
            "call",
            "--server",
            "local",
            "--tool",
            "write_file",
            "--args",
            args_json,
            "--workspace",
            str(tmp_path),
        ]
    )
    capsys.readouterr()
    assert ret == 0
    assert (tmp_path / "created_by_cli.txt").exists()
    assert (tmp_path / "created_by_cli.txt").read_text(encoding="utf-8") == "MCP CLI rocks"


def test_cli_dag_checkpoints(capsys, tmp_path: Path):
    from corporate_engineer.models import TaskInput
    from corporate_engineer.orchestrator.graph import AutonomousEngineeringGraph

    task = TaskInput(
        ticket_id="CORP-CLI-CP",
        description="CLI Checkpoint listing",
        workspace_path=str(tmp_path),
    )
    graph = AutonomousEngineeringGraph(task=task)
    graph.step_plan("Plan 1")
    graph.save_checkpoint()

    # Text format
    ret = main(["dag", "--checkpoints", "--workspace", str(tmp_path)])
    out = capsys.readouterr().out
    assert ret == 0
    assert "CORP-CLI-CP" in out

    # JSON format
    ret = main(["dag", "--checkpoints", "--workspace", str(tmp_path), "--format", "json"])
    out = capsys.readouterr().out
    assert ret == 0
    data = json.loads(out)
    assert "checkpoints" in data
    assert any(c["ticket_id"] == "CORP-CLI-CP" for c in data["checkpoints"])


def test_cli_dag_mermaid(capsys):
    ret = main(["dag", "--mermaid"])
    captured = capsys.readouterr()
    assert ret == 0
    assert "flowchart TD" in captured.out
    assert "PLANNING" in captured.out
    assert "DELIVER" in captured.out


def test_cli_dag_mermaid_output_file(capsys, tmp_path):
    out_file = tmp_path / "diagram.mmd"
    ret = main(["dag", "--mermaid", "--output", str(out_file)])
    captured = capsys.readouterr()
    assert ret == 0
    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "flowchart TD" in content
    assert "Salvo com sucesso" in captured.out or "salvo com sucesso" in captured.out.lower()


def test_cli_dag_checkpoints_mermaid(capsys, tmp_path):
    from corporate_engineer.models import TaskInput
    from corporate_engineer.orchestrator.graph import AutonomousEngineeringGraph

    task = TaskInput(
        ticket_id="CORP-CLI-MMD",
        description="CLI Checkpoints Mermaid test",
        workspace_path=str(tmp_path),
    )
    graph = AutonomousEngineeringGraph(task=task)
    graph.step_plan("Plan mermaid")
    graph.save_checkpoint()

    ret = main(["dag", "--checkpoints", "--mermaid", "--workspace", str(tmp_path)])
    captured = capsys.readouterr()
    assert ret == 0
    assert "flowchart LR" in captured.out
    assert "CORP-CLI-MMD" in captured.out


def test_cli_decide_route_text(capsys):
    ret = main(["decide", "Escrever suíte de testes TDD com pytest", "--mode", "route"])
    captured = capsys.readouterr()
    assert ret == 0
    assert "tdd-guide" in captured.out
    assert "SYSTEM-ONE AGENT ROUTING" in captured.out


def test_cli_decide_route_json(capsys):
    ret = main(
        [
            "decide",
            "Criar arquitetura e ADR para nova feature",
            "--mode",
            "route",
            "--format",
            "json",
        ]
    )
    captured = capsys.readouterr()
    assert ret == 0
    data = json.loads(captured.out)
    assert data["choice"] == "architect"
    assert "confidence" in data


def test_cli_decide_risk(capsys):
    ret = main(["decide", "Refatoração crítica do módulo de segurança e secrets", "--mode", "risk"])
    captured = capsys.readouterr()
    assert ret == 0
    assert "SYSTEM-ONE RISK ASSESSMENT" in captured.out
    assert "HIGH RISK" in captured.out


def test_cli_decide_triage_output_file(capsys, tmp_path):
    out_file = tmp_path / "triage.json"
    ret = main(
        [
            "decide",
            "Planejamento de testes e revisão de qualidade",
            "--mode",
            "triage",
            "--format",
            "json",
            "--output",
            str(out_file),
        ]
    )
    captured = capsys.readouterr()
    assert ret == 0
    assert out_file.exists()
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert "task" in data
    assert "risk_level" in data
    assert "Relatório salvo" in captured.out


def test_cli_eval_missing_path_text(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist"
    ret = main(["eval", str(missing)])
    captured = capsys.readouterr()
    assert ret == 1
    assert captured.err.strip() != ""


def test_cli_eval_missing_path_json(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.py"
    ret = main(["eval", str(missing), "--format", "json"])
    captured = capsys.readouterr()
    assert ret == 1
    data = json.loads(captured.out)
    assert "error" in data
    assert data.get("passed_gate") is False


def test_cli_mcp_no_subcommand(capsys: pytest.CaptureFixture[str]) -> None:
    ret = main(["mcp"])
    captured = capsys.readouterr()
    assert ret != 0
    assert "usage:" in captured.err.lower()


def test_cli_prompt_refine_json_output_pure_stdout(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    out_file = tmp_path / "refined.json"
    ret = main(
        [
            "prompt",
            "refine",
            "Implementar endpoint seguro",
            "--format",
            "json",
            "--workspace",
            str(tmp_path),
            "--output",
            str(out_file),
        ]
    )
    captured = capsys.readouterr()
    assert ret == 0
    assert out_file.exists()
    stdout_data = json.loads(captured.out)
    file_data = json.loads(out_file.read_text(encoding="utf-8"))
    assert stdout_data == file_data
    assert str(out_file) in captured.err


def test_cli_index_json_output_pure_stdout(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    (tmp_path / "mod.py").write_text("def foo() -> int:\n    return 1\n", encoding="utf-8")
    out_file = tmp_path / "index.json"
    ret = main(["index", "--path", str(tmp_path), "--format", "json", "--output", str(out_file)])
    captured = capsys.readouterr()
    assert ret == 0
    assert out_file.exists()
    assert captured.out.strip() == ""
    assert str(out_file.resolve()) in captured.err


def test_cli_blast_radius_json_output_pure_stdout(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    (tmp_path / "mod.py").write_text("def bar() -> int:\n    return 2\n", encoding="utf-8")
    out_file = tmp_path / "blast.json"
    ret = main(
        [
            "blast-radius",
            "bar",
            "--workspace",
            str(tmp_path),
            "--format",
            "json",
            "--output",
            str(out_file),
        ]
    )
    captured = capsys.readouterr()
    assert ret == 0
    assert out_file.exists()
    assert captured.out.strip() == ""
    assert str(out_file.resolve()) in captured.err
