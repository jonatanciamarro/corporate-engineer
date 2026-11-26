"""
Tests for Open-Source System-One Decision Engine (IMP-0013).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from corporate_engineer.models import (
    ChoiceDecision,
    NoulDecision,
    ScoreDecision,
    SystemOneReport,
)
from corporate_engineer.system_one.heuristic_engine import HeuristicDecisionEngine
from corporate_engineer.system_one.nli_engine import ONNXNLIDecisionEngine
from corporate_engineer.system_one.outlines_engine import OutlinesDecisionEngine
from corporate_engineer.system_one.router import SystemOneRouter


def test_system_one_models_validation() -> None:
    """Verifica contratos Pydantic v2 de decisões System One."""
    choice = ChoiceDecision(
        choice="architect",
        confidence=0.95,
        probabilities={"architect": 0.95, "tdd-guide": 0.05},
        rationale="Design and architecture keywords detected",
    )
    assert choice.choice == "architect"
    assert choice.confidence == 0.95

    # Teste de validação de limites de confiança [0.0, 1.0]
    with pytest.raises(ValidationError):
        ChoiceDecision(choice="invalid", confidence=1.5)

    with pytest.raises(ValidationError):
        ChoiceDecision(choice="invalid", confidence=-0.1)

    noul = NoulDecision(decision=True, probability=0.88, rationale="High risk identified")
    assert noul.decision is True
    assert noul.probability == 0.88

    score = ScoreDecision(score=2, level="High", confidence=0.85)
    assert score.score == 2
    assert score.level == "High"

    report = SystemOneReport(
        task="Evaluate security risk of change",
        engine_name="heuristic",
        duration_ms=4.2,
        choices={"agent": choice},
        nouls={"requires_full_suite": noul},
        scores={"risk_level": score},
        suggested_agent="security-reviewer",
        risk_level="HIGH",
        requires_human_approval=True,
    )
    assert report.risk_level == "HIGH"
    assert report.requires_human_approval is True
    assert "agent" in report.choices


def test_heuristic_engine_decide_choice() -> None:
    """Verifica decisão de escolha do motor heurístico."""
    engine = HeuristicDecisionEngine()
    choices = {
        "architect": "Design de arquitetura, contratos DTO e ADRs",
        "tdd-guide": "Criação de testes TDD, pytest e cobertura",
        "security-reviewer": "Auditoria de segurança, senhas, tokens e OWASP",
    }

    # Deve rotear para architect
    res_arch = engine.decide_choice(
        state="Preciso desenhar uma nova arquitetura corporativa e criar um ADR",
        choices=choices,
    )
    assert res_arch.choice == "architect"
    assert res_arch.confidence > 0.5
    assert "architect" in res_arch.probabilities

    # Deve rotear para tdd-guide
    res_tdd = engine.decide_choice(
        state="Escrever testes unitários com pytest para cobrir novo endpoint",
        choices=choices,
    )
    assert res_tdd.choice == "tdd-guide"
    assert res_tdd.confidence > 0.5

    # Deve rotear para security-reviewer
    res_sec = engine.decide_choice(
        state="Verificar possível vazamento de senhas, secrets e autenticação JWT",
        choices=choices,
    )
    assert res_sec.choice == "security-reviewer"


def test_heuristic_engine_decide_noul() -> None:
    """Verifica decisão binária/probabilística (noul) do motor heurístico."""
    engine = HeuristicDecisionEngine()

    # Hipótese afirmativa
    noul_yes = engine.decide_noul(
        state="Alterações críticas detectadas no arquivo de segurança e autenticação",
        hypothesis="Esta mudança apresenta alto risco de segurança",
    )
    assert noul_yes.decision is True
    assert noul_yes.probability >= 0.5

    # Hipótese negativa
    noul_no = engine.decide_noul(
        state="Apenas atualizei a documentação do README e corrigi um typo",
        hypothesis="Esta mudança quebra a compatibilidade retroativa da API",
    )
    assert noul_no.decision is False
    assert noul_no.probability <= 0.5


def test_heuristic_engine_decide_score() -> None:
    """Verifica avaliação de pontuação/rubrica do motor heurístico."""
    engine = HeuristicDecisionEngine()
    rubric = ["Low Risk", "Medium Risk", "High Risk / Critical"]

    score_low = engine.decide_score(
        state="docs: update changelog and markdown headers",
        rubric=rubric,
    )
    assert score_low.level == "Low Risk"
    assert score_low.score == 0

    score_high = engine.decide_score(
        state="CRITICAL: refactoring core orchestrator state engine and auth secrets",
        rubric=rubric,
    )
    assert score_high.level == "High Risk / Critical"
    assert score_high.score == 2


def test_heuristic_engine_evaluate_bundle() -> None:
    """Verifica avaliação composta do motor heurístico em lote."""
    engine = HeuristicDecisionEngine()
    questions = {
        "target_agent": {
            "type": "choice",
            "criteria": {
                "architect": "Design arquitetural",
                "tdd-guide": "Testes unitários e TDD",
            },
        },
        "is_risky": {
            "type": "noul",
            "hypothesis": "Esta tarefa envolve risco estrutural",
        },
        "complexity": {
            "type": "score",
            "rubric": ["Simples", "Moderado", "Complexo"],
        },
    }

    report = engine.evaluate(
        state="Planejar nova arquitetura complexa para o sistema",
        questions=questions,
    )
    assert isinstance(report, SystemOneReport)
    assert "target_agent" in report.choices
    assert "is_risky" in report.nouls
    assert "complexity" in report.scores
    assert report.duration_ms >= 0.0


def test_outlines_engine_graceful_degradation() -> None:
    """Verifica que o OutlinesDecisionEngine opera com mock ou cai para fallback quando outlines ausente."""
    with patch.dict("sys.modules", {"outlines": None}):
        engine = OutlinesDecisionEngine(fallback_to_heuristic=True)
        res = engine.decide_choice(
            state="Escrever testes pytest",
            choices=["architect", "tdd-guide"],
        )
        assert res.choice in ["architect", "tdd-guide"]
        assert engine.is_available() is False


def test_outlines_engine_with_mocked_generator() -> None:
    """Verifica OutlinesDecisionEngine com gerador simulado de logits restritos."""
    mock_generator = MagicMock(return_value="architect")
    engine = OutlinesDecisionEngine(generator_override=mock_generator)
    res = engine.decide_choice(
        state="Desenhar diagrama C4 e ADR",
        choices=["architect", "tdd-guide"],
    )
    assert res.choice == "architect"
    assert res.confidence == 1.0


def test_onnx_nli_engine_graceful_degradation() -> None:
    """Verifica que o ONNXNLIDecisionEngine degrada suavemente quando onnxruntime ausente."""
    with patch.dict("sys.modules", {"onnxruntime": None}):
        engine = ONNXNLIDecisionEngine(fallback_to_heuristic=True)
        res = engine.decide_noul(
            state="Alteração pontual de documentação",
            hypothesis="Modificação crítica",
        )
        assert isinstance(res, NoulDecision)
        assert engine.is_available() is False


def test_system_one_router_agent_routing() -> None:
    """Verifica roteamento unificado de subagentes via SystemOneRouter."""
    router = SystemOneRouter(engine=HeuristicDecisionEngine())

    assert router.route_agent("Planejar ADR e contratos para nova feature").choice == "architect"
    assert router.route_agent("Criar suíte de testes unitários TDD").choice == "tdd-guide"
    assert (
        router.route_agent("Auditoria de segurança, senhas e OWASP").choice == "security-reviewer"
    )
    assert (
        router.route_agent("Revisão de código ruff, tipagem mypy e PEP 8").choice == "code-reviewer"
    )


def test_system_one_router_risk_and_triage() -> None:
    """Verifica avaliação de risco e triagem de quality gate via SystemOneRouter."""
    router = SystemOneRouter(engine=HeuristicDecisionEngine())

    # Risco alto
    high_diff = "diff --git a/src/corporate_engineer/models.py b/src/corporate_engineer/models.py"
    risk_high = router.assess_risk(high_diff)
    assert risk_high.decision is True
    assert risk_high.probability >= 0.5

    # Triagem de Quality Gate
    report = router.triage_quality_gate(
        prompt="Refatorar todo o orquestrador principal e banco de dados",
        diff="M src/corporate_engineer/orchestrator/engine.py",
    )
    assert report.suggested_agent in ["architect", "refactor-cleaner", "code-reviewer"]
    assert report.risk_level in ["MEDIUM", "HIGH", "CRITICAL"]


def _build_mock_tokenizer() -> MagicMock:
    tok = MagicMock()

    def _encode(premise: str, hypothesis: str | None = None) -> MagicMock:
        enc = MagicMock()
        enc.ids = [101, len(premise), len(hypothesis or ""), 102]
        enc.attention_mask = [1, 1, 1, 1]
        enc.type_ids = [0, 0, 1, 1]
        return enc

    tok.encode.side_effect = _encode
    return tok


def test_onnx_nli_engine_real_session_inference_and_honest_engine_name() -> None:
    """Verifica inferência real com session/tokenizer injetados e engine_name honesto."""
    mock_session = MagicMock()
    inp_ids = MagicMock()
    inp_ids.name = "input_ids"
    inp_mask = MagicMock()
    inp_mask.name = "attention_mask"
    mock_session.get_inputs.return_value = [inp_ids, inp_mask]

    # Logits 3 classes [contradiction, neutral, entailment]:
    # Quando input length combina com a opção/hipótese esperada, retorna entailment alto
    def _run(_output_names: object, feed: dict[str, list[list[int]]]) -> list[list[list[float]]]:
        hypo_len = feed["input_ids"][0][2]
        if hypo_len > 15:
            return [[[0.1, 0.2, 6.0]]]
        return [[[5.0, 0.2, 0.1]]]

    mock_session.run.side_effect = _run
    mock_tokenizer = _build_mock_tokenizer()

    engine = ONNXNLIDecisionEngine(
        fallback_to_heuristic=True,
        session=mock_session,
        tokenizer=mock_tokenizer,
    )
    assert engine.is_available() is True
    assert engine.has_model() is True

    choice = engine.decide_choice(
        state="Preciso escrever testes",
        choices={"short": "curto", "detailed_tdd_agent": "Especialista em testes unitários"},
    )
    assert choice.choice == "detailed_tdd_agent"
    assert "ONNX NLI" in (choice.rationale or "")
    assert mock_session.run.call_count == 2

    noul_true = engine.decide_noul(
        state="Alteração crítica",
        hypothesis="Hipótese longa de alto risco estrutural",
    )
    assert noul_true.decision is True
    assert noul_true.probability > 0.9

    noul_false = engine.decide_noul(state="Docs", hypothesis="Curta")
    assert noul_false.decision is False
    assert noul_false.probability < 0.1

    score = engine.decide_score(
        state="Mudança",
        rubric=["Baixo", "Risco Crítico Arquitetural"],
    )
    assert score.level == "Risco Crítico Arquitetural"
    assert score.score == 1

    report = engine.evaluate(
        state="Avaliação completa",
        questions={
            "agent": {"type": "choice", "choices": {"a": "curta", "b": "descrição bem longa aqui"}},
            "risk": {"type": "noul", "hypothesis": "Hipótese longa de risco"},
        },
    )
    assert report.engine_name == "onnx-nli"

    # Quando cai para fallback heurístico (sem session/tokenizer), NEVER reportar "onnx-nli"
    fallback_engine = ONNXNLIDecisionEngine(
        model_path="non_existent_model.onnx",
        fallback_to_heuristic=True,
    )
    fallback_report = fallback_engine.evaluate(
        state="Alteração simples",
        questions={"agent": {"type": "choice", "choices": ["architect", "tdd-guide"]}},
    )
    assert fallback_report.engine_name == "heuristic-fallback"


def test_onnx_nli_engine_lazy_loads_session_and_tokenizer(tmp_path: Path) -> None:
    """Verifica lazy loading thread-safe de onnxruntime.InferenceSession e tokenizers.Tokenizer."""
    import types

    model_file = tmp_path / "model_int8.onnx"
    tok_file = tmp_path / "tokenizer.json"
    model_file.write_bytes(b"fake-onnx")
    tok_file.write_text("{}", encoding="utf-8")

    mock_session = MagicMock()
    mock_session.get_inputs.return_value = []
    mock_session.run.return_value = [[[0.1, 0.1, 4.5]]]
    mock_tok = _build_mock_tokenizer()

    fake_ort = types.SimpleNamespace(InferenceSession=MagicMock(return_value=mock_session))
    fake_tokenizers = types.SimpleNamespace(
        Tokenizer=types.SimpleNamespace(from_file=MagicMock(return_value=mock_tok))
    )

    with patch.dict("sys.modules", {"onnxruntime": fake_ort, "tokenizers": fake_tokenizers}):
        engine = ONNXNLIDecisionEngine(model_path=model_file, fallback_to_heuristic=False)
        assert engine.has_model() is True
        res1 = engine.decide_noul(state="Teste", hypothesis="Hipótese")
        res2 = engine.decide_noul(state="Teste 2", hypothesis="Hipótese 2")
        assert res1.decision is True
        assert res2.decision is True
        # Lazy loaded apenas uma vez
        fake_ort.InferenceSession.assert_called_once_with(str(model_file))
        fake_tokenizers.Tokenizer.from_file.assert_called_once_with(str(tok_file))


def test_outlines_engine_caches_model_and_wires_noul_score() -> None:
    """Verifica cache de modelo sob RLock e wiring de decide_noul/decide_score no Outlines."""
    import types

    fake_model = MagicMock(name="loaded_transformers_model")
    transformers_loader = MagicMock(return_value=fake_model)

    def _choice_factory(_model: object, choices: list[str]) -> MagicMock:
        gen = MagicMock()
        gen.side_effect = lambda _prompt: choices[-1]
        return gen

    fake_outlines = types.SimpleNamespace(
        models=types.SimpleNamespace(transformers=transformers_loader),
        generate=types.SimpleNamespace(choice=MagicMock(side_effect=_choice_factory)),
    )

    with patch.dict("sys.modules", {"outlines": fake_outlines}):
        engine = OutlinesDecisionEngine(model_id="Qwen/Qwen2.5-0.5B-Instruct")
        assert engine.model_id == "Qwen/Qwen2.5-0.5B-Instruct"
        assert engine.is_available() is True

        c1 = engine.decide_choice("Estado 1", ["architect", "tdd-guide"])
        n1 = engine.decide_noul("Estado 2", "Hipótese")
        s1 = engine.decide_score("Estado 3", ["Low", "High"])
        c2 = engine.decide_choice("Estado 4", ["architect", "tdd-guide"])

        assert c1.choice == "tdd-guide"
        assert c2.choice == "tdd-guide"
        assert isinstance(n1, NoulDecision)
        assert n1.decision is False  # ["True", "False"][-1] == "False"
        assert s1.level == "High"
        assert s1.score == 1
        # Modelo carregado e cacheado uma única vez entre todas as chamadas
        transformers_loader.assert_called_once_with("Qwen/Qwen2.5-0.5B-Instruct")

        report = engine.evaluate(
            state="Avaliação Outlines",
            questions={
                "agent": {"type": "choice", "choices": ["architect", "tdd-guide"]},
                "risk": {"type": "noul", "hypothesis": "Risco"},
                "level": {"type": "score", "rubric": ["Low", "High"]},
            },
        )
        assert report.engine_name == "outlines"

    # Quando outlines indisponível, evaluate deve reportar heuristic-fallback
    with patch.dict("sys.modules", {"outlines": None}):
        fallback_engine = OutlinesDecisionEngine(fallback_to_heuristic=True)
        fb_report = fallback_engine.evaluate(
            state="Avaliação fallback",
            questions={"agent": {"type": "choice", "choices": ["architect", "tdd-guide"]}},
        )
        assert fb_report.engine_name == "heuristic-fallback"
