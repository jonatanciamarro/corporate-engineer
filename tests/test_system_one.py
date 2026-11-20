"""
Tests for Open-Source System-One Decision Engine (IMP-0013).
"""

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
