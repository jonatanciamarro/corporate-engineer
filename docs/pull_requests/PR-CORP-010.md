# Pull Request: feat: free system-one slm fine-tuning pipeline & framework injection (IMP-0014)

## 📋 Identificação da Demanda
- **Ticket / Issue**: `IMP-0014` (Ref: `CORP-010`)
- **Tipo**: `feat`
- **Módulos Afetados**:
  - `src/corporate_engineer/models.py`
  - `src/corporate_engineer/system_one/` (`dataset.py`, `trainer.py`, `router.py`, `heuristic_engine.py`)
  - `src/corporate_engineer/orchestrator/graph.py`
  - `src/corporate_engineer/quality/surgical_runner.py`
  - `src/corporate_engineer/git_utils.py`
  - `src/corporate_engineer/cli.py`
  - `docs/adr/ADR-010-free-system-one-slm-finetuning-and-injection.md`
  - `.agents/orchestration/improvement-backlog.md`
  - `tests/test_system_one_pipeline.py`
  - `state.md`
- **Classificação de Risco**: `[x] Baixo` | `[ ] Médio` | `[ ] Alto` | `[ ] Crítico`
- **Branch**: `feat/IMP-0014-system-one-pipeline` ➔ `main`

---

## 🎯 Resumo Executivo da Mudança

Esta entrega implementa a proposta **`IMP-0014`** do backlog contínuo de melhorias (`improvement-backlog.md`), consolidando um **Pipeline 100% Gratuito de Fine-Tuning de SLMs para o Sistema 1** e a **Injeção Universal do Sistema 1 em múltiplos módulos do framework**.

Inspirado na *Dual-Process Theory* (Sistema 1 vs Sistema 2 de Daniel Kahneman), o framework agora possui capacidade de auto-geração de datasets de treino sintéticos de domínio, receita de treinamento com LoRA/PEFT para execução a custo zero no Google Colab (GPU T4 gratuita) ou CPU comum, e integração direta em pontos críticos de decisão do ecossistema.

### Principais Entregas:

1. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `TrainingSample`: Contrato para amostras supervisionadas (`instruction`, `input`, `output`, `task_type`, `metadata`).
   - `DatasetReport`: Relatório consolidado de dataset gerado com contagens e checksum SHA-256.
   - `DatasetExportConfig`: Configuração de exportação JSONL.
   - `FailureActionDecision`: Decisão rápida de recuperação de falhas na DAG (`retry`, `rollback`, `dispatch_agent`).
   - `ContextPruningReport`: Relatório de poda semântica de tokens para proteção de context window.

2. **Gerador de Datasets Sintéticos de Domínio (`src/corporate_engineer/system_one/dataset.py`)**:
   - `SystemOneDatasetGenerator`: sintetiza pares de treino corporativos para roteamento de agentes, análise de risco de diffs, classificação de Conventional Commits e descarte condicional de nós da DAG, com exportação para JSONL.

3. **Harness de Treinamento Gratuito & Receita Colab (`src/corporate_engineer/system_one/trainer.py`)**:
   - `SystemOneTrainer`: gera receita autônoma em 1-clique para Google Colab (`scripts/train_system_one_colab.py`) usando Hugging Face PEFT/LoRA sobre SLMs leves (`Qwen2.5-0.5B`, `SmolLM2-360M`), com estimativa de consumo de VRAM < 1.5GB e exportação para ONNX Runtime Int8.

4. **Injeção Universal do Sistema 1 nos Módulos Centrais**:
   - **`orchestrator/graph.py`**: `ExecutionGraph` com suporte a `should_skip_node` (pula nós irrelevantes como scanners em docs) e `triage_failure` (triagem instantânea entre retry e rollback).
   - **`quality/surgical_runner.py`**: `evaluate_scope_expansion` avalia se mudanças em modelos centrais requerem expansão dos testes cirúrgicos para a suíte completa.
   - **`git_utils.py`**: `classify_commit_type` classifica deterministicamente o tipo de Conventional Commit a partir do git diff.
   - **`system_one/router.py`**: Novos métodos `classify_commit`, `should_skip_node`, `triage_failure` e `prune_context`.

5. **Expansão da CLI Corporativa (`src/corporate_engineer/cli.py`)**:
   - Novo subcomando oficial `corporate-engineer dataset` com ações `generate` e `recipe`.
   - Novos modos no subcomando `corporate-engineer decide`: `--mode commit` e `--mode skip`.

---

## 🧪 Evidências de Teste (Shift-Left TDD)

- [x] **Certificação RED**: Testes em `tests/test_system_one_pipeline.py` foram criados previamente e falharam antes da codificação.
- [x] **Certificação GREEN**: 100% dos testes aprovados após a implementação.
- [x] **Expansão da Suíte**: De 113 para **124 testes passando** em 27.67s.
- [x] **Cobertura Global**: **88%** de cobertura de código (`pytest-cov`).

---

## 🛡️ Quality Gate & Pre-Flight Verification

- [x] **Linter (Ruff)**: 0 erros (`ruff check .` e `ruff format --check .`).
- [x] **Tipagem Estática (Mypy)**: 0 erros em 46 arquivos fonte (`mypy .`).
- [x] **Scanner de Segredos**: 0 credenciais ou chaves expostas (`secret_scanner.py .`).
- [x] **Zero Regressões**: Suíte de 124 testes unitários e baseados em propriedades 100% verde.
