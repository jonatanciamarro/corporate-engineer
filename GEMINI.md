# Project Instructions: Corporate Software Engineer

> Framework de Engenharia de Software Autônoma Corporativa (Enterprise AI Agentic Engineering).

---

## 1. Visão Geral & Arquitetura

O **corporate-engineer** é um framework corporativo para engenharia de software orientada a agentes com governança determinística.
- **Linguagem**: Python 3.10+ (target py311)
- **Pacotes Principais**: `pydantic>=2.0.0`, `pyyaml>=6.0.0`, `pytest>=8.0.0`, `hypothesis>=6.90.0`
- **Módulos do Sistema** (`src/corporate_engineer/`):
  - `mcp/`: Conectores e clientes MCP (Model Context Protocol) para stdio e SSE.
  - `orchestrator/`: Motor de orquestração de DAGs e grafos de agentes.
  - `quality/`: Quality gates, verificadores e regras de auditoria estática.
  - `rag/`: Indexador AST (Abstract Syntax Tree) e recuperação estruturada de código.
  - `models.py`: Esquemas e contratos DTO estritamente validados via Pydantic v2.
  - `cli.py`: Ponto de entrada CLI do sistema.

---

## 2. Comandos Operacionais Oficiais

| Operação | Comando |
|---|---|
| **Testes Unitários & PBT** | `pytest` ou `pytest -v` |
| **Cobertura de Testes** | `pytest --cov=src --cov-report=term-missing` |
| **Linter & Estilo** | `ruff check .` (comprimento de linha: 100) |
| **Formatador** | `ruff format --check .` |
| **Checagem Estática de Tipos** | `mypy .` |
| **Scanner de Segredos (Pre-Flight)**| `python .agents/skills/corp-pipeline/scripts/secret_scanner.py .` |
| **Detector de Stack** | `python .agents/skills/corp-pipeline/scripts/stack_detector.py .` |

---

## 3. Ecossistema ECC (Everything Claude Code) Configurado

Este repositório está configurado com o perfil **ECC Corporate Engineer** nativo para Antigravity:

### Workflows Ativos (`.agents/workflows/`)
Invoque via barra de comandos slash:
- `/corp-pipeline`: Pipeline corporativo em 5 fases com Gates 1 e 2.
- `/preflight`: Verificação completa de auditoria (Ruff, Mypy, Pytest e Secret Scanner).
- `/plan`: Planejamento arquitetural com matriz de trade-offs e modelagem STRIDE.
- `/review`: Revisão rigorosa de código, estilo e segurança.
- `/python-review`: Revisão focada em idioms Python, tipagem PEP 8 e performance.
- `/tdd`: Ciclo estrito de Test-Driven Development (Red-Green-Refactor).
- `/test-coverage`: Análise e relatório de cobertura de código.
- `/quality-gate`: Auditoria de conformidade corporativa.
- `/build-fix`: Recuperação cirúrgica e correção automática de falhas de build/lint.

### Subagentes Especializados (`.agents/agents/`)
- `architect`: Planejamento de arquitetura, contratos e ADRs (`model: pro`).
- `python-reviewer`: Revisão aprofundada de código Python e typehints (`model: pro`).
- `code-reviewer`: Revisão geral de PRs e conformidade (`model: pro`).
- `security-reviewer`: Análise de vulnerabilidades, OWASP e vazamentos (`model: pro`).
- `rag-pipeline-reviewer`: Auditoria específica para componentes RAG e AST (`model: pro`).
- `tdd-guide`: Condução de testes TDD e testes baseados em propriedades (`model: flash`).
- `build-error-resolver`: Diagnóstico rápido de erros de compilação/testes (`model: flash`).
- `refactor-cleaner`: Limpeza segura de código preservando comportamento (`model: flash`).

### Regras do Workspace Ativas (`.agents/rules/`)
- `state-tracking.md` (`trigger: always_on`): Protocolo obrigatório de leitura e atualização contínua do `state.md`.
- `corporate-quality-gate.md` (`trigger: always_on`): Portões de governança e invariantes corporativos.
- `common-coding-style.md`, `common-git-workflow.md`, `common-security.md`, `common-testing.md` (`trigger: always_on`).
- `python-coding-style.md`, `python-patterns.md`, `python-security.md` (`trigger: glob: **/*.py`).
- `python-testing.md` (`trigger: glob: tests/**/*.py,src/**/*.py`).

### Skills em Destaque (Daily Workflow)
- `corp-pipeline`, `grill-me_v2`, `plan_v2`: Governança corporativa, entrevista investigativa e ADRs.
- `python-patterns`, `python-testing`, `tdd-workflow`: Padrões avançados Python e testes.
- `security-review`, `api-design`, `mcp-server-patterns`: Segurança e integração MCP.
- *(318 skills adicionais disponíveis na biblioteca sob demanda via progressive disclosure).*

---

## 4. Invariantes de Engenharia & Governança

1. **Rastreamento de Estado (`state.md`) (CRÍTICO)**: O arquivo `state.md` DEVE ser lido no início de toda sessão para contextualização completa do projeto, e atualizado ao final de cada entrega com o que foi feito, pendências e próximos passos.
2. **Shift-Left TDD**: Toda alteração funcional ou correção de bug exige teste automatizado prévio em `tests/` que comprove a falha (RED) antes da implementação (GREEN).
3. **Modelos Pydantic V2**: Todos os contratos de dados devem ser tipados estritamente, sem uso de `dict` solto ou `Any` desnecessário.
4. **Decisões Arquiteturais Registradas (ADR)**: Qualquer mudança estrutural ou nova dependência deve ser documentada em `docs/adr/ADR-<NUM>-<slug>.md`.
5. **Pre-Flight Obrigatório**: Antes de qualquer commit ou entrega, é mandatório rodar `/preflight` (todos os 4 cheques devem passar com 0 erros).
6. **Padrão Git & Conventional Commits**: Branches no padrão `feat/<ID>-<slug>` ou `fix/<ID>-<slug>`. Commits seguindo a especificação convencional (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).
