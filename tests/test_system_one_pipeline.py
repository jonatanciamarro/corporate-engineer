"""
Tests for Free System-One SLM Fine-Tuning Pipeline & Universal Framework Injection (IMP-0014).
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from corporate_engineer.git_utils import classify_commit_type
from corporate_engineer.models import (
    ContextPruningReport,
    DatasetExportConfig,
    DatasetReport,
    FailureActionDecision,
    TrainingSample,
)
from corporate_engineer.orchestrator.graph import ExecutionGraph
from corporate_engineer.quality.surgical_runner import SurgicalTestRunner
from corporate_engineer.system_one.dataset import SystemOneDatasetGenerator
from corporate_engineer.system_one.router import SystemOneRouter
from corporate_engineer.system_one.trainer import SystemOneTrainer


def test_training_sample_and_dataset_models() -> None:
    """Verifica modelos Pydantic v2 do dataset de fine-tuning."""
    sample = TrainingSample(
        instruction="Classifique o tipo de commit convencional com base no git diff fornecido.",
        input="diff --git a/src/core.py b/src/core.py\n+def fix_bug(): pass",
        output="fix",
        task_type="classification",
        metadata={"category": "git"},
    )
    assert sample.output == "fix"
    assert sample.task_type == "classification"
    assert sample.metadata["category"] == "git"

    # Falha de validação em campos obrigatórios vazios
    with pytest.raises(ValidationError):
        TrainingSample(instruction="", input="a", output="b", task_type="classification")

    report = DatasetReport(
        total_samples=100,
        task_distribution={"classification": 60, "noul": 40},
        source="corporate-engineer-synthetic",
        export_path="/data/train.jsonl",
        hash_sha256="abc12345def67890",
    )
    assert report.total_samples == 100
    assert report.task_distribution["classification"] == 60

    config = DatasetExportConfig(
        format="jsonl",
        include_metadata=True,
        train_test_split=0.8,
    )
    assert config.format == "jsonl"
    assert config.train_test_split == 0.8

    failure_decision = FailureActionDecision(
        action="retry",
        confidence=0.92,
        target_agent="build-error-resolver",
        rationale="Timeout transitório de conexão detectado.",
    )
    assert failure_decision.action == "retry"
    assert failure_decision.target_agent == "build-error-resolver"

    prune_report = ContextPruningReport(
        original_symbols_count=50,
        pruned_symbols_count=12,
        original_tokens_estimate=3500,
        pruned_tokens_estimate=850,
        savings_percentage=75.7,
        retained_symbols=["HeuristicDecisionEngine", "SystemOneRouter"],
    )
    assert prune_report.savings_percentage == 75.7
    assert len(prune_report.retained_symbols) == 2


def test_dataset_generator_samples(tmp_path: Path) -> None:
    """Verifica a geração sintética de amostras corporativas para fine-tuning."""
    generator = SystemOneDatasetGenerator()

    # Geração de amostras de roteamento de subagentes
    agent_samples = generator.generate_agent_samples(count=16)
    assert len(agent_samples) == 16
    assert any(s.output == "architect" for s in agent_samples)
    assert any(s.output == "tdd-guide" for s in agent_samples)

    # Geração de amostras de risco de diffs
    risk_samples = generator.generate_risk_samples(count=10)
    assert len(risk_samples) == 10
    assert all(s.output in ("True", "False") for s in risk_samples)

    # Geração de amostras de Conventional Commits
    commit_samples = generator.generate_commit_samples(count=12)
    assert len(commit_samples) == 12
    assert any(s.output == "feat" for s in commit_samples)
    assert any(s.output == "fix" for s in commit_samples)

    # Geração de amostras de skipping de nós da DAG
    skip_samples = generator.generate_skip_samples(count=8)
    assert len(skip_samples) == 8

    # Exportação completa
    output_file = tmp_path / "system_one_train.jsonl"
    report = generator.export_dataset(
        output_path=output_file,
        agent_samples=10,
        risk_samples=10,
        commit_samples=10,
        skip_samples=10,
    )

    assert report.total_samples == 40
    assert output_file.exists()
    assert report.hash_sha256 != ""
    assert output_file.stat().st_size > 0


def test_system_one_trainer_recipe(tmp_path: Path) -> None:
    """Verifica a geração de receita de fine-tuning gratuita para Colab e dry-run."""
    trainer = SystemOneTrainer(model_id="Qwen/Qwen2.5-0.5B-Instruct")

    recipe_script = trainer.generate_colab_recipe(
        dataset_path="data/train.jsonl",
        output_dir="models/system_one_lora",
    )
    assert "pip install" in recipe_script
    assert "peft" in recipe_script
    assert "Qwen/Qwen2.5-0.5B-Instruct" in recipe_script
    assert "SFTTrainer" in recipe_script
    assert "onnx" in recipe_script

    # Salva arquivo de receita
    recipe_file = tmp_path / "colab_recipe.py"
    trainer.save_recipe(recipe_file)
    assert recipe_file.exists()
    assert recipe_file.read_text(encoding="utf-8") == recipe_script

    # Execução de dry-run simulado sem GPUs caras
    dry_run_result = trainer.dry_run(samples_count=5)
    assert dry_run_result["status"] == "SUCCESS"
    assert dry_run_result["model_id"] == "Qwen/Qwen2.5-0.5B-Instruct"
    assert "estimated_vram_mb" in dry_run_result


def test_system_one_router_universal_injections() -> None:
    """Verifica novos métodos especializados injetados no SystemOneRouter."""
    router = SystemOneRouter()

    # 1. Classificação de tipo de commit
    commit_feat = router.classify_commit("Adiciona nova funcionalidade de telemetria com spans")
    assert commit_feat.choice == "feat"

    commit_fix = router.classify_commit("Corrige bug de concorrência no cliente MCP")
    assert commit_fix.choice == "fix"

    # 2. Avaliação de descarte de nó da DAG (Skip)
    # Docs alteradas não precisam de auditoria pesada de segurança
    skip_decision = router.should_skip_node(
        node_name="security_scan",
        context="Modificações apenas em arquivos README.md e docs/adr/",
    )
    assert skip_decision.decision is True

    # Mudança no núcleo de auth não deve ser pulada
    no_skip = router.should_skip_node(
        node_name="security_scan",
        context="Modificação em src/corporate_engineer/mcp/client.py alterando Bearer Token auth",
    )
    assert no_skip.decision is False

    # 3. Triagem de falha de nó
    failure_triage = router.triage_failure(
        node_name="pytest_execution",
        error_message="AssertionError: assert 1 == 2 in test_calc",
        traceback_snippet="tests/test_calc.py:15: in test_calc assert 1 == 2",
    )
    assert failure_triage.action in ("dispatch_agent", "retry")
    if failure_triage.action == "dispatch_agent":
        assert failure_triage.target_agent in ("tdd-guide", "build-error-resolver")

    # 4. Poda de contexto semântico (Token Pruning)
    symbols = [
        "HeuristicDecisionEngine",
        "SystemOneRouter",
        "UnrelatedWidgetFactory",
        "LegacyPrinterHelper",
    ]
    pruning = router.prune_context(
        prompt="Preciso de ajuda com a decisão de escolha no HeuristicDecisionEngine",
        symbols=symbols,
    )
    assert "HeuristicDecisionEngine" in pruning.retained_symbols
    assert pruning.savings_percentage > 0


def test_execution_graph_system_one_integration() -> None:
    """Verifica a integração do System One no motor de DAG (ExecutionGraph)."""
    graph = ExecutionGraph()

    # Adiciona nós de exemplo
    graph.add_node("index", lambda: "indexed")
    graph.add_node("security_scan", lambda: "scanned", dependencies=["index"])

    # Teste de should_skip_node nativo no graph
    assert (
        graph.should_skip_node(
            "security_scan",
            context="Apenas alterações na documentação docs/index.md",
        )
        is True
    )

    assert (
        graph.should_skip_node(
            "security_scan",
            context="Alteração crítica em src/corporate_engineer/models.py",
        )
        is False
    )

    # Teste de triage_failure nativo no graph
    triage = graph.triage_failure(
        "security_scan",
        error_message="Connection timed out while fetching CRL",
        traceback_snippet="ConnectionError: timeout",
    )
    assert triage.action in ("retry", "dispatch_agent", "rollback")


def test_surgical_runner_scope_expansion_integration() -> None:
    """Verifica a avaliação de expansão de escopo no SurgicalTestRunner."""
    runner = SurgicalTestRunner()

    # Mudança puramente local/isolada não deve expandir para suíte completa
    low_risk_diff = "diff --git a/docs/README.md b/docs/README.md\n+Texto novo"
    expand_low = runner.evaluate_scope_expansion(
        git_diff=low_risk_diff,
        direct_tests=["tests/test_docs.py"],
    )
    assert expand_low.decision is False

    # Mudança no contrato base deve sugerir expansão para testes de integração
    high_risk_diff = "diff --git a/src/corporate_engineer/models.py b/src/corporate_engineer/models.py\n-class ChoiceDecision\n+class ChoiceDecisionV2"
    expand_high = runner.evaluate_scope_expansion(
        git_diff=high_risk_diff,
        direct_tests=["tests/test_models.py"],
    )
    assert expand_high.decision is True


def test_git_utils_classify_commit_type_integration() -> None:
    """Verifica o classificador de commit nos utilitários Git."""
    feat_diff = "diff --git a/src/feature.py\n+def nova_funcionalidade(): pass"
    decision = classify_commit_type(feat_diff)
    assert decision.choice == "feat"

    test_diff = "diff --git a/tests/test_demo.py\n+def test_something(): assert True"
    test_decision = classify_commit_type(test_diff)
    assert test_decision.choice == "test"


def test_cli_dataset_and_decide_modes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Verifica a execução CLI dos comandos dataset e novos modos de decide."""
    from corporate_engineer.cli import main

    # 1. CLI decide --mode commit
    code = main(["decide", "Adiciona novo endpoint na API", "--mode", "commit"])
    assert code == 0
    captured = capsys.readouterr()
    assert "SYSTEM-ONE COMMIT CLASSIFICATION" in captured.out
    assert "feat" in captured.out

    # 2. CLI decide --mode skip
    code = main(["decide", "security_scan", "--mode", "skip", "--diff", "docs/README.md"])
    assert code == 0
    captured = capsys.readouterr()
    assert "SYSTEM-ONE DAG NODE SKIP EVALUATION" in captured.out
    assert "True" in captured.out

    # 3. CLI dataset generate
    dataset_file = tmp_path / "cli_train.jsonl"
    code = main(
        ["dataset", "generate", "--output", str(dataset_file), "--samples", "2", "--format", "json"]
    )
    assert code == 0
    captured = capsys.readouterr()
    assert '"total_samples": 8' in captured.out
    assert dataset_file.exists()

    # 4. CLI dataset recipe
    recipe_file = tmp_path / "colab_recipe.py"
    code = main(["dataset", "recipe", "--output", str(recipe_file)])
    assert code == 0
    captured = capsys.readouterr()
    assert "SYSTEM-ONE COLAB 1-CLICK RECIPE GERADA" in captured.out
    assert recipe_file.exists()
