# Pull Request: feat: add open-source system-one decision engine (IMP-0013)

## 📋 Identificação da Demanda
- **Ticket / Issue**: `IMP-0013` (Ref: `CORP-009`)
- **Tipo**: `feat`
- **Módulos Afetados**:
  - `src/corporate_engineer/models.py`
  - `src/corporate_engineer/system_one/` (`base.py`, `heuristic_engine.py`, `outlines_engine.py`, `nli_engine.py`, `router.py`, `__init__.py`)
  - `src/corporate_engineer/cli.py`
  - `docs/adr/ADR-009-open-source-system-one-decisions.md`
  - `.agents/orchestration/improvement-backlog.md`
  - `tests/test_system_one.py`
  - `tests/test_cli.py`
  - `state.md`
- **Classificação de Risco**: `[x] Baixo` | `[ ] Médio` | `[ ] Alto` | `[ ] Crítico`
- **Branch**: `feat/IMP-0013-system-one-engine` ➔ `main`

---

## 🎯 Resumo Executivo da Mudança

Esta entrega implementa formalmente a proposta **`IMP-0013`** do backlog contínuo de melhorias (`improvement-backlog.md`), introduzindo o **Open-Source System-One Decision Engine** no framework `corporate-engineer`.

O recurso traz para a arquitetura uma camada de decisões probabilísticas estruturadas e tipadas (System One) de altíssima velocidade (sub-milissegundo), desacoplando a *tomada de decisão* da *geração de texto*. Toda a solução é 100% open-source, local, compatível com Python 3.10+, sem dependência de APIs de terceiros e sem alucinação de esquemas.

### Principais Entregas:
1. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `ChoiceDecision`: Seleção categórica com probabilidade e distribuição calibrada (`choice`, `confidence`, `probabilities`, `rationale`).
   - `NoulDecision`: Decisão booleana condicional com probabilidade contínua de 0.0 a 1.0 (`decision`, `probability`, `rationale`).
   - `ScoreDecision`: Pontuação contra rubricas ordenadas (`score`, `level`, `confidence`, `rationale`).
   - `SystemOneReport`: Relatório completo consolidado de lote de decisões (`task`, `engine_name`, `duration_ms`, mapeamentos, `suggested_agent`, `risk_level`, `requires_human_approval`).

2. **Arquitetura Modular System One (`src/corporate_engineer/system_one/`)**:
   - `SystemOneEngine`: Contrato base abstrato padronizado.
   - `HeuristicDecisionEngine`: Motor ultrarrápido em Python puro (<1ms) com calibração probabilística via softmax e sigmoide. Zero dependências externas obrigatórias.
   - `OutlinesDecisionEngine`: Decodificação restrita por autômatos finitos (FSM) via biblioteca `outlines` com SLMs locais, garantindo 0% de erro estrutural.
   - `ONNXNLIDecisionEngine`: Inferência de linguagem natural (NLI) via ONNX Runtime para cálculo contínuo de acarretamento (*entailment*).
   - `SystemOneRouter`: Fachada unificada para roteamento dos 8 subagentes canônicos, análise de risco de diffs e triagem de quality gate.

3. **Integração na CLI Corporativa (`src/corporate_engineer/cli.py`)**:
   - Novo subcomando oficial `corporate-engineer decide`:
     - Modos: `--mode route` (seleção de agente), `--mode risk` (avaliação de risco) e `--mode triage` (triagem do quality gate).
     - Motores: `--engine auto|heuristic|outlines|nli`.
     - Formatos: `--format text|json` e exportação com `--output`.

4. **Arquitetura Formal (ADR-009)**:
   - Formalizada em `docs/adr/ADR-009-open-source-system-one-decisions.md`.

---

## 🧪 Evidências de Teste (Shift-Left TDD)

- [x] **Certificação RED**: Testes em `tests/test_system_one.py` foram criados previamente e falharam antes da codificação.
- [x] **Certificação GREEN**: 100% dos testes aprovados após a implementação.
- [x] **Expansão da Suíte**: De 99 para **113 testes passando** em 11.81s.
- [x] **Cobertura Global**: **87%** de cobertura de código (`pytest-cov`).

---

## 🛡️ Quality Gate & Pre-Flight Verification

- [x] **Unit & PBT Tests**: 113/113 PASS (`pytest`)
- [x] **Code Style & Linting**: 0 erros (`ruff check .`)
- [x] **Code Formatting**: 0 inconformidades (`ruff format --check .`)
- [x] **Static Type Checking**: 0 erros em 43 arquivos (`mypy .`)
- [x] **Secret Scanning**: 0 segredos detectados (`secret_scanner.py`)
