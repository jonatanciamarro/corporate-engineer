# ADR-001: Arquitetura do Engenheiro Autônomo Corporativo Open-Source

- **Status**: Aceito
- **Data**: 2026-11-18
- **Autores / Decisores**: Usuário & Antigravity Lead Architect
- **Ticket / Contexto**: Implementação do Engenheiro Autônomo Corporativo baseado no relatório Deep Research 2026

---

## 1. Contexto e Declaração do Problema
O desenvolvimento de software moderno exige ir além de ferramentas de autocompletar e chat em IDE. As empresas enfrentam um gargalo crítico na revisão, validação, testes e governança de código gerado por IA. O objetivo desta iniciativa é construir um **Engenheiro de Software Autônomo de nível Sênior**, 100% alinhado com ferramentas **Open-Source**, capaz de receber demandas corporativas, planejar, escrever testes (TDD), implementar código cirurgicamente, passar por quality gates e interagir com repositórios e ferramentas através do protocolo aberto MCP.

---

## 2. Drivers de Decisão
- [x] **Aderência Open-Source**: Evitar lock-in de fornecedores proprietários; compatibilidade com modelos abertos (Llama, DeepSeek, Qwen) ou comerciais via LiteLLM.
- [x] **Governança & Determinismo**: Uso de máquina de estados em grafo (LangGraph) para fluxos de raciocínio verificáveis e com checkpointing durável.
- [x] **Segurança Corporativa**: Allowlist de comandos executáveis e nós de interrupção Human-in-the-Loop (HITL) para ações destrutivas.
- [x] **Conectividade Padronizada**: Adoção do Model Context Protocol (MCP) como camada padrão de ferramentas e dados.
- [x] **Observabilidade Total**: Tracing nativo OpenTelemetry compatível com plataformas OSS (Arize Phoenix / Langfuse).
- [x] **Prevenção de Loops e Custos**: Limite determinístico de turns (máx 20), teto de tokens e persistência de checkpoints SQLite.

---

## 3. Opções Consideradas

### Opção A: LangGraph + MCP + LiteLLM + OTel (Escolhida)
- **Descrição**: Grafo de estados assíncrono com checkpoints SQLite, orquestração de ferramentas via MCP Client, camada agnóstica de LLMs via LiteLLM, observabilidade OpenTelemetry e pipeline de TDD/Quality Gate integrado.
- **Prós**:
  - (+) Alta auditabilidade e determinismo estrutural em grafo (nós e arestas explícitos).
  - (+) Suporte nativo a pausas Human-in-the-Loop (Gate 1 e Gate 2).
  - (+) Conectores padronizados via MCP e suporte a qualquer LLM via LiteLLM.
  - (+) Checkpoints persistentes para recuperação de falhas sem perda de contexto.
- **Contras**:
  - (-) Requer modelagem prévia de estados e tipagem de mensagens.

### Opção B: Script Monolítico Baseado em ReAct Loop Tradicional
- **Descrição**: Loop simples de `thought -> action -> observation` em um script Python procedural.
- **Prós**:
  - (+) Implementação rápida inicial.
- **Contras**:
  - (-) Propenso a loops infinitos e estouro de orçamento de tokens.
  - (-) Dificuldade para persistir estado, auditar passos intermediários e pausar para aprovação humana.

---

## 4. Decisão Escolhida & Justificativa
Adotamos a **Opção A**. O projeto será construído como um pacote Python corporativo tipado (`pyproject.toml`), estruturado em 4 módulos centrais:
1. **`orchestrator`**: Grafo de estados LangGraph (`Plan` -> `TDD` -> `Implement` -> `Audit` -> `Deliver`) com checkpointing SQLite.
2. **`mcp_client`**: Client assíncrono universal para servidores MCP (filesystem, git, shell sandbox).
3. **`codebase_rag`**: Indexador semântico e estrutural de repositório baseado em AST (Tree-sitter) e embeddings locais.
4. **`quality_gate`**: Runner determinístico de testes (Pytest, Hypothesis PBT, Secret Scanner e Semgrep).
5. **`observability`**: Exportador de traces OpenTelemetry (OTel) para visualização e avaliação contínua.

---

## 5. Consequências & Impactos
- **Positivas**:
  - O engenheiro autônomo opera de maneira determinística, auditável e segura dentro do ambiente corporativo.
  - Permite "Bring Your Own Model" (BYOM) e "Bring Your Own MCP Tools" sem reescrever código.
  - Resiliência contra quedas ou timeouts graças aos checkpoints do SQLite.
- **Riscos & Mitigações**:
  - *Risco*: Latência acumulada entre nós do grafo. *Mitigação*: Execuções de ferramentas assíncronas paralelas quando não houver dependência de dados.
  - *Risco*: Comandos nocivos no terminal. *Mitigação*: Allowlist determinística de comandos seguros e validação obrigatória antes de operações no Git remoto.
