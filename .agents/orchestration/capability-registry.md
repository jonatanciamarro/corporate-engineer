# Corp-Pipeline Master Capability Registry (`capability-registry.md`)

> **Autonomous Capability Intelligence & Routing Registry**  
> *Authoritative mapping of Antigravity subagents, skills, workflows, CLI commands, and workspace MCP tools available in `corporate-engineer`.*

---

## 1. Visão Geral da Arquitetura

O **Corp-Pipeline** opera como a camada permanente de orquestração e inteligência do projeto. Este registro centraliza a descoberta de recursos reais do ambiente, estabelece a matriz de roteamento inteligente e mapeia as interfaces operacionais do ecossistema.

```text
                               [REQUISIÇÃO DO USUÁRIO]
                                          │
                                          ▼
                      ┌───────────────────────────────────────┐
                      │    Corp-Pipeline Master Orchestrator  │
                      │  (Planejamento, Roteamento & Gates)   │
                      └──────────────────┬────────────────────┘
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        ▼                                ▼                                ▼
┌──────────────┐                 ┌──────────────┐                 ┌──────────────┐
│  Subagentes  │                 │    Skills    │                 │  Workflows   │
│  Antigravity │                 │  Reutilizáveis│                │  Operacionais│
└───────┬──────┘                 └───────┬──────┘                 └───────┬──────┘
        │                                │                                │
        └────────────────────────────────┼────────────────────────────────┘
                                         ▼
                      ┌───────────────────────────────────────┐
                      │ CLI corporate-engineer & MCP Plugin   │
                      │ (.agents/plugins/corporate-engineer/) │
                      └──────────────────┬────────────────────┘
                                         │
                                         ▼
                             [Pre-Flight & Validação]
```

---

## 2. Matriz de Roteamento Inteligente

O orquestrador seleciona automaticamente a menor combinação efetiva de recursos para cada tarefa:

| Natureza da Tarefa | Recurso Primário | Recurso Secundário / Apoio | Validação Mandatória |
|---|---|---|---|
| **Exploração Read-Only de Código** | Subagente nativo `research` | Tools MCP `ast_symbols`, `blast_radius`; CLI `index` | Evidências exatas com caminhos e símbolos verificados |
| **Nova Feature Corporativa** | Skill `corp-pipeline` | Subagentes `research` / `self` / `swarm` com personas `.agents/agents/` | Gate 1 (ADR + Plano), TDD (`RED→GREEN`), Gate 2 |
| **Arquitetura & Contratos DTO** | Subagente `self` (`architect.md`) | Skills `grill-me_v2`, `plan_v2`, `api-design` | ADR em `docs/adr/` e `_FrozenDTO` em `models.py` |
| **Implementação & Testes TDD** | Subagente `self` (`tdd-guide.md`) | Skills `tdd-workflow`, `python-testing`; MCP `surgical_tests_plan` | Teste `RED` inicial, `GREEN`, cobertura `>=80%` |
| **Revisão de Código & Padrões** | Subagente `self` (`code-reviewer.md`, `python-reviewer.md`) | MCP `eval_scorecard`; skill `python-patterns` | `ruff check .`, `ruff format --check .`, `mypy .` |
| **Auditoria de Segurança & OWASP** | Subagente `self` (`security-reviewer.md`) | MCP `secret_scan`, `audit_wiring`; `secret_scanner.py` | 0 segredos expostos, confinamento de caminho, `shell=False` |
| **Indexação AST & Blast Radius** | MCP `ast_symbols`, `blast_radius` | CLI `index`, `blast-radius`; `rag-pipeline-reviewer.md` | PBT com Hypothesis e integridade de grafos |
| **Correção Rápida de Build/Testes** | Subagente `self` (`build-error-resolver.md`) | Workflow `build-fix.md`; `test-surgical` | Máximo 3 iterações cirúrgicas |
| **Refatoração Segura** | Subagente `self` (`refactor-cleaner.md`) | Workflow `orch-refine-code.md` | Preservação comportamental com suíte verde |
| **Ferramentas MCP do Workspace** | Plugin `.agents/plugins/corporate-engineer/` | CLI `mcp serve`, `mcp ping`, `mcp list-tools`, `mcp hub` | Handshake JSON-RPC 2.0 `stdio`, `allow_mutations=False` |
| **Pre-Flight & Auto-Wiring** | Workflow `preflight.md` | CLI `audit --strict --wiring`, `secret_scanner.py` | 0 erros em Pytest, Ruff, Mypy, Secrets e Wiring |

---

## 3. Classificação de Status Operacional

Cada capacidade catalogada possui um status operacional rigorosamente verificado:

- `AVAILABLE`: Testado e pronto para execução imediata no ambiente atual.
- `AVAILABLE_WITH_RESTRICTIONS`: Operacional com dependências ou limitações documentadas.
- `PERSONA_TEMPLATE`: Arquivo de instruções de papel em `.agents/agents/*.md` (requer `self`/`swarm`/`define_subagent`).
- `REQUIRES_AUTHENTICATION`: Necessita de tokens de autenticação ou chaves de API.
- `REQUIRES_APPROVAL`: Operação sensível que requer confirmação explícita do usuário (ex.: push, PR, mutações).
- `UNAVAILABLE`: Não suportado ou com dependência faltante no host.
- `DEPRECATED`: Mantido temporariamente para compatibilidade, com substituto designado.

---

## 4. Sub-Registros Especializados

Para detalhamento técnico completo de cada categoria de recursos, consulte os sub-registros:

1. [Subagentes Nativos e Personas](./agent-registry.md) (`agent-registry.md`)
2. [Skills e Conhecimento Reutilizável](./skills-registry.md) (`skills-registry.md`)
3. [Workflows e Pipelines](./workflow-registry.md) (`workflow-registry.md`)
4. [Ferramentas Nativas e CLI](./tool-registry.md) (`tool-registry.md`)
5. [Integrações, MCPs e Plugins](./integration-registry.md) (`integration-registry.md`)
6. [Backlog Contínuo de Melhorias](./improvement-backlog.md) (`improvement-backlog.md`)

---

## 5. Diretriz de Não-Suposição

O orquestrador **NUNCA** deve inventar nomes de ferramentas, subagentes inexistentes (como artefatos de Claude Code), arquivos de configuração ou status de execução. Toda capacidade deve ser descoberta, verificada e executada de acordo com as fronteiras reais do ambiente.
