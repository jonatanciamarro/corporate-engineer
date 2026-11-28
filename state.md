# Estado Atual do Projeto (`state.md`)

> **Documento Vivo de Estado e Continuidade de Sessão**  
> *Este arquivo DEVE ser lido no início de cada sessão por qualquer agente e atualizado ao final de cada entrega para garantir transição suave e contexto perene.*

---

## 1. Visão Geral & Saúde do Projeto

| Métrica / Aspecto | Status Atual | Detalhes |
|---|---|---|
| **Projeto** | `corporate-engineer` | Framework Corporativo de Engenharia com Agentes AI & Orquestrador Corp-Pipeline |
| **Versão** | `0.1.0` | Python 3.10+ (Target: Python 3.11) |
| **Branch Ativa** | `feat/IMP-0040-p3-frozen-dtos-and-skills-curation` | 🟢 Baseada em `7277aeb` (Onda `IMP-0042` / `ADR-036` em execução) |
| **Ambiente Local** | `.venv` (Python 3.11.9) | 🟢 Ambiente virtual ativo (`--system-site-packages` + `.pth` apontando para `src/`) |
| **Armazenamento Total** | 🟢 **74.6 GB Livres (Multi-Disco)** | C: 20.77 GB, D: 17.85 GB, E: 35.99 GB, F: 24.49 GB (+27.9 GB recuperados) |
| **Testes (Pytest + Hypothesis)** | 🟢 **436/436 PASS** | `IMP-0042` concluído em 239.31s (`test_mcp_server_and_plugin.py` + `test_runtime_honesty_and_wiring.py` + `test_concurrency_thread_safety.py` incluídos) |
| **Linter & Formatação (Ruff)** | 🟢 **0 Erros** | Validação limpa com Ruff (188 arquivos formatados — `IMP-0042`) |
| **Tipagem Estática (Mypy)** | 🟢 **0 Erros** | 108 arquivos fonte validados estritamente (`IMP-0042`) |
| **Scanner de Segredos** | 🟢 **0 Vazamentos** | Validado por `.agents/skills/corp-pipeline/scripts/secret_scanner.py` e `CanonicalSecretScanner` |
| **Wiring & Scorecard EDD** | 🟢 **100% Wired** | `audit --wiring` 49/49 módulos conectados (`PASS`); 6 ferramentas MCP (`blast_radius`, `eval_scorecard`, `audit_wiring`, `secret_scan`, `surgical_tests_plan`, `ast_symbols`) |
| **Orquestrador Central** | 🟢 **Corp-Pipeline Always-On Ativo** | Frontmatter `trigger: always_on` ativo em `.agents/rules/corp-pipeline-orchestrator.md` |
| **Registros de Capacidades** | 🟢 **7 Registros Canônicos** | `.agents/orchestration/` (`IMP-0034`–`IMP-0042` `IMPLEMENTED`; curadoria `21 DAILY / 310 LIBRARY`) |
| **Lifecycle Hooks & MCP** | 🟢 **5 Hooks + Plugin MCP Workspace** | `.agents/hooks.json` (`run_hook.py`) & `.agents/plugins/corporate-engineer/` (`IMP-0042` ✅) |

---

## 2. O Que Foi Feito Recentemente (Últimas 3 Ondas + Onda Ativa)

📚 **Histórico Completo (`IMP-0001`–`IMP-0035` / `CORP-DISK-CLEANUP`)**: Arquivado em [docs/history/state_archive_v1.md](docs/history/state_archive_v1.md).

### Onda Ativa ✅ — `IMP-0042` / `ADR-036` (Runtime Alignment, MCP Server Nativo & Honestidade CLI) — **IMPLEMENTADO**:
- **`CorporateEngineerMCPServer`** (`mcp serve`): servidor stdio JSON-RPC 2.0 com 6 ferramentas (`blast_radius`, `eval_scorecard`, `audit_wiring`, `secret_scan`, `surgical_tests_plan`, `ast_symbols`), `protocolVersion="2024-11-05"`, `allow_mutations=False`; plugin declarado em `.agents/plugins/corporate-engineer/{plugin.json,mcp_config.json}`.
- **Honestidade de Execução**: `run_pipeline(dry_run=False, code_executor=None)` retorna `SIMULATED_NO_EXECUTOR` (bloqueia `DELIVER`, `exit 1`); `dry_run=True` sinaliza `is_simulated=True`; `SwarmCoordinator` marca papéis não implementados como `SKIPPED`; `fallback_reason` em `SystemOneReport`; `dubious ownership` git tratado sem cascata.
- **Hooks Enxutos**: `session_start.py` ≤600 chars via parsing regex de `state.md` (sem subprocessos `git`); `proactive_advisor.py` short-circuit `{}` em `invocationNum > 1`; `.agents/hooks.json` fallback `py → python3 → python` via `cmd /c`, `timeout: 15`.
- **Limpeza de `.agents/`**: zero refs legadas Claude Code em `.agents/workflows/`; registros alinhados com subagentes nativos Antigravity vs personas `.agents/agents/*.md`; `state.md` compactado de `~90 KB` → `<12 KB` ✅.
- **Pre-Flight Final** (verifier #19): **436/436 PASS** (239.31s), 0 erros Ruff (188 formatados), 0 erros Mypy (108 arquivos), 0 secrets, `audit --wiring` 49/49, MCP handshake `RC=0` 6 tools.

### Onda P3 (`IMP-0040` + `IMP-0041` / `ADR-035` — Imutabilidade Pydantic v2 & Curadoria de Skills):
- **Imutabilidade Estrita (`IMP-0040`)**: `_FrozenDTO(BaseModel)` com `ConfigDict(frozen=True)` aplicado a **55 modelos** em `src/corporate_engineer/models.py` (mantendo apenas `SwarmMember` e `AgentSpan` mutáveis); consumidores migrados para `model_copy(update=...)` em `graph.py`, `swarm.py`, `router.py` e `lora/validator.py`.
- **Curadoria `DAILY` vs `LIBRARY` (`IMP-0041`)**: mantidas **21 skills `DAILY`** em `.agents/skills/` e realocadas **310 skills `LIBRARY`** para `.agents/skills-library/`, com sincronização de `skills-registry.md` e `ecc-install-state.json`.
- **Qualidade**: [ADR-035](docs/adr/ADR-035-p3-frozen-dtos-and-skills-curation.md), 6 testes em `tests/test_p3_immutability_and_skills_curation.py` (**409/409 PASS**), consenso determinístico `APPROVED` (`92.34/100 Grade A`, `48/48` wired, `577` símbolos AST).

### Onda P2 (`IMP-0037` + `IMP-0038` + `IMP-0039` / `ADR-034` — SSE Real, Executores Plugáveis & Auditoria AST):
- **SSE Real (`IMP-0037`)**: `RemoteMCPSSEClient` (`src/corporate_engineer/mcp/client.py`) com parsing `application/json` e `text/event-stream`, casamento de `id` e rastreamento no `CircuitBreaker` (12 testes).
- **Executores Plugáveis (`IMP-0038`)**: protocolo `RoleExecutor` e analisadores determinísticos reais no `SwarmCoordinator`, além de `code_executor` e `execution_mode` em `AutonomousEngineeringGraph.run_pipeline()` (5 testes).
- **Wiring AST Real (`IMP-0039`)**: `CapabilityWiringAuditor` (`src/corporate_engineer/quality/wiring_auditor.py`) usando `TestASTReferences` em vez de busca textual por substring (6 testes; **403/403 PASS**).

### Onda P1 (`IMP-0032` + `IMP-0033` + `IMP-0036` / `ADR-033` — CLI/Hooks, RAG/LoRA & System-One):
- **Hooks & CLI (`IMP-0032`)**: dispatch dinâmico validado (`^[a-zA-Z0-9_]+$`) em `.agents/orchestration/hooks/run_hook.py`, validação de caminho em `rag eval`, subcomando obrigatório em `mcp`, e isolamento em `sys.stderr` para `--format json --output`.
- **RAG, LoRA & Refiner (`IMP-0033`)**: correção de *cache starvation* em `CachedASTCodebaseIndexer.get_all_symbol_names()`, suporte a generics TypeScript em `LoraSyntaxValidator` e mapeamento `cli/parser.py`/`cli/main.py` em `PromptRefiner`.
- **System-One (`IMP-0036`)**: acurácia sobre `total_runs` em `SystemOneBenchmark`, lazy-loading + `heuristic-fallback` transparente em `ONNXNLIDecisionEngine`, cache de instância em `OutlinesDecisionEngine` e exportação `optimum.onnxruntime` (**380/380 PASS**).

---

## 3. Roteiro Consolidado do Framework (Roadmap)

- `[x]` **Trilha 1 — CLI Modular (`src/corporate_engineer/cli/`)**: 20+ subcomandos (`run`, `audit`, `index`, `dag`, `mcp`, `eval`, `blast-radius`, `telemetry`, `test-surgical`, `decide`, `dataset`, `benchmark`, `swarm`, `prompt`, `lora`, `fix`, `clean`, `anticipate`, `dialectic`, `pr`).
- `[x]` **Trilha 2 — Conectores & Hub MCP (`src/corporate_engineer/mcp/`)**: `StdioMCPClient`, `RemoteMCPSSEClient`, `CircuitBreaker` e `MCPEnterpriseHub`.
- `[x]` **Trilha 3 — AST Indexing & Blast Radius (`src/corporate_engineer/rag/`)**: cache SHA-256 (`CachedASTCodebaseIndexer`), herança/call-graph, análise em lote (`BlastRadiusAnalyzer`) e PBT.
- `[x]` **Trilha 4 — Orquestração & Qualidade (`orchestrator/`, `quality/`, `eval/`)**: FSM/DAG com checkpoints e rollback, `SwarmCoordinator`, `AdversarialLoopCoordinator`, `MutationTestingEngine`, `SemanticCodeEvaluator`, `ASTSelfHealingFixer`, `CapabilityWiringAuditor` e `SafeStorageCleaner`.
- `[x]` **Trilha 5 — System-One & Observabilidade (`system_one/`, `telemetry/`)**: `SystemOneRouter` (Heuristic / Outlines / ONNX NLI), `SystemOneBenchmark`, `AgentTracer` com `ContextVar` OTel e pipeline LoRA.
- `[x]` **Trilha 6 — Corp-Pipeline & Governança (`.agents/`)**: regra `always_on`, 7 registros canônicos, 5 lifecycle hooks e curadoria `21 DAILY / 310 LIBRARY`.
- `[x]` **Trilha 7 — `IMP-0042` / `ADR-036` (IMPLEMENTADO)**: `CorporateEngineerMCPServer` (`mcp serve` + `.agents/plugins/corporate-engineer/`), hooks enxutos sem spam, workflows limpos de Claude Code e honestidade de execução na CLI (`SIMULATED_NO_EXECUTOR`, `SKIPPED`, `fallback_reason`, `dubious ownership`, wiring 49/49). **436/436 PASS** ✅.

---

## 4. Próximos Passos Imediatos

1. `[x]` ~~Finalizar implementação `IMP-0042`~~ — **IMPLEMENTADO** (Pre-Flight: **436/436 PASS**, wiring 49/49, MCP 6 tools, 0 erros Ruff/Mypy/Secrets).
2. `[ ]` Executar Gate 2: `git push -u origin feat/IMP-0040-p3-frozen-dtos-and-skills-curation` e abrir PR via link de [docs/pull_requests/PR-CORP-042.md](docs/pull_requests/PR-CORP-042.md).
3. `[ ]` Validar carregamento de `.agents/hooks.json` e plugin MCP em **Trusted Workspace** no Antigravity após merge.

---

## 5. Histórico Recente de Modificações do `state.md`

> Entradas anteriores a `2026-11-26T03:00:00-03:00` (`IMP-0035` / P0 e anteriores) estão arquivadas em [docs/history/state_archive_v1.md](docs/history/state_archive_v1.md).

| Data/Hora (ISO) | Autor | Resumo da Alteração |
|---|---|---|
| `2026-11-27T21:57:00-03:00` | `agents-cleaner` (`IMP-0042` Swarm — Turnover Final) | Métricas finais do Pre-Flight registradas: **436/436 PASS** (239.31s), 0 erros Ruff (188 arquivos), 0 erros Mypy (108 arquivos), 0 secrets, `audit --wiring` 49/49, MCP handshake `RC=0` / 6 tools. `IMP-0042` marcado `IMPLEMENTED` em `improvement-backlog.md`; `docs/pull_requests/PR-CORP-042.md` criado; Trilha 7 do roadmap marcada `[x]`. |
| `2026-11-27T21:15:00-03:00` | `agents-cleaner` (`IMP-0042` Swarm) | Compactação do `state.md` (`90,7 KB` → `<12 KB`) movendo sessões de `IMP-0035` e anteriores para `docs/history/state_archive_v1.md`; atualização de `session_start.py` (`<=600` chars), `proactive_advisor.py`, `.agents/hooks.json`, `.agents/workflows/`, `.agents/rules/corp-pipeline-orchestrator.md` e `.agents/orchestration/*-registry.md` conforme `ADR-036`. |
| `2026-11-27T19:49:00-03:00` | Corp-Pipeline Master Orchestrator (Swarm P3) | Onda P3 (`IMP-0040` + `IMP-0041` / `ADR-035`): `_FrozenDTO` em 55 modelos Pydantic v2, migração para `model_copy(update=...)`, curadoria `21 DAILY / 310 LIBRARY`. Pre-Flight: **409/409 PASS** (127.40s), 0 erros Ruff/Mypy/Secret Scan, `audit --wiring` PASS (`48/48`), consenso `APPROVED` (`92.34/100 Grade A`). |
| `2026-11-26T05:13:00-03:00` | Corp-Pipeline Master Orchestrator (Senior Swarm P2) | Onda P2 (`IMP-0037`–`IMP-0039` / `ADR-034`): SSE `text/event-stream` no `RemoteMCPSSEClient`, `RoleExecutor` + analisadores reais no `SwarmCoordinator`, `code_executor` em `run_pipeline()` e auditoria AST em `CapabilityWiringAuditor`. Pre-Flight: **403/403 PASS**, 0 erros Ruff/Mypy/Secret Scan. |
| `2026-11-26T03:03:00-03:00` | Corp-Pipeline Master Orchestrator (Swarm P1) | Onda P1 (`IMP-0032`, `IMP-0033`, `IMP-0036` / `ADR-033`): dispatch dinâmico em `run_hook.py`, CLI `sys.stderr` isolation, fix de cache AST, generics TS no validador LoRA e `heuristic-fallback` transparente no System-One. Pre-Flight: **380/380 PASS**, 0 erros Ruff/Mypy/Secret Scan. |
