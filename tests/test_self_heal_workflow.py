"""
Testes unitários e de integração para o GitHub Actions Self-Healing Workflow (IMP-0017 / ADR-017).
Validação de sintaxe YAML, gatilhos de Pull Request, passos de remediação e integração com CLI.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml


def test_self_heal_workflow_file_exists() -> None:
    """Verifica se o arquivo de workflow .github/workflows/self-heal.yml existe."""
    workflow_path = Path(".github/workflows/self-heal.yml")
    assert workflow_path.exists(), "O workflow .github/workflows/self-heal.yml deve existir"


def test_self_heal_workflow_yaml_syntax() -> None:
    """Verifica se a estrutura YAML do workflow é estritamente válida e possui chaves obrigatórias."""
    workflow_path = Path(".github/workflows/self-heal.yml")
    content = workflow_path.read_text(encoding="utf-8")
    data = yaml.safe_load(content)

    assert isinstance(data, dict), "O workflow deve ser um dicionário YAML válido"
    assert "name" in data
    assert "on" in data or True in data
    assert "jobs" in data


def test_self_heal_workflow_triggers() -> None:
    """Valida se o workflow é acionado exclusivamente em eventos de Pull Request."""
    workflow_path = Path(".github/workflows/self-heal.yml")
    data = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))

    triggers = data.get("on") or data.get(True) or {}
    assert "pull_request" in triggers, "O workflow deve ser disparado em pull_request"
    pr_config = triggers["pull_request"]
    if isinstance(pr_config, dict) and "types" in pr_config:
        types = pr_config["types"]
        assert any(t in types for t in ["opened", "synchronize", "reopened"])


def test_self_heal_workflow_job_structure() -> None:
    """Valida se o job possui passos essenciais de auto-cura e proteção contra loop de commits."""
    workflow_path = Path(".github/workflows/self-heal.yml")
    content = workflow_path.read_text(encoding="utf-8")
    data = yaml.safe_load(content)

    jobs = data.get("jobs", {})
    assert len(jobs) > 0, "Deve haver pelo menos um job configurado"

    job = next(iter(jobs.values()))
    steps = job.get("steps", [])
    step_runs = [s.get("run", "") for s in steps]
    combined_runs = " ".join(step_runs)

    # Verificações de passos fundamentais
    assert any("checkout" in str(s.get("uses", "")).lower() for s in steps), "Deve ter checkout"
    assert any("setup-python" in str(s.get("uses", "")).lower() for s in steps), (
        "Deve configurar Python"
    )
    assert (
        "corporate-engineer fix --auto" in combined_runs
        or "python -m corporate_engineer.cli fix" in combined_runs
    ), "Deve conter passo de auto-cura (corporate-engineer fix --auto)"
    assert "[skip ci]" in combined_runs or "github-actions" in combined_runs, (
        "Deve conter mensagem de commit preventiva ou identidade do bot para evitar loops de CI"
    )


def test_self_healing_cli_integration(tmp_path: Path) -> None:
    """Verifica a auto-cura na prática: arquivo degradado é curado por corporate-engineer fix."""
    bad_code = "class Order:\n    def __init__(self, items=[]):\n        pass\n"
    test_file = tmp_path / "order_service.py"
    test_file.write_text(bad_code, encoding="utf-8")

    # Executa o fix --auto sobre o arquivo temporário
    cmd = [
        sys.executable,
        "-m",
        "corporate_engineer.cli",
        "fix",
        "--path",
        str(test_file),
        "--auto",
        "--format",
        "json",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert result.returncode == 0, f"Falha na CLI fix: {result.stderr}"

    report = json.loads(result.stdout)
    assert report["files_modified"] >= 1
    assert len(report["fixes_applied"]) >= 1

    # Conteúdo curado
    fixed_code = test_file.read_text(encoding="utf-8")
    assert "-> None" in fixed_code
    assert "items=None" in fixed_code
    assert "pass" not in fixed_code
