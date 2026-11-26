"""
Testes unitários e de integração para a Trilha 1: Fine-Tuning no Colab & ONNX Runtime Loader (ADR-013).
Validação do notebook interativo, script Colab atualizado e lazy loader com fallback transparente.
"""

import json
from pathlib import Path

import pytest

from corporate_engineer.models import ChoiceDecision, NoulDecision, ScoreDecision
from corporate_engineer.system_one.nli_engine import ONNXNLIDecisionEngine
from corporate_engineer.system_one.trainer import SystemOneTrainer


def test_colab_script_references_real_dataset() -> None:
    """Valida se o script train_system_one_colab.py referencia o dataset corporativo real."""
    script_path = Path("scripts/train_system_one_colab.py")
    assert script_path.exists(), "O script scripts/train_system_one_colab.py deve existir"
    content = script_path.read_text(encoding="utf-8")
    assert "data/system_one_dataset.jsonl" in content, (
        "Script deve referenciar data/system_one_dataset.jsonl"
    )
    assert "SFTTrainer" in content
    assert "model_int8.onnx" in content


def test_system_one_trainer_generate_colab_recipe() -> None:
    """Verifica se o gerador de receita Colab produz o script completo com dataset real e ONNX."""
    trainer = SystemOneTrainer(model_id="Qwen/Qwen2.5-0.5B-Instruct")
    recipe = trainer.generate_colab_recipe()

    assert "data/system_one_dataset.jsonl" in recipe
    assert "Qwen/Qwen2.5-0.5B-Instruct" in recipe
    assert "LoraConfig" in recipe
    assert "model_int8.onnx" in recipe
    assert "Int8" in recipe


def test_system_one_trainer_generate_notebook(tmp_path: Path) -> None:
    """Verifica se o gerador do SystemOneTrainer é capaz de criar o notebook Jupyter válido."""
    trainer = SystemOneTrainer(model_id="Qwen/Qwen2.5-0.5B-Instruct")
    nb_path = tmp_path / "test_colab.ipynb"
    generated_path = trainer.generate_notebook(output_path=nb_path)

    assert generated_path.exists()
    content = json.loads(generated_path.read_text(encoding="utf-8"))
    assert content["nbformat"] >= 4
    assert len(content["cells"]) >= 4
    # Deve conter a badge do Colab
    assert any(
        "colab.research.google.com" in "".join(c.get("source", [])) for c in content["cells"]
    )


def test_notebook_file_exists_and_is_valid() -> None:
    """Garante que notebooks/train_system_one_colab.ipynb existe no projeto e é válido."""
    nb_file = Path("notebooks/train_system_one_colab.ipynb")
    assert nb_file.exists(), "O arquivo notebooks/train_system_one_colab.ipynb deve existir"
    data = json.loads(nb_file.read_text(encoding="utf-8"))
    assert data["nbformat"] >= 4
    assert len(data["cells"]) >= 4


def test_models_directory_and_gitkeep() -> None:
    """Verifica se o diretório models/ e .gitkeep existem no projeto."""
    models_dir = Path("models")
    assert models_dir.exists(), "O diretório models/ deve existir"
    gitkeep = models_dir / ".gitkeep"
    assert gitkeep.exists(), "models/.gitkeep deve existir para versionamento"


def test_onnx_engine_lazy_loading_and_fallback() -> None:
    """Verifica se o ONNXNLIDecisionEngine carrega com segurança e opera com fallback transparente."""
    engine = ONNXNLIDecisionEngine(model_path="models/model_int8.onnx", fallback_to_heuristic=True)
    assert engine.fallback_to_heuristic is True
    # Sem modelo no disco, has_model() deve retornar False
    assert engine.has_model() is False

    # Deve responder a decisões via fallback sem lançar exceções
    choice = engine.decide_choice(
        state="Escreva testes unitários com pytest",
        choices=["tdd-guide", "architect", "code-reviewer"],
    )
    assert isinstance(choice, ChoiceDecision)
    assert choice.choice in ["tdd-guide", "architect", "code-reviewer"]

    noul = engine.decide_noul(
        state="Alteração de documentação no README.md",
        hypothesis="O risco é alto",
    )
    assert isinstance(noul, NoulDecision)
    assert isinstance(noul.decision, bool)

    score = engine.decide_score(
        state="Função simples sem complexidade ciclomática",
        rubric=["complexidade", "cobertura"],
    )
    assert isinstance(score, ScoreDecision)
    assert score.level in ["complexidade", "cobertura"]

    # Relatório completo
    report = engine.evaluate(
        state="Refatoração cirúrgica em módulo",
        questions={"agent": {"type": "choice", "choices": ["tdd-guide", "refactor-cleaner"]}},
    )
    assert report.task == "Refatoração cirúrgica em módulo"
    assert report.engine_name in ["onnx-nli", "heuristic-fallback"]


def test_onnx_engine_strict_mode_without_model(tmp_path: Path) -> None:
    """Verifica se em modo estrito sem fallback e sem modelo/onnxruntime lança FileNotFoundError."""
    missing_path = tmp_path / "non_existent.onnx"
    engine = ONNXNLIDecisionEngine(model_path=missing_path, fallback_to_heuristic=False)
    assert engine.has_model() is False

    with pytest.raises(FileNotFoundError):
        engine.decide_choice(
            state="Teste de falha",
            choices=["a", "b"],
        )


def test_colab_recipe_and_script_use_real_optimum_onnx_export(tmp_path: Path) -> None:
    """Garante exportação e quantização ONNX Int8 real via optimum.onnxruntime sem placeholders."""
    trainer = SystemOneTrainer(model_id="Qwen/Qwen2.5-0.5B-Instruct")
    recipe = trainer.generate_colab_recipe()
    script_content = Path("scripts/train_system_one_colab.py").read_text(encoding="utf-8")

    for content in (recipe, script_content):
        assert "optimum.onnxruntime" in content
        assert "ORTModelForCausalLM" in content
        assert "export=True" in content
        assert "ORTQuantizer" in content
        assert "AutoQuantizationConfig" in content
        assert "merge_and_unload" in content
        assert "model_int8.onnx" in content
        assert "Int8" in content

    nb_recipe_path = trainer.generate_notebook(output_path=tmp_path / "test_nb.ipynb")
    nb_text = nb_recipe_path.read_text(encoding="utf-8")
    assert "|| touch models/model_int8.onnx" not in nb_text
    assert "ORTModelForCausalLM" in nb_text
    assert "ORTQuantizer" in nb_text
