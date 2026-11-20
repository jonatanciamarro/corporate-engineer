# Project Instructions: Corporate Software Engineer & Corp-Pipeline Master Orchestrator

> **Framework de Engenharia de Software Autônoma Corporativa (Enterprise AI Agentic Engineering)**  
> **Padrão Operacional Obrigatório**: Corp-Pipeline Master Orchestration System  
> **Filosofia de Execução**: Planejar Inteligentemente → Delegar Estrategicamente → Executar com Confiabilidade → Verificar Rigorosamente → Melhorar Continuamente

---

## 1. O Orquestrador Corp-Pipeline (Always-On)

O **Corp-Pipeline** não é apenas um agente ou comando isolado: ele é a **camada permanente de inteligência, governança e orquestração** de todo o projeto `corporate-engineer`.
- **Ativação Padrão**: Qualquer prompt ou tarefa submetida pelo usuário é automaticamente processada através do ciclo do Corp-Pipeline (Fases 0 a 6).
- **Três Camadas da Arquitetura**:
  1. **Core Orchestrator**: Regras persistentes, identidade sênior, inteligência de requisição, roteamento enxuto e protocolo de delegação.
  2. **Capability Intelligence**: Registros estruturados em `.agents/orchestration/` que mapeiam agentes, skills, workflows, ferramentas e MCPs sem depender de memória efêmera.
  3. **Execution & Governance**: Hooks de ciclo de vida (`.agents/hooks.json`), portões de qualidade, estado vivo (`state.md`) e backlog contínuo de melhorias (`improvement-backlog.md`).

---

## 2. Visão Geral & Arquitetura do Código

- **Linguagem**: Python 3.10+ (Target: py311)
- **Pacotes Principais**: `pydantic>=2.0.0`, `pyyaml>=6.0.0`, `pytest>=8.0.0`, `hypothesis>=6.90.0`
- **Módulos do Sistema** (`src/corporate_engineer/`):
  - `mcp/`: Conectores e clientes MCP (Model Context Protocol) para stdio e SSE com Bearer auth.
  - `orchestrator/`: Motor de orquestração de DAGs, execução paralela de nós e checkpoints determinísticos.
  - `quality/`: Quality gates, verificadores e regras de auditoria estática e credenciais.
  - `rag/`: Indexador AST (Abstract Syntax Tree) para extração de classes, herança, imports e call graphs.
  - `models.py`: Esquemas e contratos DTO estritamente validados via Pydantic v2.
  - `cli.py`: Ponto de entrada CLI corporativa com subcomandos `audit`, `index`, `dag` e `mcp`.

---

## 3. Comandos Operacionais Oficiais

| Operação | Comando Oficial (Ambiente Virtual Recomendado) |
|---|---|
| **Testes Unitários & PBT** | `.venv\Scripts\pytest` (ou `pytest`) |
| **Cobertura de Testes** | `.venv\Scripts\pytest --cov=src --cov-report=term-missing` |
| **Linter & Estilo** | `.venv\Scripts\ruff check .` (comprimento de linha: 100) |
| **Formatador** | `.venv\Scripts\ruff format --check .` |
| **Checagem Estática de Tipos** | `.venv\Scripts\mypy .` |
| **Scanner de Segredos (Pre-Flight)**| `.venv\Scripts\python .agents/skills/corp-pipeline/scripts/secret_scanner.py .` |
| **Detector de Stack** | `.venv\Scripts\python .agents/skills/corp-pipeline/scripts/stack_detector.py .` |
| **CLI do Framework** | `.venv\Scripts\python -m corporate_engineer.cli <subcomando>` |

---

## 4. Ecossistema ECC & Registros de Capacidades

O ecossistema está organizado e mapeado em registros canônicos:

### Registros Centrais (`.agents/orchestration/`):
- `capability-registry.md`: Matriz de decisão de roteamento inteligente e catálogo unificado.
- `agent-registry.md`: Subagentes especializados (`architect`, `planner`, `tdd-guide`, `code-reviewer`, `python-reviewer`, `security-reviewer`, `rag-pipeline-reviewer`, `build-error-resolver`, `refactor-cleaner`) e nativos.
- `skills-registry.md`: 13 skills diárias (DAILY) e índice das 318 skills sob demanda (LIBRARY).
- `workflow-registry.md`: 16 workflows operacionais determinísticos.
- `tool-registry.md`: Ferramentas nativas do Antigravity, comandos CLI e scripts utilitários.
- `integration-registry.md`: Clientes MCP stdio/SSE, plugins do marketplace e remote git.
- `improvement-backlog.md`: Repositório de melhorias com separação estrita entre descobrir, recomendar, salvar e implementar.

### Regras do Workspace Ativas (`.agents/rules/`):
- `corp-pipeline-orchestrator.md` (`always_on`): Protocolo mestre do orquestrador e ciclo em 6 fases.
- `state-tracking.md` (`always_on`): Leitura obrigatória do `state.md` no início e atualização ao final.
- `corporate-quality-gate.md` (`always_on`): Invariantes corporativos e gates obrigatórios.
- `common-coding-style.md`, `common-development-workflow.md`, `common-git-workflow.md`, `common-security.md`, `common-testing.md`.
- `python-coding-style.md`, `python-patterns.md`, `python-security.md`, `python-testing.md`.

---

## 5. Invariantes de Engenharia & Governança

1. **Rastreamento de Estado (`state.md`) (CRÍTICO)**: O arquivo `state.md` DEVE ser lido no início de toda sessão para contextualização completa do projeto, e atualizado ao final de cada entrega com o que foi feito, pendências e próximos passos.
2. **Shift-Left TDD**: Toda alteração funcional ou correção de bug exige teste automatizado prévio em `tests/` que comprove a falha (RED) antes da implementação (GREEN).
3. **Modelos Pydantic V2**: Todos os contratos de dados devem ser tipados estritamente, sem uso de `dict` solto ou `Any` desnecessário.
4. **Decisões Arquiteturais Registradas (ADR)**: Qualquer mudança estrutural ou nova dependência deve ser documentada em `docs/adr/ADR-<NUM>-<slug>.md`.
5. **Pre-Flight Obrigatório**: Antes de qualquer commit ou entrega, é mandatório rodar `/preflight` (todos os 4 cheques devem passar com 0 erros).
6. **Governança de Melhorias**: NUNCA aplicar melhorias não solicitadas sem aprovação. Apresentar formato padrão `[CORP-PIPELINE / IMPROVEMENT DETECTED]` e oferecer salvamento no backlog.
7. **Padrão Git & Conventional Commits**: Branches no padrão `feat/<ID>-<slug>` ou `fix/<ID>-<slug>`. Commits seguindo a especificação convencional (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`).
8. **Push Remoto Pré-PR Mandatório (Always-On)**: O envio da branch para o remote no GitHub (`git push -u origin <branch>`) DEVE OBRIGATORIAMENTE anteceder a geração, formatação ou apresentação de qualquer link de PR. O framework e o orquestrador NUNCA devem emitir links de PR para branches locais não sincronizadas (garantindo zero erros 404 no GitHub).

