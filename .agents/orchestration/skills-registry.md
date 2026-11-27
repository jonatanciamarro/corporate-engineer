# Registro de Skills do Ecossistema (`skills-registry.md`)

> **Catálogo Curado de Conhecimento e Procedimentos Reutilizáveis (`IMP-0041` / `ADR-035`)**  
> *Separação estrita entre 21 skills `DAILY` ativas em `.agents/skills/` e 310 skills `LIBRARY` sob demanda em `.agents/skills-library/`.*

---

## 1. Skills de Operação Diária (DAILY Core Skills — `.agents/skills/`)

Estas 21 skills foram selecionadas e perfiladas por evidência do repositório (`agent-sort` + workflows ativos) especificamente para o stack Python 3.11 / Pydantic v2 / TDD / Segurança / MCP / AST / Corp-Pipeline do `corporate-engineer`:

| Skill | Status | Finalidade Operacional | Gatilho / Invocação | Localização |
|---|---|---|---|---|
| `corp-pipeline` | `AVAILABLE` | Pipeline corporativo em 5 fases com Gate 1 (Escopo/ADR), TDD, Auto-debug, Pre-Flight e Gate 2 (PR). | `/corp-pipeline` | [.agents/skills/corp-pipeline](../skills/corp-pipeline/SKILL.md) |
| `grill-me_v2` | `AVAILABLE` | Entrevista investigativa e hierárquica para descoberta de requisitos e geração formal de ADRs. | `/grill-me_v2` | [.agents/skills/grill-me_v2](../skills/grill-me_v2/SKILL.md) |
| `plan_v2` | `AVAILABLE` | Planejamento técnico corporativo com Matriz de Trade-offs, STRIDE e contratos DTO tipados. | `/plan_v2` | [.agents/skills/plan_v2](../skills/plan_v2/SKILL.md) |
| `python-patterns` | `AVAILABLE` | Padrões idiomáticos de Python 3.10/3.11, tipagem rigorosa, PEP 8 e arquitetura limpa. | Contexto Python | [.agents/skills/python-patterns](../skills/python-patterns/SKILL.md) |
| `python-testing` | `AVAILABLE` | Estratégias de teste com Pytest, fixtures, mocks, parametrização e cobertura. | Contexto de Testes | [.agents/skills/python-testing](../skills/python-testing/SKILL.md) |
| `tdd-workflow` | `AVAILABLE` | Metodologia rigorosa Test-Driven Development (Red-Green-Refactor) com 80%+ cobertura. | `/tdd` | [.agents/skills/tdd-workflow](../skills/tdd-workflow/SKILL.md) |
| `security-review` | `AVAILABLE` | Checklist corporativo de segurança: segredos, sanitização, autenticação e autorização. | `/security-scan` | [.agents/skills/security-review](../skills/security-review/SKILL.md) |
| `security-scan` | `AVAILABLE` | Auditoria e varredura operacional de segurança alinhada ao workflow `security-scan.md`. | `/security-scan` | [.agents/skills/security-scan](../skills/security-scan/SKILL.md) |
| `api-design` | `AVAILABLE` | Padrões de design de APIs RESTful, contratos DTO e tratamento padronizado de erros. | Design de Interfaces | [.agents/skills/api-design](../skills/api-design/SKILL.md) |
| `mcp-server-patterns` | `AVAILABLE` | Padrões para clientes e servidores MCP: stdio, SSE, schemas de ferramentas e validação. | Módulo MCP | [.agents/skills/mcp-server-patterns](../skills/mcp-server-patterns/SKILL.md) |
| `agentic-engineering` | `AVAILABLE` | Engenharia orientada a agentes com decomposição de tarefas e execução orientada a evals. | Orquestração | [.agents/skills/agentic-engineering](../skills/agentic-engineering/SKILL.md) |
| `conventional-commit-review` | `AVAILABLE` | Auditoria de diffs para redação de commits semânticos no padrão Conventional Commits. | Pré-commit | [.agents/skills/conventional-commit-review](../skills/conventional-commit-review/SKILL.md) |
| `verification-loop` | `AVAILABLE` | Ciclo contínuo de verificação pós-implementação com checagem estática e dinâmica. | Pós-implementação | [.agents/skills/verification-loop](../skills/verification-loop/SKILL.md) |
| `agent-sort` | `AVAILABLE` | Auditoria e perfilamento de repositório para distribuição de skills DAILY vs LIBRARY. | `/agent-sort` | [.agents/skills/agent-sort](../skills/agent-sort/SKILL.md) |
| `ecc-guide` | `AVAILABLE` | Guia canônico do ecossistema ECC consultando a superfície real do repositório. | Workflow `ecc-guide` | [.agents/skills/ecc-guide](../skills/ecc-guide/SKILL.md) |
| `orch-add-feature` | `AVAILABLE` | Orquestração ponta a ponta de nova funcionalidade via agentes especializados. | Workflow `orch-add-feature` | [.agents/skills/orch-add-feature](../skills/orch-add-feature/SKILL.md) |
| `orch-change-feature` | `AVAILABLE` | Alteração de comportamento existente com atualização prévia de especificações e testes. | Orquestração | [.agents/skills/orch-change-feature](../skills/orch-change-feature/SKILL.md) |
| `orch-fix-defect` | `AVAILABLE` | Correção de defeitos com reprodução em teste regressivo falhando (RED→GREEN). | Workflow `orch-fix-defect` | [.agents/skills/orch-fix-defect](../skills/orch-fix-defect/SKILL.md) |
| `orch-refine-code` | `AVAILABLE` | Refatoração preservando comportamento sob suíte verde contínua. | Workflow `orch-refine-code` | [.agents/skills/orch-refine-code](../skills/orch-refine-code/SKILL.md) |
| `architecture-decision-records` | `AVAILABLE` | Padronização formal de ADRs em `docs/adr/ADR-<NUM>-<slug>.md`. | Governança | [.agents/skills/architecture-decision-records](../skills/architecture-decision-records/SKILL.md) |
| `content-hash-cache-pattern` | `AVAILABLE` | Padrão de cache incremental baseado em hash SHA-256 utilizado pelo `CachedASTCodebaseIndexer`. | Módulo RAG/AST | [.agents/skills/content-hash-cache-pattern](../skills/content-hash-cache-pattern/SKILL.md) |

---

## 2. Catálogo de Skills da Biblioteca Sob Demanda (LIBRARY — `.agents/skills-library/`)

O repositório preserva **310 skills adicionais** sob demanda em [`.agents/skills-library/`](../skills-library/) (fora do diretório auto-carregado `.agents/skills/`), evitando sobrecarga de orçamento de contexto e ruído visual sem perda de capacidade.

### Principais Domínios Disponíveis Sob Demanda:
1. **Engenharia de Backend & APIs**:
   - `fastapi-patterns`, `django-patterns`, `django-celery`, `django-tdd`, `nestjs-patterns`, `springboot-patterns`, `springboot-tdd`, `golang-patterns`, `golang-testing`, `rust-patterns`, `rust-testing`, `dotnet-patterns`.
2. **Dados, Persistência & Bancos**:
   - `postgres-patterns`, `mysql-patterns`, `redis-patterns`, `clickhouse-io`, `jpa-patterns`, `kotlin-exposed-patterns`, `database-migrations`.
3. **Qualidade, Testes & E2E**:
   - `e2e-testing`, `react-testing`, `csharp-testing`, `cpp-testing`, `godot-testing`, `windows-desktop-e2e`.
4. **Segurança & Conformidade**:
   - `security-bounty-hunter`, `hipaa-compliance`, `django-security`, `laravel-security`, `defi-amm-security`, `prediction-market-risk-review`.
5. **Automação, Multi-Agente & LLM Ops**:
   - `continuous-agent-loop`, `autonomous-loops`, `devfleet`, `dmux-workflows`, `cost-aware-llm-pipeline`, `cost-tracking`, `eval-harness`, `gan-style-harness`.
6. **Infraestrutura, Redes & DevOps**:
   - `deployment-patterns`, `kubernetes-patterns`, `docker-patterns`, `terraform-patterns`, `canary-watch`, `cisco-ios-patterns`, `netmiko-ssh-automation`, `network-bgp-diagnostics`.

---

## 3. Diretriz de Progressive Disclosure & Economia de Contexto

- Somente as **21 skills `DAILY`** residem em `.agents/skills/` para carregamento imediato.
- Qualquer skill `LIBRARY` pode ser consultada sob demanda diretamente em `.agents/skills-library/<nome-da-skill>/SKILL.md` ou promovida via `agent-sort` caso o stack do projeto se expanda.
