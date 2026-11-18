# Enterprise AI Software Engineering Framework

Repositório padronizado com governança corporativa para ciclo de vida de desenvolvimento de software impulsionado por IA (Agentic Software Engineering).

---

## 🧭 Skills Corporativas Integradas

Este repositório possui as seguintes skills ativas em `.agents/skills/`:

### 1. `corp-pipeline` (`/corp-pipeline`)
Pipeline determinístico de 5 fases para entrega corporativa:
- **Fase 1: Governança, Contratos & Escopo (Gate 1)**
  - **1.1 (`/grill-me_v2`)**: Entrevista adaptativa, extração de SLAs/NFRs e síntese de ADR em `docs/adr/ADR-<NUM>-<slug>.md`.
  - **1.2 (`/plan_v2`)**: Matriz de Trade-offs, Threat Modeling (STRIDE/OWASP), Rollback & Blast Radius e Contratos DTOs.
  - **1.3 (🔴 Gate 1)**: Validação humana explícita obrigatória antes do código.
- **Fase 2**: Shift-Left TDD com `stack_detector.py` (Certificação **RED**).
- **Fase 3**: Implementação Cirúrgica & Auto-recuperação (Certificação **GREEN**, máx 3 retentativas).
- **Fase 4**: Pre-Flight Gate & Auditoria Local (Linter, Typecheck, `secret_scanner.py`, Regressão Global).
- **Fase 5**: Entrega Corporativa (🔴 **Gate 2: Aprovação Final** → Branch `feat/<ID>-<slug>` & PR padronizado).

### 2. `plan_v2` (`/plan_v2`)
Protocolo de planejamento avançado com:
- Matriz de Trade-offs de Arquitetura (Mínimo 2 alternativas)
- Modelagem de Ameaças (STRIDE / OWASP)
- Estratégia de Rollback & Análise de Blast Radius
- Especificação formal de Contratos DTOs

### 3. `grill-me_v2` (`/grill-me_v2`)
Protocolo de entrevista investigativa baseado em:
- Árvore de Decisão Hierárquica
- Extração de Requisitos Não-Funcionais (SLAs, Throughput, Resiliência)
- Síntese Automática de **ADR (Architecture Decision Record)** formal em `docs/adr/`

---

## 🛠️ Scripts Utilitários

- **Detector de Stack**:
  ```powershell
  python .agents/skills/corp-pipeline/scripts/stack_detector.py [caminho]
  ```
  Identifica a stack técnica (Python, TS/Node, Go, Java/Kotlin, C#/.NET, Rust, PHP) e sugere os comandos adequados de teste, lint e typecheck.

- **Scanner de Segredos (Pre-Flight)**:
  ```powershell
  python .agents/skills/corp-pipeline/scripts/secret_scanner.py [caminho]
  ```
  Audita arquivos contra vazamento de credenciais, chaves de API e tokens sensíveis antes de qualquer commit.


  [corp-pipeline](slashCommand;corp-pipeline) agora me explique sobre os agentes, skills e workflows de orquestradores, ensine o antigravity a usalos em cada caso adequado, as melhores praticas nivel senior devem ser incorporadas nas regras do projeto, em todas as categorias [Quote](textBlock;label:Quote:Principais%20Categorias%20Instaladas%0AAgentic%20%26%20AI%20Engineering%3A%20agentic-engineering%2C%20agent-introspection-debugging%2C%20agent-architecture-audit%2C%20ai-regression-testing%2C%20unified-memory%2C%20verification-loop.%0ATesting%20%26%20TDD%3A%20tdd-workflow%2C%20test-collaboration%2C%20benchmark-methodology%2C%20module-regression.%0ASecurity%20%26%20Auditing%3A%20security-review%2C%20agent-security-hardening%2C%20web-perimeter-owasp-2025-audit.%0AArchitecture%20%26%20Standards%3A%20coding-standards%2C%20context-and-decisions%2C%20api-design%2C%20change-impact.%0AFrontend%20%26%20Backend%20Stacks%3A%20frontend-patterns%2C%20backend-patterns%2C%20bun-runtime%2C%20nextjs-turbopack%2C%20vue-patterns.%0AConsulte%20o%20documento%20completo%20com%20o%20%C3%ADndice%20de%20todas%20as%20skills%20em%20ecc-skills-catalog.md.) 
a minha ideia é criar um orquestrador que conhece todos os agentes, skills, apis, regras, workflows, plugins, mcp, conectores e ferramentas do projeto. esse orquestrador estará sempre ativo, e ele mantem/usa o padrao [corp-pipeline](slashCommand;corp-pipeline) sempre que eu mandar um prompt. portanto isso tudo sera feito de forma automatica nas regras, hooks, etc.. do projeto
ele é tambem pro ativo e se ele ver alguma possibilidade de melhoria ou transcendencia de alguma coisa ele sugere a melhoria, com a opção de salva-la para se quisermos implementar depois nao ser perdida.

---

## 📚 Documentação Adicional
- [Relatório Deep Research 2026](./deep-research-ai-software-engineering-2026.md): Estado da arte em agentes autônomos, MCP, A2A, segurança AI e testes mutation/PBT.
- [Decisões de Arquitetura (ADRs)](./docs/adr/): Histórico imutável de decisões de engenharia do projeto.
