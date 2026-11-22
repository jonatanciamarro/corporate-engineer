# Estado Atual do Projeto (`state.md`)

> **Documento Vivo de Estado e Continuidade de Sessão**  
> *Este arquivo DEVE ser lido no início de cada sessão por qualquer agente e atualizado ao final de cada entrega para garantir transição suave e contexto perene.*

---

## 1. Visão Geral & Saúde do Projeto

| Métrica / Aspecto | Status Atual | Detalhes |
|---|---|---|
| **Projeto** | `corporate-engineer` | Framework Corporativo de Engenharia com Agentes AI & Orquestrador Corp-Pipeline |
| **Versão** | `0.1.0` | Python 3.10+ (Target: Python 3.11) |
| **Branch Ativa** | `main` | 🟢 Suíte com 155/155 testes PASS, 88% cobertura, ADR-014 e SafeStorageCleaner integrados |
| **Ambiente Local** | `.venv` (Python 3.11.9) | 🟢 Ambiente virtual ativo, compatibilidade Python 3.10/3.11+ assegurada (`-e .[dev,test]`) |
| **Armazenamento Total** | 🟢 **74.6 GB Livres (Multi-Disco)** | C: 20.77 GB, D: 17.85 GB, E: 35.99 GB, F: 24.49 GB (+27.9 GB recuperados) |
| **Testes (Pytest + Hypothesis)** | 🟢 **155/155 PASS** | Cobertura global robusta (`pytest-cov`) em 17.24s |
| **Linter & Formatação (Ruff)** | 🟢 **0 Erros** | Validação 100% limpa com Ruff (92 arquivos verificados e formatados) |
| **Tipagem Estática (Mypy)** | 🟢 **0 Erros** | 55 arquivos validados estritamente no root |
| **Scanner de Segredos** | 🟢 **0 Vazamentos** | Validado pelo `secret_scanner.py` (tempo de varredura otimizado para sub-1s) |
| **Orquestrador Central** | 🟢 **Corp-Pipeline Ativo** | Arquitetura em 3 Camadas: Core, Intelligence & Governance |
| **Registros de Capacidades** | 🟢 **7 Registros Canônicos** | `.agents/orchestration/` (capabilities, agents, skills, workflows, tools, integrations, backlog) |
| **Lifecycle Hooks** | 🟢 **SessionStart & PreInvocation Ativos** | `.agents/hooks.json` integrado com push remoto Always-On antes da geração de PR |

---

## 2. O Que Foi Feito Recentemente

### Sessão Atual (Implementação de CORP-DISK-CLEANUP / ADR-014: Safe Storage Optimizer & Automated Disk Hygiene):
1. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `StorageTarget`: Contrato tipado com `category`, `name`, `path`, `size_bytes`, `is_safe` e `description`.
   - `StorageCleanResult`: Detalhe da limpeza de cada alvo com tratamento seguro de erros e métrica de bytes liberados.
   - `StorageOptimizationReport`: Relatório estruturado consolidando `total_freed_bytes`, `total_freed_gb`, `results` e flag `dry_run`.
2. **Motor Safe Storage Cleaner (`src/corporate_engineer/quality/storage_cleaner.py`)**:
   - Classe `SafeStorageCleaner` com invariante rigorosa de proteção: recusa categórica de exclusão de pastas pessoais (`Desktop`, `Documents`, `Music`, `Pictures`, `Videos`, `OneDrive`, `.ssh`, `.aws`) e de diretórios da workspace de código.
   - Detecção e varredura padronizada de caches de desenvolvimento (`pip`, `npm`, `torch`, `huggingface`) e alvos de modelos pesados descontinuados (GPT4All e blobs órfãos do Ollama).
   - Suporte defensivo a simulação em memória (`--dry-run`).
3. **CLI Corporativa (`src/corporate_engineer/cli.py`)**:
   - Adição do subcomando oficial `corporate-engineer clean` com flags `--dry-run` e `--format [text|json]`.
4. **Otimização do Pre-Flight Scanner (`.agents/skills/corp-pipeline/scripts/secret_scanner.py`)**:
   - Ignora pastas binárias de modelos (`models/`) e extensões de pesos (`.onnx`, `.bin`, `.gguf`), reduzindo o tempo de varredura de segurança de 45s para 0.5s.
5. **Suíte de Testes Automatizados (Shift-Left TDD)**:
   - 10 novos testes unitários e de integração em `tests/test_storage_cleaner.py` (100% PASS, 80% de cobertura).
   - Expansão da suíte global para **155/155 testes PASS** em 17.24s.
6. **Recuperação Real de Armazenamento**:
   - Recuperação prática de **mais de 20.3 GB** no disco local `C:`, saindo de estado crítico de 64 MB para **20.38 GB livres**.
7. **Governança & Documentação**:
   - Formalização de [ADR-014](docs/adr/ADR-014-disk-storage-optimization-and-cleaner.md) e minuta de PR em [PR-CORP-014.md](docs/pull_requests/PR-CORP-014.md).

---

## 3. Roteiro de Evolução do Framework (Roadmap)

### 🎯 Trilha 1: Expansão da CLI Corporativa (`src/corporate_engineer/cli.py`)
- `[x]` Adicionar subcomando `audit`: executa pre-flight de qualidade diretamente pela CLI (com `--strict` e `--format json`).
- `[x]` Adicionar subcomando `index`: indexa uma base de código via AST e exporta o grafo semântico (com `--format json` e `--output`).
- `[x]` Adicionar subcomando `dag`: inspeciona ciclo de vida FSM, transições e checkpoints (`--show-phases`, `--checkpoints`, `--format json`, `--mermaid`, `--trace`).
- `[x]` Adicionar subcomando `mcp`: testa conectividade e inspeciona schemas de servidores MCP stdio/SSE (`ping`, `list-tools`, `call`).
- `[x]` Adicionar subcomando `eval`: scorecard semântico de código via AST.
- `[x]` Adicionar subcomando `blast-radius`: análise de impacto de mudanças e testes afetados.
- `[x]` Adicionar subcomando `telemetry`: inspeção e renderização de relatórios de spans OTel.
- `[x]` Adicionar subcomando `test-surgical`: execução cirúrgica de testes via git diff e blast radius (`IMP-0010`).
- `[x]` Adicionar subcomando `decide`: inferência probabilística e roteamento de subagentes (`IMP-0013 / IMP-0014 / Trilha 1`).
- `[x]` Adicionar subcomando `dataset`: geração sintética e receitas de treinamento (`IMP-0014 / Trilha 1`).
- `[x]` Adicionar subcomando `fix`: auto-remediação de violações de AST (`IMP-0012`).
- `[x]` Adicionar subcomando `clean`: otimização segura de armazenamento e limpeza de disco (`ADR-014`).

### 🔌 Trilha 2: Conectores e Transporte Remoto MCP (`src/corporate_engineer/mcp/`)
- `[x]` Suporte a transporte Server-Sent Events (SSE) / JSON-RPC 2.0 para servidores MCP remotos.
- `[x]` Autenticação corporativa: Bearer Tokens e injeção padronizada de cabeçalhos de segurança.
- `[x]` Testes de resiliência: reconexão automática com backoff exponencial e circuit breaker (`IMP-0002`).
- `[x]` MCP Enterprise Hub com isolamento de falhas e poda seletiva via Sistema 1 (`IMP-0011`).

### 🧠 Trilha 3: AST Indexing & Code Intelligence (`src/corporate_engineer/rag/`)
- `[x]` Extração semântica de hierarquia de herança e relacionamentos entre classes/funções.
- `[x]` Grafo de chamadas de funções e métodos e mapeamento estruturado de importações.
- `[x]` Testes baseados em propriedades (PBT com Hypothesis) cobrindo estruturas de sintaxe do Python 3.11+.
- `[x]` Cache de indexação baseado em SHA-256 (`IMP-0004`).
- `[x]` Análise de blast radius e árvore de propagação de mudanças (`IMP-0008`).

### ⚙️ Trilha 4: Orquestração e DAGs de Agentes (`src/corporate_engineer/orchestrator/`)
- `[x]` Paralelização de nós de agentes independentes no grafo de engenharia (`execute_parallel_tasks`).
- `[x]` Persistência de checkpoints de execução (`save_checkpoint`, `load_checkpoint`, `list_checkpoints`).
- `[x]` Mecanismo determinístico de recuperação de falhas e rollback (`rollback_to_checkpoint`).
- `[x]` Instrumentação nativa de spans OpenTelemetry em cada nó do fluxo (`IMP-0009`).

### 🔭 Trilha 5: Observabilidade e Telemetria OTel (`src/corporate_engineer/telemetry/`)
- `[x]` Tracer OpenTelemetry-compatible (`AgentTracer`, spans, hierarquia pai-filho, latências e tokens).
- `[x]` Captura granular de erros e tempos com precisão monotônica.
- `[x]` Exportador e relatórios consolidados em JSON e CLI.

### 👑 Trilha 6: Corp-Pipeline Master Orchestrator (Sistema Central Permanente)
- `[x]` Regra permanente Always-On `.agents/rules/corp-pipeline-orchestrator.md`.
- `[x]` Registros canônicos `.agents/orchestration/` (capabilities, agents, skills, workflows, tools, integrations, backlog).
- `[x]` Hook `SessionStart` em `.agents/hooks.json` com injeção de contexto via protojson nativo.
- `[x]` Hook `PreInvocation` gerador automático de URLs pré-preenchidas de PR 1-clique (`pr-link`).
- `[x]` Governança de melhorias: formato padronizado de recomendação e persistência no backlog.
- `[x]` Formalização de ADR-002 e documentação técnica (`architecture.md` e `operating-manual.md`).

---

## 4. Próximos Passos Imediatos para a Próxima Sessão

1. `[x]` **Trilha Operacional: CORP-DISK-CLEANUP & ADR-014** (Concluído: `SafeStorageCleaner`, modelos DTO, subcomando CLI `clean`, 155/155 testes PASS, 20.38 GB livres no C:).
2. `[ ]` **Trilha Estratégica 2: Novas Fronteiras de Engenharia no Backlog (`IMP-0015` a `IMP-0017`)**:
   - `IMP-0015`: Autonomous Benchmark & Eval Harness (comparação de acurácia, latência e throughput entre Heurístico vs SLM LoRA vs ONNX Runtime).
   - `IMP-0016`: Multi-Agent Swarm Coordinator via MCP Hub.
   - `IMP-0017`: GitHub Actions Workflow de Auto-Remediação em PRs (`.github/workflows/self-heal.yml`).
3. `[ ]` **Trilha Estratégica 3: Dogfooding e Teste de Ponta a Ponta com Projeto Real**:
   - Execução completa do comando `corporate-engineer run --ticket CORP-101 --task "..."`.

---

## 5. Histórico de Modificações do `state.md`

| Data/Hora (ISO) | Autor | Resumo da Alteração |
|---|---|---|
| `2026-11-22T10:02:00-03:00` | Corp-Pipeline Master Orchestrator | Conclusão do ciclo TDD para CORP-DISK-CLEANUP: motor `SafeStorageCleaner` (`src/corporate_engineer/quality/storage_cleaner.py`), modelos Pydantic v2 `StorageTarget`, `StorageCleanResult` e `StorageOptimizationReport`, subcomando CLI `clean`, otimização do `secret_scanner.py`, 10 novos testes unitários (155/155 testes PASS), elaboração do ADR-014 e PR-CORP-014, e recuperação de mais de 20.3 GB livres na partição C: (de 64 MB para 20.38 GB livres). |
| `2026-11-22T08:20:00-03:00` | Corp-Pipeline Master Orchestrator | Execução de `git pull` na branch `main`: sincronização com origin/main (fast-forward `1498dfe..f0d3b69`), incorporando o merge do PR #17 (Trilha 1: Colab Notebook, modelos ONNX INT8 e suite de testes) e validação local completa (145/145 testes PASS, 0 erros Ruff e Mypy). |
| `2026-11-22T02:37:00-03:00` | Corp-Pipeline Master Orchestrator | Integração real dos artefatos ONNX INT8 fine-tuned do Qwen2.5-0.5B gerados via Google Colab (`qwen_int8_onnx.zip` extraído em `models/` contendo `model.onnx`, `model_int8.onnx`, `config.json`, `generation_config.json`). Execução e validação completa dos testes com ONNX Runtime local (`tests/test_system_one_colab_onnx.py` 7/7 PASS). |
| `2026-11-21T22:05:00-03:00` | Corp-Pipeline Master Orchestrator | Conclusão da Trilha 1 do Roadmap: geração do Jupyter Notebook interativo `notebooks/train_system_one_colab.ipynb` com badge Open In Colab, atualização do script `scripts/train_system_one_colab.py`, criação de `models/`, implementação de lazy loading com fallback transparente em `ONNXNLIDecisionEngine`, suporte a `--engine onnx` na CLI, resiliência de rede e git com timeouts e `tests/conftest.py`, elaboração do ADR-013 e PR-CORP-013, expansão para 145/145 testes PASS (88% cobertura) e push da branch `feat/TRILHA-1-colab-onnx-training` para origin. |
| `2026-11-21T13:32:00-03:00` | Corp-Pipeline Master Orchestrator | Atualização formal do state.md e sincronização no remote: consolidação de todas as 14 melhorias na main, 138/138 testes PASS (88% cobertura), 0 erros Ruff/Mypy, catalogação dos próximos passos estratégicos (Colab Fine-Tuning real, IMP-0015/016/017 e Dogfooding) e push para origin/main. |
| `2026-11-21T10:14:00-03:00` | Corp-Pipeline Master Orchestrator | Consolidação completa das 4 etapas aprovadas pelo usuário na branch `main`: PR #11 (IMP-0011) e PR #15 (IMP-0012) mergeados com sucesso, dataset sintético do Sistema 1 de 100 amostras validado com receita Colab, testes de inferência reflexiva em todos os modos e suíte global 100% verde (138/138 PASS, 88% cobertura, 0 erros Ruff/Mypy). |
| `2026-11-21T10:05:00-03:00` | Corp-Pipeline Master Orchestrator | Conclusão do ciclo TDD para IMP-0012: motor `ASTSelfHealingFixer` (`src/corporate_engineer/eval/fixer.py`), modelos Pydantic v2 `FixDetail` e `FixReport`, transformadores AST para `__init__ -> None`, argumentos padrão mutáveis e limpeza de `pass` redundante, guardrail do Sistema 1, subcomando CLI `fix`, formalização do ADR-012, PR-CORP-012 e expansão da suíte para 138/138 testes PASS (88% cobertura). |
| `2026-11-20T21:20:00-03:00` | Corp-Pipeline Master Orchestrator | Conclusão do ciclo TDD para IMP-0011: motor `MCPEnterpriseHub` (`src/corporate_engineer/mcp/hub.py`), modelos Pydantic v2, suporte a `.mcp.json`, isolamento de falhas por Circuit Breaker individual, poda seletiva via Sistema 1, subcomando CLI `mcp hub` (`list`, `call`, `prune`), formalização do ADR-011, PR-CORP-011 e expansão da suíte para 130/130 testes PASS (88% cobertura). |
| `2026-11-20T10:15:00-03:00` | Corp-Pipeline Master Orchestrator | Conclusão do ciclo TDD para IMP-0014: pipeline gratuito de fine-tuning para o Sistema 1 (`src/corporate_engineer/system_one/dataset.py`, `trainer.py`), modelos Pydantic v2, injeção universal em `ExecutionGraph` (DAG), `SurgicalTestRunner`, `git_utils.py` (Conventional Commits), novos modos e subcomandos CLI (`dataset`, `decide --mode commit/skip`), formalização do ADR-010, PR-CORP-010 e expansão da suíte para 124/124 testes PASS (88% cobertura). |
| `2026-11-20T09:38:00-03:00` | Corp-Pipeline Master Orchestrator | Blindagem Always-On da Invariante de Push Remoto Pré-PR: atualização em `git_utils.py` (`is_branch_pushed`, `push_branch_to_remote`, `ensure_pushed=True`), correção dos caminhos em `.agents/hooks.json` e `pr_link_generator.py`, adição da Invariante 8 em `AGENTS.md`, `GEMINI.md`, `corp-pipeline-orchestrator.md` e `common-git-workflow.md`, expansão da suíte para 116/116 testes PASS. |
| `2026-11-20T09:28:00-03:00` | Corp-Pipeline Master Orchestrator | Conclusão do ciclo TDD para IMP-0013: módulo System One (`src/corporate_engineer/system_one/`), modelos Pydantic v2, motores heurístico, outlines e ONNX NLI, fachada `SystemOneRouter`, subcomando `corporate-engineer decide`, formalização do ADR-009, PR-CORP-009, expansão da suíte para 113/113 testes PASS (87% cobertura) e push da branch `feat/IMP-0013-system-one-engine` para origin no GitHub. |
