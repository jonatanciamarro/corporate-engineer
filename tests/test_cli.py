"""
Tests for Corporate Autonomous Engineer CLI.
"""

import json

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
    secret_file.write_text('AWS_KEY = "AKIAIOSFODNN7EXAMPLE12"\n', encoding="utf-8")
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
