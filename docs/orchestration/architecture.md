# Arquitetura do Sistema Corp-Pipeline Master Orchestrator

> **Documento de Arquitetura Técnica & Especificação de Sistema**  
> **Status**: Aprovado & Implementado  
> **Data**: 2026-11-19

---

## 1. Visão Geral Executiva

O **Corp-Pipeline Master Orchestrator** transforma o ecossistema `corporate-engineer` de um conjunto de scripts e agentes isolados em uma **camada de inteligência e orquestração de sistema permanente e auto-consciente**.

O objetivo primordial é libertar o usuário de ter que lembrar qual agente, skill, workflow, ferramenta ou regra deve ser acionado para cada demanda. O usuário apenas fornece o objetivo de negócio ou engenharia; o orquestrador descobre e administra os recursos que realmente existem no ambiente, planeja a execução, delega tarefas de forma cirúrgica e rigorosa, fiscaliza a qualidade e detecta continuamente melhorias para evolução da plataforma.

```text
                               ┌───────────────────────────────┐
                               │       Usuário / Prompt        │
                               └──────────────┬────────────────┘
                                              │
                                              ▼
                        ┌─────────────────────────────────────────────┐
                        │      CAMADA 1: CORE ORCHESTRATOR           │
                        │    (GEMINI.md, AGENTS.md, Rules)            │
                        │  Inteligência, Roteamento & Protocolo 6-Fases│
                        └─────────────────────┬───────────────────────┘
                                              │
                                              ▼
                        ┌─────────────────────────────────────────────┐
                        │    CAMADA 2: CAPABILITY INTELLIGENCE        │
                        │         (.agents/orchestration/)            │
                        │  Registros de Agentes, Skills, Workflows,   │
                        │  Ferramentas, MCPs e Backlog de Melhorias   │
                        └─────────────────────┬───────────────────────┘
                                              │
                                              ▼
                        ┌─────────────────────────────────────────────┐
                        │   CAMADA 3: EXECUTION & GOVERNANCE          │
                        │  Hooks (.agents/hooks.json), Quality Gates, │
                        │  state.md e Automação de Pull Requests      │
                        └─────────────────────────────────────────────┘
```

---

## 2. As Três Camadas Estruturais

### Camada 1: Core Orchestrator (Always-On)
- **Localização**: `GEMINI.md`, `AGENTS.md` e `.agents/rules/corp-pipeline-orchestrator.md`.
- **Comportamento**: Carregado de forma persistente e incondicional no início de qualquer interação no workspace.
- **Função**:
  - Intercepta qualquer demanda do usuário.
  - Executa as Fases 0 a 6 do ciclo Corp-Pipeline.
  - Aplica o protocolo de delegação e alocação de contexto.
  - Garante os princípios corporativos de KISS, DRY, YAGNI, Imutabilidade e Shift-Left TDD.

### Camada 2: Capability Intelligence (Registros Canônicos)
- **Localização**: `.agents/orchestration/`.
- **Arquivos**:
  - `capability-registry.md`: Matriz unificada de capacidades e tabela de decisão de roteamento.
  - `agent-registry.md`: Especificação dos 9 subagentes especialistas e subagentes nativos.
  - `skills-registry.md`: 13 skills essenciais (DAILY) e índice das 318 skills sob demanda (LIBRARY).
  - `workflow-registry.md`: Mapeamento dos 16 workflows determinísticos.
  - `tool-registry.md`: Ferramentas nativas do Antigravity, subcomandos da CLI Python e scripts.
  - `integration-registry.md`: Conectores MCP stdio/SSE, plugins do marketplace e remote git.
  - `improvement-backlog.md`: Repositório vivo de ideias e evoluções detectadas pelo orquestrador.

### Camada 3: Execution & Governance (Ciclo de Vida e Portões)
- **Localização**: `.agents/hooks.json`, `state.md`, `src/corporate_engineer/quality/`, `.agents/skills/corp-pipeline/scripts/`.
- **Comportamento**:
  - `SessionStart Hook`: Dispara script `session_start.py` para injetar o estado do projeto no início de cada nova sessão via contrato protojson nativo.
  - `Quality Gate (Pre-Flight)`: Fiscalização automática dos 4 testes fundamentais: `ruff check .`, `mypy .`, `pytest` e `secret_scanner.py`.
  - `Living State Tracking`: Manutenção ininterrupta de `state.md` como pulso vital do repositório.

---

## 3. O Ciclo de Execução em 6 Fases

Para cada requisição do usuário, o orquestrador executa o fluxo determinístico:

1. **FASE 0 — Context Initialization**:
   - Lê obrigatoriamente `state.md`.
   - Inspeciona o estado do workspace e status de git.
   - Recupera decisões arquiteturais prévias (`docs/adr/`).
2. **FASE 1 — Request Intelligence**:
   - Identifica objetivos primários, escopo, requisitos funcionais e não-funcionais.
   - Discrimina o que foi expressamente solicitado do que seria escopo excessivo.
3. **FASE 2 — Capability Discovery**:
   - Consulta os registros em `.agents/orchestration/`.
   - Verifica status de disponibilidade e permissões.
4. **FASE 3 — Intelligent Capability Routing**:
   - Seleciona o menor conjunto efetivo de recursos (agentes, skills, workflows, tools).
   - Evita delegações desnecessárias para tarefas triviais.
5. **FASE 4 — Execution & Multi-Agent Delegation**:
   - Aplica Shift-Left TDD.
   - Delega tarefas com pacote completo de restrições e critérios de aceite.
   - Mantém checkpoints de estado determinísticos.
6. **FASE 5 — Verification & Pre-Flight Gate**:
   - Executa a suíte de pre-flight com 0 tolerância a erros.
   - Apresenta evidências empíricas de teste e cobertura.
7. **FASE 6 — Continuous Improvement & Knowledge Preservation**:
   - Identifica oportunidades de evolução da arquitetura.
   - Apresenta no formato padrão `[CORP-PIPELINE / IMPROVEMENT DETECTED]`.
   - Atualiza `state.md` e registros correspondentes.

---

## 4. Separação Estrita de Governança de Melhorias

A característica crítica da inteligência proativa é a estrita separação entre 4 atos:

```text
[Descobrir Oportunidade]
           │
           ▼
[Apresentar Recomendação Padronizada com [SAVE FOR LATER] [DISMISS] [IMPLEMENT]]
           │
           ├──────────────────────────────┬──────────────────────────────┐
           ▼                              ▼                              ▼
    [SAVE FOR LATER]                  [DISMISS]                    [IMPLEMENT]
           │                              │                              │
           ▼                              ▼                              ▼
Persiste no Backlog            Descarta e não repete        Executa sob o Corp-Pipeline
(Status: SAVED_NOT_APPROVED)   inconvenientemente           (Fase 1 a Fase 5)
```

Nenhuma modificação arquitetural ou instalação não solicitada é realizada sem autorização formal do usuário.
