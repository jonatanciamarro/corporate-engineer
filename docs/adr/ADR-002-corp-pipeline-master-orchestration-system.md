# ADR-002: Implementação do Corp-Pipeline Master Orchestration System

> **Status**: ACEITO (ACCEPTED)  
> **Data**: 2026-11-19  
> **Decisores**: Chief Orchestrator Architect, Antigravity AI  
> **Contexto Técnico**: Evolução do framework `corporate-engineer` para adotar uma camada perene de inteligência, governança e orquestração multi-agente.

---

## 1. Contexto & Problema

Anteriormente, o `corp-pipeline` existia no repositório primordialmente como uma skill e um workflow disparado sob demanda (`/corp-pipeline`). Embora os subagentes e regras estivessem presentes, o usuário ainda precisava lembrar explicitamente quais ferramentas e fluxos invocar. Além disso, ideias e oportunidades de melhoria arquitetural corriam o risco de serem implementadas sem aprovação ou perdidas entre sessões de desenvolvimento.

Havia a necessidade de consolidar o **Corp-Pipeline como uma camada permanente de orquestração**, ativa em todos os prompts, capaz de:
1. Conhecer e descobrir o ecossistema real de agentes, skills, workflows, MCPs, APIs e regras.
2. Selecionar dinamicamente a combinação ideal de capacidades para qualquer tarefa.
3. Reter e governar propostas de melhoria contínua com separação estrita entre descobrir, recomendar, salvar e implementar.
4. Integrar hooks de ciclo de vida nativos do Antigravity (`SessionStart`) sem depender de ferramentas fictícias.

---

## 2. Decisão Arquitetural

Decidiu-se adotar o **Corp-Pipeline Master Orchestrator** estruturado em três camadas permanentes:

1. **Camada 1 — Core Orchestrator (Always-On)**:
   - Fixado em `GEMINI.md`, `AGENTS.md` e na regra persistente `.agents/rules/corp-pipeline-orchestrator.md`.
   - Estabelece o ciclo em 6 fases: Context Initialization → Request Intelligence → Capability Discovery → Capability Routing → Execution & Delegation → Pre-Flight Verification → Improvement & State.
2. **Camada 2 — Capability Intelligence (Registros Canônicos)**:
   - Criação da pasta canônica `.agents/orchestration/` contendo:
     - `capability-registry.md`: Matriz de roteamento e índice unificado.
     - `agent-registry.md`: Mapeamento dos 9 subagentes especialistas e nativos.
     - `skills-registry.md`: 13 skills diárias e 318 skills em progressive disclosure.
     - `workflow-registry.md`: 16 workflows operacionais.
     - `tool-registry.md`: Ferramentas nativas do Antigravity, subcomandos CLI e scripts utilitários.
     - `integration-registry.md`: Clientes MCP stdio/SSE e conectores.
     - `improvement-backlog.md`: Repositório de melhorias com ciclo formal de status.
3. **Camada 3 — Execution & Governance**:
   - Criação de `.agents/hooks.json` com hook nativo `SessionStart` acionando script determinístico em `.agents/orchestration/hooks/session_start.py`.
   - Preservação estrita dos gates de pre-flight (Ruff, Mypy, Pytest, Secret Scanner).

---

## 3. Matriz de Trade-offs & Alternativas Consideradas

| Critério | Opção A: Prompt Único Gigante (Monolítico) | Opção B: Agente Especialista Isolado (Status Quo) | Opção C: Arquitetura em 3 Camadas com Registros (Escolhida) |
|---|---|---|---|
| **Consumo de Contexto** | Ruim (estoura tokens com todas as instruções a cada turno). | Médio (mas perde visibilidade do ecossistema geral). | **Excelente** (Progressive disclosure e registros modulares sob demanda). |
| **Persistência Entre Sessões** | Nula (depende de memória efêmera da conversa). | Baixa. | **Máxima** (Registros em markdown versionados e `state.md`). |
| **Governança de Melhorias** | Caótica (risco de alucinar ou aplicar sem autorização). | Inexistente. | **Rigorosa** (Fluxo padronizado com aprovação explícita do usuário). |
| **Aderência ao Antigravity** | Baixa. | Média. | **Nativa** (Usa regras `always_on`, hooks `.agents/hooks.json` e protojson). |

---

## 4. Análise de Segurança & Blast Radius (STRIDE)

- **Spoofing / Tampering**: Registros versionados no Git impedem alterações arbitrárias ou alucinações de ferramentas que não existem no projeto.
- **Elevation of Privilege**: O hook `SessionStart` apenas lê metadados públicos e o `state.md`; nenhuma execução arbitrária de código privilegiado é permitida sem Gate 2.
- **Information Disclosure**: Scanner de segredos corporativo protege contra qualquer vazamento em arquivos de log, registros ou documentação.

---

## 5. Consequências & Próximos Passos

### Positivas:
- O ecossistema agora é totalmente auto-consciente.
- Nenhuma ideia ou proposta de evolução é perdida ou implementada unilateralmente.
- Inicialização de sessão automatizada via hook nativo.

### Próximos Passos:
- Submeter e validar as primeiras propostas salvas no backlog (`IMP-0001` a `IMP-0005`) conforme priorização do usuário.
