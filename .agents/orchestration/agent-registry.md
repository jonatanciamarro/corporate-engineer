# Registro de Agentes Especializados (`agent-registry.md`)

> **Catálogo de Subagentes Nativos Antigravity & Personas de Papel do Workspace**  
> *Separação explícita entre subagentes executáveis nativos do runtime Antigravity e templates de persona em `.agents/agents/*.md`.*

---

## 1. Subagentes Nativos da Plataforma Antigravity (Executáveis via `invoke_subagent` / `swarm`)

Estes são os únicos identificadores de subagentes nativos disponíveis diretamente no runtime Antigravity sem declaração prévia via `define_subagent`:

| Identificador | Modelo Padrão | Status | Descrição de Uso |
|---|---|---|---|
| `research` | `inherit` | `AVAILABLE` | Subagente somente leitura para exploração profunda da base de código, documentações locais e pesquisa técnica. |
| `self` | `inherit` | `AVAILABLE` | Subagente com herança completa de ferramentas e permissões do agente principal, para execução isolada com foco ou persona dedicada. |
| `browser` | `flash` | `AVAILABLE_WITH_RESTRICTIONS` | Subagente navegador para interação com páginas web, dashboards visuais e workflows cliente. |
| `image-generator` | `inherit` | `AVAILABLE` | Geração e manipulação de diagramas e artefatos de imagem baseados em prompts visuais. |
| `swarm` | Multi-Agent | `AVAILABLE` | Orquestração paralela de múltiplos workers em quadro de mensagens compartilhado (`swarm` tool). |

> **Extensão Dinâmica**: Para instanciar um subagente especializado com nome customizado durante uma sessão, utilize primeiro `define_subagent` ou adicione um worker no `swarm` injetando o prompt da persona desejada de `.agents/agents/`.

---

## 2. Personas de Papéis do Workspace (`.agents/agents/*.md`) & `SwarmCoordinator`

Os arquivos `.agents/agents/*.md` são **templates de persona e checklists de especialidade** (não são nomes nativos pré-registrados para `invoke_subagent`). Em Python, `SwarmCoordinator` também suporta papéis com analisadores determinísticos reais e papéis que requerem `role_executor` / ferramentas MCP:

| Persona / Papel | Status em `invoke_subagent` | Execução em `SwarmCoordinator` (sem `role_executor`) | Propósito & Arquivo de Definição |
|---|---|---|---|
| `architect` | `PERSONA_TEMPLATE` (usar via `self` / `define_subagent`) | Analisador determinístico (`CapabilityWiringAuditor`) | Arquitetura, Pydantic v2 `_FrozenDTO`, trade-offs e ADRs ([architect.md](../agents/architect.md)) |
| `code-reviewer` | `PERSONA_TEMPLATE` (usar via `self` / `define_subagent`) | Analisador determinístico (`SemanticCodeEvaluator`) | Revisão geral, imutabilidade, padrões e scorecard AST ([code-reviewer.md](../agents/code-reviewer.md)) |
| `security-reviewer` | `PERSONA_TEMPLATE` (usar via `self` / `define_subagent`) | Analisador determinístico (`CanonicalSecretScanner`) | Auditoria OWASP, segredos, sanitização e least privilege ([security-reviewer.md](../agents/security-reviewer.md)) |
| `rag-pipeline-reviewer` | `PERSONA_TEMPLATE` (usar via `self` / `define_subagent`) | Analisador determinístico (`CachedASTCodebaseIndexer`) | Auditoria AST, grafos de herança, chamadas e code intelligence ([rag-pipeline-reviewer.md](../agents/rag-pipeline-reviewer.md)) |
| `planner` | `PERSONA_TEMPLATE` (usar via `self` / `define_subagent`) | Requer `role_executor` ou tools MCP (caso contrário `SKIPPED`) | Decomposição técnica por fases e PRDs ([planner.md](../agents/planner.md)) |
| `tdd-guide` | `PERSONA_TEMPLATE` (usar via `self` / `define_subagent`) | Requer `role_executor` ou tools MCP (caso contrário `SKIPPED`) | Ciclo Shift-Left TDD (`RED→GREEN→IMPROVE`) e PBT Hypothesis ([tdd-guide.md](../agents/tdd-guide.md)) |
| `python-reviewer` | `PERSONA_TEMPLATE` (usar via `self` / `define_subagent`) | Requer `role_executor` ou tools MCP (caso contrário `SKIPPED`) | Python 3.11+, `mypy`, `ruff`, PEP 8 e performance ([python-reviewer.md](../agents/python-reviewer.md)) |
| `build-error-resolver` | `PERSONA_TEMPLATE` (usar via `self` / `define_subagent`) | Requer `role_executor` ou tools MCP (caso contrário `SKIPPED`) | Diagnóstico e correção cirúrgica de falhas (limite: 3 tentativas) ([build-error-resolver.md](../agents/build-error-resolver.md)) |
| `refactor-cleaner` | `PERSONA_TEMPLATE` (usar via `self` / `define_subagent`) | Requer `role_executor` ou tools MCP (caso contrário `SKIPPED`) | Remoção de dead code preservando comportamento verde ([refactor-cleaner.md](../agents/refactor-cleaner.md)) |

---

## 3. Protocolo de Delegação e Hand-off

Toda delegação de subtarefa pelo Corp-Pipeline Master Orchestrator deve conter explicitamente:
1. **TASK**: Objetivo preciso e sem ambiguidades.
2. **CONTEXT**: Informações arquiteturais e decisões prévias relevantes.
3. **SCOPE**: Lista de arquivos que podem ou não ser modificados.
4. **INPUTS**: Contratos, dados ou referências de entrada.
5. **CONSTRAINTS**: Regras corporativas, restrições de imutabilidade e segurança.
6. **DELIVERABLES**: Saídas esperadas (código, testes, pareceres).
7. **VALIDATION**: Critérios de aceite e comandos de teste obrigatórios.
8. **REPORTING**: Sumário de evidências técnicas e riscos remanescentes.
