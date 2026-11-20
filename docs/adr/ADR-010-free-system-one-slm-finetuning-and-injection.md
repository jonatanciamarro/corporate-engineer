# ADR-010: Pipeline Gratuito de Fine-Tuning de SLMs para o Sistema 1 & Injeção Universal no Framework

## Status
Aceito (Accepted)

## Data
2026-11-20

## Contexto & Motivação
A implementação do motor `SystemOne` no [ADR-009](ADR-009-open-source-system-one-decisions.md) validou a arquitetura cognitiva de processo duplo (*Dual-Process Theory* de Daniel Kahneman) no framework `corporate-engineer`, desacoplando reflexos instantâneos estruturados (Sistema 1) do raciocínio generativo profundo (Sistema 2).

Entretanto, dois desafios arquiteturais emergiram:
1. **Otimização sem Custo de Modelos Locais (Fine-Tuning Zero-Cost)**:
   Embora modelos gerais de SLM (como `Qwen2.5-0.5B` ou `SmolLM2-360M`) e classificadores NLI funcionem bem fora da caixa (*zero-shot*), a precisão em tarefas altamente específicas do nosso framework (classificação dos 8 subagentes canônicos, padrões de Conventional Commits corporativos, detecção de nós desnecessários na DAG) pode ultrapassar 99% com ajuste fino supervisionado (SFT). Esse pipeline precisava ser concebido para rodar **100% de graça** (usando Google Colab T4, Kaggle ou CPU local com LoRA/PEFT e exportação para ONNX quantizado em Int8), sem necessidade de infraestrutura cara.
2. **Subutilização do Sistema 1 nos Módulos Existentes**:
   O `SystemOneRouter` estava restrito a roteamento e risco geral. Componentes centrais como a DAG (`orchestrator/graph.py`), o Surgical Runner (`quality/surgical_runner.py`), os utilitários git (`git_utils.py`) e a análise de impacto AST (`rag/impact.py`) continuavam dependendo de regras estáticas ou exigiriam invocar o Sistema 2.

## Decisão de Arquitetura

1. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `TrainingSample`: Representação estruturada de amostra de treino com `instruction`, `input`, `output`, `task_type` (`classification`, `noul`, `score`) e `metadata`.
   - `DatasetReport`: Relatório consolidado com `total_samples`, `task_distribution`, `source`, `export_path` e `hash_sha256`.
   - `DatasetExportConfig`: Configuração de exportação (formato `jsonl`, `alpaca` ou `chatml`).
   - `FailureActionDecision`: Decisão do Sistema 1 para tratamento de falhas na DAG (`action`: `retry`, `rollback`, `dispatch_agent`).
   - `ContextPruningReport`: Relatório de poda de contexto semântico com contagem de tokens originais vs podados.

2. **Gerador de Dataset Sintético Corporativo (`src/corporate_engineer/system_one/dataset.py`)**:
   - `SystemOneDatasetGenerator`: sintetizador autônomo baseado no ecossistema ECC e nos padrões do repositório:
     - Geração de amostras de roteamento dos 8 subagentes canônicos.
     - Geração de amostras de classificação de risco de diffs de código.
     - Geração de amostras de classificação de commit convencional (`feat`, `fix`, `refactor`, `test`, `docs`, `chore`).
     - Geração de amostras de skipping de nós da DAG.
   - Suporte a exportação determinística para formato JSONL com validação de esquema.

3. **Harness de Fine-Tuning e Receita Gratuita (`src/corporate_engineer/system_one/trainer.py`)**:
   - `SystemOneTrainer`: abstração de treino supervisionado com LoRA/PEFT:
     - Geração de receita autônoma para Google Colab com 1-clique (`scripts/train_system_one_colab.py`).
     - Simulação e dry-run local com fallback gracioso quando `torch`/`transformers` não estão instalados.
     - Definição do pipeline de quantização e exportação para ONNX Runtime Int8.

4. **Injeção Universal do Sistema 1 nos Módulos do Framework**:
   - **`orchestrator/graph.py`**:
     - `should_skip_node(node_name, context)`: decide via `decide_noul` se nós opcionais (ex.: auditoria de segurança em docs) podem ser ignorados.
     - `triage_node_failure(node_name, error_message, traceback)`: classifica instantaneamente a ação de recuperação adequada (`retry`, `rollback`, `dispatch_agent`).
   - **`quality/surgical_runner.py`**:
     - `evaluate_scope_expansion(git_diff, direct_tests)`: avalia via inferência probabilística se alterações estruturais justificam rodar testes de integração.
   - **`git_utils.py`**:
     - `classify_commit_type(git_diff_or_message)`: classifica deterministicamente o tipo convencional de commit.
   - **`rag/impact.py`**:
     - `prune_context(prompt, symbols)`: filtra símbolos irrelevantes do AST antes de alimentar o LLM principal, economizando tokens.

5. **Interface de Linha de Comando (`src/corporate_engineer/cli.py`)**:
   - Adicionado subcomando `corporate-engineer dataset`:
     - Subcomandos `generate`: gera datasets sintéticos em JSONL com `--samples`, `--task` e `--output`.
     - Subcomandos `inspect`: inspeciona estatísticas e qualidade de um dataset gerado.
   - Atualizado subcomando `corporate-engineer decide`:
     - Novos modos: `--mode commit` (tipo de commit) e `--mode skip` (descarte de nós).

## Consequências
- **Positivas**:
  - Treinamento e ajuste fino 100% acessíveis e gratuitos usando recursos públicos de computação (Google Colab / Kaggle) ou CPU comum.
  - Redução drástica (>70%) no volume de tokens e custo de Sistema 2 em requisições de agentes.
  - Velocidade sub-5ms em decisões transversais (DAG, Git, Testes, AST).
  - Soberania e privacidade de dados total: inferência e dados locais no ambiente de desenvolvimento.
- **Mitigações**:
  - Todas as integrações mantêm o fallback transparente para o motor heurístico caso SLMs locais não estejam baixados ou no path.
