# PR-CORP-042 -- feat(mcp,orchestrator,quality,agents): IMP-0042 -- Runtime Alignment, MCP Server Nativo & Honestidade CLI (ADR-036)

> **Branch**: feat/IMP-0040-p3-frozen-dtos-and-skills-curation
> **Base**: main
> **ADR**: ADR-036-runtime-alignment-mcp-server-and-cli-honesty.md
> **Data**: 2026-11-27
> **Pre-Flight Verifier**: APPROVED

## 1. Identificacao da Demanda

| Campo | Valor |
|---|---|
| ID | IMP-0042 |
| Categoria | ORCHESTRATION / ARCHITECTURE / CAPABILITY |
| Titulo | Runtime Alignment, MCP Server Nativo & Honestidade CLI |
| ADR | ADR-036 |
| Branch | feat/IMP-0040-p3-frozen-dtos-and-skills-curation |
| Swarm | tdd-author, mcp-engineer, cli-engineer, agents-cleaner, verifier |

## 2. Pre-Flight Final (verifier board #19)

| Check | Resultado | Detalhe |
|---|---|---|
| Pytest | PASS | 436 passed em 239.31s -- EXIT=0 |
| Ruff check | PASS | All checks passed! -- EXIT=0 |
| Ruff format | PASS | 188 files already formatted -- EXIT=0 |
| Mypy | PASS | 0 issues in 108 source files -- EXIT=0 |
| Secret Scanner | PASS | 0 secrets -- EXIT=0 |
| CLI Wiring Audit | PASS | 49/49 modulos conectados |
| MCP Handshake | PASS | RC=0, 6 tools, protocolVersion=2024-11-05 |
| state.md size | PASS | <12 KB |
| Workflows legados | PASS | 0 hits |

## 3. Pilares Implementados

**Pilar 1** - CorporateEngineerMCPServer (mcp/server.py): 6 tools stdio JSON-RPC 2.0 (blast_radius, eval_scorecard, audit_wiring, secret_scan, surgical_tests_plan, ast_symbols), protocolVersion=2024-11-05, allow_mutations=False. Plugin em .agents/plugins/corporate-engineer/.

**Pilar 2** - Hooks Enxutos: session_start.py <=600 chars via regex em state.md; proactive_advisor.py short-circuit {} em invocationNum>1; .agents/hooks.json fallback py->python3->python via cmd /c, timeout:15.

**Pilar 3** - Honestidade em graph.py & swarm.py: run_pipeline sem code_executor -> SIMULATED_NO_EXECUTOR, bloqueia DELIVER; SwarmCoordinator marca roles sem role_executor como SKIPPED.

**Pilar 4** - System-One & Adversarial: SystemOneReport.fallback_reason; warnings nao-silenciosos em RunExecutionReport.

**Pilar 5** - Git Dubious Ownership: `git_utils.py` & `surgical_runner.py` detectam `dubious ownership` (exit 128) via `_is_dubious_ownership_error` e `_summarize_git_stderr` sem cascade para `git diff` (exit 129). Nao usam `-c safe.directory=*`.

**Pilar 6** - CapabilityWiringAuditor: valida cli/parser.py, cli/main.py, PromptRefiner.DOMAIN_KEYWORDS; 49/49.

**Pilar 7** - Limpeza .agents/: zero refs Claude Code em workflows; state.md 90KB-><12 KB; historia arquivada em docs/history/state_archive_v1.md.

## 4. TDD Evidence

RED: test_mcp_server_and_plugin.py (14 falhas) + test_runtime_honesty_and_wiring.py (13 falhas) CONFIRMADOS antes da implementacao.
GREEN: 436/436 PASS.
REFACTOR: test_concurrency_thread_safety.py alinhado com contrato SKIPPED/COMPLETED.

## 5. Pre-Flight Verifier

tdd-author: PASS | mcp-engineer: PASS | cli-engineer: PASS | agents-cleaner: PASS | verifier: APPROVED
Resultado: APPROVED -- prontos para Gate 2 (git push + PR).
