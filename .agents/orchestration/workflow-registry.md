# Registro de Workflows Operacionais (`workflow-registry.md`)

> **Catálogo de Workflows Determinísticos do Workspace**  
> *Mapeamento dos 16 workflows padronizados disponíveis em `.agents/workflows/`, alinhados ao runtime Antigravity e à CLI/MCP `corporate-engineer`.*

---

## 1. Workflows de Governança, Qualidade & Pre-Flight

| Workflow | Slash Command | Finalidade | Portões / Ferramentas Reais | Arquivo de Definição |
|---|---|---|---|---|
| `preflight` | `/preflight` | Auditoria completa de pre-flight local: Ruff, Mypy, Pytest e Secret Scanner. | 0 erros em todos os cheques via `.venv`. | [.agents/workflows/preflight.md](../workflows/preflight.md) |
| `quality-gate` | `/quality-gate` | Auditoria estática, scorecard AST, formatação e auto-wiring corporativo. | CLI `audit --strict --wiring`, `eval`, MCP `eval_scorecard` & hooks `run_hook.py`. | [.agents/workflows/quality-gate.md](../workflows/quality-gate.md) |
| `security-scan` | `/security-scan` | Auditoria de segredos, injeção de comandos, path traversal e MCP least privilege. | `secret_scanner.py`, `audit --strict --wiring`, MCP `secret_scan` & persona `security-reviewer.md`. | [.agents/workflows/security-scan.md](../workflows/security-scan.md) |
| `test-coverage` | `/test-coverage` | Análise e relatório de cobertura de código (`pytest --cov=src`). | Cobertura global mínima de 80% (meta: 90%+). | [.agents/workflows/test-coverage.md](../workflows/test-coverage.md) |

---

## 2. Workflows de Ciclo de Vida e Entrega de Software

| Workflow | Finalidade | Sequência Operacional | Arquivo de Definição |
|---|---|---|---|
| `feature-dev` | Desenvolvimento ponta a ponta de novas funcionalidades corporativas. | `state.md` → `research` + MCP AST → Gate 1 (ADR/`plan_v2`) → TDD `RED→GREEN` → Pre-Flight → Gate 2 (PR). | [.agents/workflows/feature-dev.md](../workflows/feature-dev.md) |
| `orch-add-feature` | Orquestração multi-agente para novas features, delegando pesquisa, TDD e revisão. | Delegação estruturada com isolamento de contexto e checkpoints. | [.agents/workflows/orch-add-feature.md](../workflows/orch-add-feature.md) |
| `orch-fix-defect` | Correção determinística de defeitos e bugs reportados. | Reprodução em teste regressivo (`RED`) → correção (`GREEN`) → revisão (`self`). | [.agents/workflows/orch-fix-defect.md](../workflows/orch-fix-defect.md) |
| `orch-refine-code` | Refatoração arquitetural com garantia matemática de não-regressão. | Testes verdes antes da refatoração → alteração estrutural → testes verdes mantidos. | [.agents/workflows/orch-refine-code.md](../workflows/orch-refine-code.md) |
| `build-fix` | Recuperação cirúrgica e autocorreção de falhas de build/lint/testes. | Diagnóstico de traceback → isolamento → máximo de 3 tentativas cirúrgicas. | [.agents/workflows/build-fix.md](../workflows/build-fix.md) |
| `checkpoint` | Inspeção de checkpoints FSM do DAG e snapshots Git / `state.md`. | CLI `dag --checkpoints`, `run --dry-run` e `git -c "safe.directory=*" stash`. | [.agents/workflows/checkpoint.md](../workflows/checkpoint.md) |

---

## 3. Workflows de Planejamento, Revisão e Documentação

| Workflow | Slash Command | Finalidade | Arquivo de Definição |
|---|---|---|---|
| `plan` | `/plan` | Planejamento técnico com `plan_v2`, `docs/adr/`, STRIDE e contratos `_FrozenDTO`. | [.agents/workflows/plan.md](../workflows/plan.md) |
| `review` | `/review` | Revisão sênior local ou de PR usando CLI/MCP, `AGENTS.md`, `docs/adr/` e `docs/pull_requests/`. | [.agents/workflows/review.md](../workflows/review.md) |
| `python-review` | `/python-review` | Revisão técnica especializada em Python 3.11+, tipos estritos (`mypy`), `ruff` e PEP 8. | [.agents/workflows/python-review.md](../workflows/python-review.md) |
| `refactor-clean` | `/refactor-clean` | Higienização de imports, remoção de dead code e alinhamento com padrões PEP 8. | [.agents/workflows/refactor-clean.md](../workflows/refactor-clean.md) |
| `update-docs` | `/update-docs` | Sincronização perene de documentação técnica, ADRs e histórico de decisões. | [.agents/workflows/update-docs.md](../workflows/update-docs.md) |
| `ecc-guide` | `/ecc-guide` | Guia operacional interativo da superfície real do repositório (`AGENTS.md`, `.agents/`). | [.agents/workflows/ecc-guide.md](../workflows/ecc-guide.md) |

---

## 4. Invariantes de Execução

1. **Nunca executar workflows cegamente**: O orquestrador deve checar os pré-requisitos e dependências reais antes de disparar um workflow.
2. **Respeitar os Gates Humanos**: Workflows com confirmação explícita (Gate 1 e Gate 2) jamais devem prosseguir sem autorização do usuário.
3. **Sem Artefatos Fantasmas**: Nenhum workflow deve referenciar diretórios ou executáveis legados de Claude Code (`.claude/`, `scripts/hooks/quality-gate.js`, `ecc-agentshield`).
