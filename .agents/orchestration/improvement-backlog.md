# Backlog Contínuo de Melhorias (`improvement-backlog.md`)

> **Repositório Persistente de Oportunidades de Evolução do Framework**  
> *Governança estrita: Descoberta → Recomendação → Salvamento com Aprovação do Usuário → Implementação.*

---

## 1. Protocolo de Governança do Backlog

Este catálogo preserva ideias e melhorias identificadas pelo **Corp-Pipeline Master Orchestrator**, garantindo que nenhuma oportunidade valiosa seja perdida ou implementada sem aprovação prévia.

### Estados do Ciclo de Vida:
- `PROPOSED`: Descoberta inicial pela inteligência do orquestrador; aguardando apreciação do usuário.
- `SAVED_NOT_APPROVED`: Usuário aprovou o salvamento para backlog, mas ainda não autorizou a implementação.
- `APPROVED`: Usuário autorizou formalmente o início do desenvolvimento.
- `IN_PROGRESS`: Em desenvolvimento ativo seguindo o Corp-Pipeline (Fase 1 a 5).
- `IMPLEMENTED`: Código implementado e pre-flight aprovado com testes verdes.
- `VERIFIED`: Validado formalmente em produção ou mergeado no branch principal.
- `REJECTED`: Analisado e descartado com justificativa documentada.
- `DEFERRED`: Postergado para milestones futuras.
- `SUPERSEDED`: Substituído por uma proposta ou arquitetura mais moderna.

---

## 2. Tabela de Registro Geral de Melhorias

| ID | Título da Melhoria | Categoria | Complexidade | Status Atual | Data de Descoberta |
|---|---|---|---|---|---|
| `IMP-0001` | Detecção Automática do `.venv` no `stack_detector.py` | `AUTOMATION` | Baixa (S) | `IMPLEMENTED` | `2026-11-19` |
| `IMP-0002` | Circuit Breaker e Reconexão com Backoff no `RemoteMCPSSEClient` | `RELIABILITY` | Média (M) | `IMPLEMENTED` | `2026-11-19` |
| `IMP-0003` | Script de Hook `SessionStart` com Injeção de Contexto Corp-Pipeline | `AUTOMATION` | Baixa (S) | `IMPLEMENTED` | `2026-11-19` |
| `IMP-0004` | Cache de Indexação AST Baseado em Hash SHA-256 de Conteúdo | `EFFICIENCY` | Média (M) | `IMPLEMENTED` | `2026-11-19` |
| `IMP-0005` | Exportação de Diagramas Mermaid Dinâmicos a partir da CLI `dag` | `CAPABILITY` | Baixa (S) | `IMPLEMENTED` | `2026-11-19` |
| `IMP-0006` | Motor Nativo de Mutation Testing via AST para Validação de Testes AI | `QUALITY` | Média (M) | `IMPLEMENTED` | `2026-11-20` |
| `IMP-0007` | Evaluation-Driven Development (EDD) & Scorecard Semântico | `GOVERNANCE` | Média (M) | `IMPLEMENTED` | `2026-11-20` |
| `IMP-0008` | Code GraphRAG & Análise de Blast Radius / Impacto de Mudanças | `EFFICIENCY` | Média (M) | `IMPLEMENTED` | `2026-11-20` |
| `IMP-0009` | OpenTelemetry Agent Tracing & Span Telemetry (OTel LLMOps) | `OBSERVABILITY` | Média (M) | `IMPLEMENTED` | `2026-11-20` |
| `IMP-0010` | Surgical TDD Runner Integrado ao Git Diff & Blast Radius | `EFFICIENCY` | Baixa-Média (S-M) | `IMPLEMENTED` | `2026-11-20` |
| `IMP-0011` | MCP Enterprise Hub & Tool Multiplexer (.mcp.json pools) | `INTEGRATION` | Média (M) | `IMPLEMENTED` | `2026-11-20` |
| `IMP-0012` | AST Auto-Refactor & Self-Healing Fixer (Auto-Remediação) | `AUTOMATION` | Média-Alta (M-L) | `IMPLEMENTED` | `2026-11-20` |
| `IMP-0013` | Open-Source System-One Decision Engine (Outlines / Local SLM) | `EFFICIENCY` | Média (M) | `IMPLEMENTED` | `2026-11-20` |
| `IMP-0014` | Free System-One SLM Fine-Tuning Pipeline & Universal Framework Injection | `EFFICIENCY` | Média (M) | `IMPLEMENTED` | `2026-11-20` |
| `IMP-0015` | Autonomous Benchmark & Eval Harness (Heuristic vs Outlines vs ONNX) | `QUALITY` | Média (M) | `IMPLEMENTED` | `2026-11-22` |
| `IMP-0016` | Multi-Agent Swarm Coordinator via MCP Hub | `ORCHESTRATION` | Média-Alta (M-L) | `IMPLEMENTED` | `2026-11-22` |
| `IMP-0017` | GitHub Actions Workflow de Auto-Remediação em PRs (`self-heal.yml`) | `AUTOMATION` | Baixa-Média (S-M) | `IMPLEMENTED` | `2026-11-22` |
| `IMP-0018` | Context-Aware Metaprompt Engine & Prompt Refiner | `INTELLIGENCE` | Média (M) | `IMPLEMENTED` | `2026-11-22` |
| `IMP-0019` | Autonomous End-to-End Engineering Runner & Dogfooding Pipeline | `ORCHESTRATION` | Média (M) | `IMPLEMENTED` | `2026-11-22` |
| `IMP-0020` | Blindagem de Concorrência & Thread-Safety no Swarm e Tracer | `RELIABILITY` | Média (M) | `IMPLEMENTED` | `2026-11-22` |
| `IMP-0021` | Isolamento Atômico do Motor de Testes de Mutação | `QUALITY` | Média (M) | `IMPLEMENTED` | `2026-11-22` |
| `IMP-0022` | Tratamento Robusto de Timeouts Git e Eliminação de Erros Silenciosos | `RELIABILITY` | Baixa-Média (S-M) | `IMPLEMENTED` | `2026-11-22` |
| `IMP-0023` | Modularização da CLI Corporativa (Decomposição do Monólito) | `MAINTAINABILITY` | Média-Alta (M-L) | `IMPLEMENTED` | `2026-11-22` |
| `IMP-0024` | Gemini LoRA Modular Pipeline para Motion Graphics & Tool Calling (DarkFactory) | `CAPABILITY` | Média-Alta (M-L) | `IMPLEMENTED` | `2026-11-22` |
| `IMP-0025` | Autonomous Proactive Intelligence & Full E2E Lifecycle Hook Suite | `ORCHESTRATION` | Média-Alta (M-L) | `IMPLEMENTED` | `2026-11-22` |
| `IMP-0026` | Tri-Phase Adversarial Loop (Red Team 1.5 → Transcendência 1.6 → Verificação 1.7) | `ORCHESTRATION` | Média-Alta (M-L) | `IMPLEMENTED` | `2026-11-22` |
| `IMP-0027` | Conexão Total de Módulos Desconectados, Unificação de Cache AST SHA-256 e Enriquecimento E2E | `ORCHESTRATION` | Média-Alta (M-L) | `IMPLEMENTED` | `2026-11-24` |
| `IMP-0028` | Resiliência Universal de Hooks do Ciclo de Vida e Ativação Permanente de Regras Always-On | `AUTOMATION` | Baixa-Média (S-M) | `IMPLEMENTED` | `2026-11-24` |
| `IMP-0029` | Continuous Capability Auto-Wiring & Invariante de Potência Máxima (Zero Código Órfão) | `QUALITY` | Média-Alta (M-L) | `IMPLEMENTED` | `2026-11-24` |
| `IMP-0030` | Resiliência de Concorrência, Sincronização & Eliminação de Erros Silenciosos (Pacote 1) | `RELIABILITY` | Média-Alta (M-L) | `IMPLEMENTED` | `2026-11-24` |
| `IMP-0031` | Blindagem de Qualidade, Segurança & Sandboxing de Mutação (Pacote 2) | `QUALITY` | Média-Alta (M-L) | `SAVED_NOT_APPROVED` | `2026-11-24` |
| `IMP-0032` | Integridade da CLI, Output Contratos & Dynamic Hook Dispatching (Pacote 3) | `ARCHITECTURE` | Média (M) | `SAVED_NOT_APPROVED` | `2026-11-24` |
| `IMP-0033` | AI Systems, RAG Cache Starvation & Unificação de Dívidas Técnicas (Pacote 4) | `EFFICIENCY` | Média-Alta (M-L) | `SAVED_NOT_APPROVED` | `2026-11-24` |

---

## 3. Especificação Detalhada das Propostas

---

### 🔹 IMP-0001: Detecção Automática do `.venv` no `stack_detector.py`
- **Categoria**: `AUTOMATION` | `RELIABILITY`
- **Status**: `IMPLEMENTED`
- **Data de Descoberta**: 2026-11-19
- **Problema / Limitação Atual**: No Windows, se o desenvolvedor executa `pytest` ou `python` pelo terminal padrão sem o `.venv` ativado no path, o Python global pode não conter as dependências instaladas (`hypothesis`, `pytest-cov`, `pydantic`), causando falhas falsas. O `stack_detector.py` atualmente emite comandos genéricos como `pytest` ao invés de apontar para `.venv\Scripts\pytest` quando o `.venv` existe localmente.
- **Solução Proposta**: Atualizar `stack_detector.py` para inspecionar se a pasta `.venv` existe no root. Em caso afirmativo no Windows, sugerir `.venv\Scripts\<tool>` ou `.venv/bin/<tool>` em sistemas Unix/macOS.
- **Benefícios Esperados**: Execução determinística dos testes e ferramentas de qualidade sem necessidade de ativação manual do virtualenv.
- **Componentes Afetados**: `.agents/skills/corp-pipeline/scripts/stack_detector.py`.
- **Complexidade**: Baixa (10-15 linhas de código).
- **Riscos**: Mínimos.
- **Critérios de Aceite**: `stack_detector.py` retorna caminhos do virtualenv quando detectado; testes unitários cobrem o comportamento.

---

### 🔹 IMP-0002: Circuit Breaker e Reconexão com Backoff no `RemoteMCPSSEClient`
- **Categoria**: `RELIABILITY` | `CAPABILITY`
- **Status**: `IMPLEMENTED`
- **Data de Descoberta**: 2026-11-19
- **Problema / Limitação Atual**: O cliente SSE para MCP (`RemoteMCPSSEClient`) trata desconexões imediatas, mas não possui um padrão de circuit breaker integrado com retentativas automáticas e backoff exponencial quando o endpoint remoto fica intermitente.
- **Solução Proposta**: Implementar padrão Circuit Breaker com três estados (`CLOSED`, `OPEN`, `HALF_OPEN`) e política configurável de reconexão no cliente SSE.
- **Benefícios Esperados**: Resiliência contra flutuações de rede corporativa e proteção contra sobrecarga em endpoints MCP degradados.
- **Componentes Afetados**: `src/corporate_engineer/mcp/client.py`, `tests/test_mcp_client.py`.
- **Complexidade**: Média (estimado: 60-80 linhas com PBT).
- **Riscos**: Complexidade de concorrência em streaming.
- **Critérios de Aceite**: Suíte de testes com simulação de timeout, transição de estados do circuit breaker e 100% dos testes verdes.

---

### 🔹 IMP-0003: Script de Hook `SessionStart` com Injeção de Contexto Corp-Pipeline
- **Categoria**: `AUTOMATION` | `ARCHITECTURE`
- **Status**: `IMPLEMENTED`
- **Data de Descoberta**: 2026-11-19
- **Problema / Limitação Atual**: Antigravity suporta `SessionStart` em `hooks.json`, mas atualmente não havia nenhum hook configurado para alertar a sessão sobre o estado do projeto e o orquestrador Corp-Pipeline ativo.
- **Solução Proposta**: Implementar `.agents/hooks.json` apontando para um script Python em `.agents/orchestration/hooks/session_start.py` que lê o `state.md`, valida a saúde inicial e injeta a mensagem inicial no formato oficial protojson de Antigravity.
- **Benefícios Esperados**: Inicialização consistente e imediata em qualquer nova conversa sem intervenção do usuário.
- **Componentes Afetados**: `.agents/hooks.json`, `.agents/orchestration/hooks/session_start.py`.
- **Complexidade**: Baixa.
- **Riscos**: Saída inválida se o script emitir texto solto. Deve emitir exclusivamente JSON válido no stdout.
- **Critérios de Aceite**: Execução do script com payload de entrada mockado produz JSON estritamente em conformidade com a especificação de hooks do Antigravity.

---

### 🔹 IMP-0004: Cache de Indexação AST Baseado em Hash SHA-256 de Conteúdo
- **Categoria**: `EFFICIENCY` | `PERFORMANCE`
- **Status**: `IMPLEMENTED`
- **Data de Descoberta**: 2026-11-19
- **Problema / Limitação Atual**: O indexador AST (`ASTCodebaseIndexer`) re-analisa todos os arquivos `.py` a cada execução de `corporate-engineer index`, mesmo quando os arquivos não foram modificados.
- **Solução Proposta**: Integrar o padrão `content-hash-cache-pattern`, armazenando os nós AST indexados indexados por SHA-256 do arquivo fonte em arquivo `.cache/ast_index.json`.
- **Benefícios Esperados**: Redução de até 90% no tempo de reindexação em repositórios grandes.
- **Componentes Afetados**: `src/corporate_engineer/rag/ast_indexer.py`.
- **Complexidade**: Média.
- **Riscos**: Invalidação incorreta de cache em mudanças de sintaxe.
- **Critérios de Aceite**: Testes com Hypothesis garantem que o resultado com e sem cache é semanticamente idêntico.

---

### 🔹 IMP-0005: Exportação de Diagramas Mermaid Dinâmicos a partir da CLI `dag`
- **Categoria**: `CAPABILITY`
- **Status**: `IMPLEMENTED`
- **Data de Descoberta**: 2026-11-19
- **Problema / Limitação Atual**: O comando `corporate-engineer dag` gera tabelas de texto ou JSON dos nós e transições, mas não gera diagramas visuais legíveis para documentação ou PRs.
- **Solução Proposta**: Adicionar flag `--mermaid` ao comando `dag` que produz uma string `flowchart TD` dos estados da FSM e dependências de tarefas.
- **Benefícios Esperados**: Visualização instantânea da topologia do grafo de engenharia e fácil inclusão em ADRs e relatórios.
- **Componentes Afetados**: `src/corporate_engineer/cli.py`, `src/corporate_engineer/orchestrator/graph.py`.
- **Complexidade**: Baixa.
- **Riscos**: Mínimos.
- **Critérios de Aceite**: Flag `--mermaid` gera código Mermaid válido testado via pytest.

---

### 🔹 IMP-0006: Motor Nativo de Mutation Testing via AST para Validação de Testes AI
- **Categoria**: `QUALITY` | `RELIABILITY`
- **Status**: `IMPLEMENTED`
- **Data de Descoberta**: 2026-11-20
- **Problema / Limitação Atual**: O pipeline avalia cobertura de código em linhas (`pytest-cov`), mas não valida a assertividade real dos testes contra bugs lógicos. Testes gerados por IA correm o risco de passarem com 100% de cobertura mesmo quando há regressões de lógica sutis.
- **Solução Proposta**: Implementar motor nativo de Mutation Testing via manipulação de AST (`src/corporate_engineer/quality/mutation.py`), integrando mutadores de operadores relacionais, booleanos e retornos. Adicionar flag `--mutation` ao subcomando `corporate-engineer audit` para calcular e reportar o Mutation Score (% de mutantes mortos pela suíte de testes).
- **Benefícios Esperados**: Certificação objetiva de que a suíte de testes do repositório é robusta e resistente contra falhas lógicas e testes superficiais.
- **Componentes Afetados**: `src/corporate_engineer/quality/mutation.py`, `src/corporate_engineer/cli.py`, `tests/test_mutation.py`.
- **Complexidade**: Média (M).
- **Riscos**: Tempo excessivo de execução se mutantes não forem testados de forma seletiva e isolada.
- **Critérios de Aceite**: Motor gera mutantes sintáticos válidos, calcula taxa de mutantes mortos e sobrevive a auditoria pre-flight com 100% dos testes verdes.

---

### 🔹 IMP-0007: Evaluation-Driven Development (EDD) & Scorecard Semântico
- **Categoria**: `GOVERNANCE` | `QUALITY`
- **Status**: `IMPLEMENTED`
- **Data de Descoberta**: 2026-11-20
- **Problema / Limitação Atual**: Não há comando ou módulo CLI para emitir um scorecard holístico da saúde do código (imutabilidade, tipagem Pydantic, complexidade ciclomática, ausência de code smells corporativos).
- **Solução Proposta**: Criar o comando `corporate-engineer eval` e módulo `src/corporate_engineer/eval/` que executa avaliações semânticas estáticas e emite uma pontuação de 0 a 100 com scorecard em 5 eixos.
- **Benefícios Esperados**: Observabilidade imediata da saúde da base de código contra degradação por agentes autônomos.
- **Componentes Afetados**: `src/corporate_engineer/eval/`, `src/corporate_engineer/cli.py`.
- **Complexidade**: Média (M).
- **Riscos**: Falsos positivos em regras heurísticas de estilo se os limites não forem calibrados.
- **Critérios de Aceite**: Comando `eval` gera scorecard JSON/tabular detalhando conformidade com os 5 eixos.

---

### 🔹 IMP-0008: Code GraphRAG & Análise de Blast Radius / Impacto de Mudanças
- **Categoria**: `EFFICIENCY` | `CAPABILITY`
- **Status**: `IMPLEMENTED`
- **Data de Descoberta**: 2026-11-20
- **Problema / Limitação Atual**: O indexador AST atual mapeia classes e métodos por arquivo, mas não calcula o grafo de impacto ("se a função X mudar, quais arquivos e testes são diretamente afetados?").
- **Solução Proposta**: Adicionar motor de cálculo de **Blast Radius / Impact Analysis** ao indexador AST e flag `index --impact-of <arquivo/função>`.
- **Benefícios Esperados**: Permite que o pipeline execute cirurgicamente apenas os testes afetados por uma mudança, acelerando o ciclo TDD.
- **Componentes Afetados**: `src/corporate_engineer/rag/ast_indexer.py`, `src/corporate_engineer/cli.py`.
- **Complexidade**: Média (M).
- **Riscos**: Chamadas dinâmicas (ex.: `getattr`) podem não ser detectadas via AST estático.
- **Critérios de Aceite**: Identificação precisa de símbolos dependentes com testes demonstrando acurácia no grafo.

---

### 🔹 IMP-0009: OpenTelemetry Agent Tracing & Span Telemetry (OTel LLMOps)
- **Categoria**: `OBSERVABILITY` | `RELIABILITY`
- **Status**: `IMPLEMENTED` (Ref: `PR-CORP-007.md`, `ADR-007`)
- **Data de Descoberta**: 2026-11-20
- **Problema / Limitação Atual**: A execução de DAGs, nós de agentes e ferramentas MCP não gera traces de telemetria estruturados compatíveis com OpenTelemetry, dificultando a análise de gargalos de latência, contagem de tokens consumidos e diagnóstico de bugs distribuídos.
- **Solução Proposta**: Implementar módulo `src/corporate_engineer/telemetry/` com `AgentTracer` gerando spans padronizados (`trace_id`, `span_id`, latência, contagem de tokens, prompt/completion payload, status de erro) e exportadores locais para JSON e coletores OTel.
- **Benefícios Esperados**: Observabilidade de nível sênior em produção para mitigar o "observability gap" em sistemas multi-agentes.
- **Componentes Afetados**: `src/corporate_engineer/telemetry/`, `src/corporate_engineer/orchestrator/graph.py`, `src/corporate_engineer/mcp/client.py`.
- **Complexidade**: Média (M).
- **Riscos**: Overhead de serialização se não for mantido assíncrono.
- **Critérios de Aceite**: Spans gerados para cada nó do grafo com validação de formato e testes unitários.

---

### 🔹 IMP-0010: Surgical TDD Runner Integrado ao Git Diff & Blast Radius
- **Categoria**: `EFFICIENCY` | `QUALITY`
- **Status**: `IMPLEMENTED` (Ref: `PR-CORP-008.md`, `ADR-008`)
- **Data de Descoberta**: 2026-11-20
- **Problema / Limitação Atual**: O desenvolvedor ou agente precisa rodar `corporate-engineer blast-radius` manualmente e em seguida copiar o comando de teste para validar mudanças no código.
- **Solução Proposta**: Criar o subcomando `corporate-engineer test-surgical` que inspeciona o `git diff` contra a branch base (ex.: `main`), calcula automaticamente o blast radius dos símbolos/arquivos alterados e executa cirurgicamente apenas os testes afetados.
- **Benefícios Esperados**: Redução de até 80% no tempo de ciclo do loop TDD em repositórios grandes.
- **Componentes Afetados**: `src/corporate_engineer/cli.py`, `src/corporate_engineer/rag/impact.py`.
- **Complexidade**: Baixa-Média (S-M).
- **Riscos**: Mudanças puramente dinâmicas podem exigir fallback para execução completa da suíte.
- **Critérios de Aceite**: `test-surgical` detecta alterações locais não commitadas ou no diff da branch e executa os testes afetados retornando código 0 ou 1.

---

### 🔹 IMP-0011: MCP Enterprise Hub & Tool Multiplexer (.mcp.json pools)
- **Categoria**: `INTEGRATION` | `CAPABILITY`
- **Status**: `IMPLEMENTED` (Ref: `PR-CORP-011.md`, `ADR-011`)
- **Data de Descoberta**: 2026-11-20
- **Problema / Limitação Atual**: O cliente MCP atual (`LocalMCPToolAdapter` e `RemoteMCPSSEClient`) gerencia um servidor isolado por vez via CLI ou parâmetros pontuais. Não há suporte para carregar arquivos de configuração como `.mcp.json` e orquestrar múltiplos servidores corporativos simultaneamente (ex.: GitHub, Jira, Postgres, Sentry).
- **Solução Proposta**: Criar `MCPEnterpriseHub` que lê arquivos `.mcp.json`, instancia pools de conexões stdio/SSE com circuit breakers individuais e oferece um namespace unificado de ferramentas (`github.create_pr`, `postgres.query`, `jira.get_issue`).
- **Benefícios Esperados**: Transforma o framework em uma plataforma unificada de consumo MCP enterprise.
- **Componentes Afetados**: `src/corporate_engineer/mcp/hub.py`, `src/corporate_engineer/cli.py`.
- **Complexidade**: Média (M).
- **Riscos**: Gerenciamento de ciclo de vida de múltiplos subprocessos em sistemas Windows.
- **Critérios de Aceite**: Carregamento de configuração multi-servidor com resolução de ferramentas e isolamento de falhas.

---

### 🔹 IMP-0012: AST Auto-Refactor & Self-Healing Fixer (Auto-Remediação)
- **Categoria**: `AUTOMATION` | `QUALITY`
- **Status**: `IMPLEMENTED` (Ref: `PR-CORP-012.md`, `ADR-012`)
- **Data de Descoberta**: 2026-11-20
- **Problema / Limitação Atual**: Quando os subcomandos `eval` (scorecard semântico) ou `audit` detectam violações estruturais (ex.: métodos `__init__` sem `-> None`, ausência de tipos em retornos evidentes, variáveis globais indevidas), a correção necessita de intervenção manual.
- **Solução Proposta**: Adicionar o comando `corporate-engineer fix --auto` que utiliza `ast.NodeTransformer` para aplicar correções seguras e cirúrgicas sem introduzir regressões.
- **Benefícios Esperados**: Aumento autônomo na pontuação do scorecard semântico sem atrito manual.
- **Componentes Afetados**: `src/corporate_engineer/eval/fixer.py`, `src/corporate_engineer/cli.py`.
- **Complexidade**: Média-Alta (M-L).
- **Riscos**: Risco de alterar semântica do código se transformações não forem estritamente conservadoras.
- **Critérios de Aceite**: Transformações aplicadas são validadas por re-execução da suíte de testes existente.

---

### 🔹 IMP-0013: Open-Source System-One Decision Engine (Outlines / Local SLM)
- **Categoria**: `EFFICIENCY` | `ARCHITECTURE` | `PRIVACY`
- **Status**: `IMPLEMENTED` (Ref: `PR-CORP-009.md`, `ADR-009`)
- **Data de Descoberta**: 2026-11-20
- **Problema / Limitação Atual**: Decisões categóricas de alta frequência (como roteamento de subagentes na DAG, triagem de risco de mudanças para o Surgical Runner e validação semântica de regras como imutabilidade) atualmente ou dependem de casamento heurístico simples ou exigiriam invocar LLMs generativos pesados (System Two). Isso gera latência indesejada, alto custo de tokens, risco de parsing de JSON e dependência de APIs proprietárias fechadas (como Jev/TypeSafe AI).
- **Solução Proposta**: Implementar um motor corporativo desacoplado de decisões rápidas (System One) baseado em tecnologias open-source:
  1. *Constrained Logits Decoding*: via biblioteca `outlines` com SLMs locais leves (ex.: `Qwen/Qwen2.5-0.5B-Instruct` ou `SmolLM2-360M`) para saídas Pydantic v2 estritas com 0% de erro de schema.
  2. *Calibração Probabilística por NLI*: via modelos compactos de inferência de linguagem natural (ex.: `ModernBERT` ou `DeBERTa-v3` via ONNX Runtime) para probabilidades contínuas (equivalente a `noul`/Yes-No).
  3. *Arquitetura Modular com Graceful Fallback*: fallback automático para `HeuristicDecisionEngine` se dependências pesadas ou pesos locais não estiverem instalados.
- **Benefícios Esperados**: Despacho de subagentes e decisões em sub-50ms no localhost, conformidade total de privacidade e dados corporativos (zero envio externo), 100% de precisão de schema e ausência de custos de API.
- **Componentes Afetados**: `src/corporate_engineer/system_one/`, `src/corporate_engineer/orchestrator/`, `src/corporate_engineer/quality/`, `src/corporate_engineer/models.py`, `src/corporate_engineer/cli.py`.
- **Complexidade**: Média (M).
- **Riscos**: Tamanho de dependências e tempo de download inicial de modelos locais. Mitigação: empacotamento opcional (`.[system-one]`), lazy-loading e fallback heurístico nativo.
- **Critérios de Aceite**: Contratos Pydantic v2 para `DecisionChoice`, `DecisionScore` e `DecisionNoul`; interface abstrata `SystemOneEngine` com implementação concreta e fallback estático; suíte de testes com 100% de isolamento e zero chamadas de rede externas.

---

### 🔹 IMP-0014: Free System-One SLM Fine-Tuning Pipeline & Universal Framework Injection
- **Categoria**: `EFFICIENCY` | `ARCHITECTURE` | `AI-ENGINEERING`
- **Status**: `IMPLEMENTED` (Ref: `PR-CORP-010.md`, `ADR-010`)
- **Data de Descoberta**: 2026-11-20
- **Problema / Limitação Atual**: O motor `SystemOne` introduzido em `IMP-0013` provou o valor de decisões reflexivas ultrarrápidas, mas opera apenas em um subconjunto de pontos de decisão (roteamento de agente e risco geral de diff). Além disso, não existia um pipeline padronizado, reprodutível e 100% gratuito para sintetizar datasets de domínio do framework e treinar/otimizar SLMs compactos (0.5B / 360M) via LoRA/PEFT e exportar para ONNX Int8.
- **Solução Proposta**:
  1. *Gerador de Dataset Sintético Corporativo (`system_one/dataset.py`)*: Extrai e sintetiza amostras tipadas Pydantic v2 cobrindo roteamento de subagentes, avaliação de risco de diffs, seleção de commit types e descarte de nós da DAG, exportando para formato compatível com Hugging Face / SFTTrainer.
  2. *Pipeline de Fine-Tuning & Exportação Gratuita (`system_one/trainer.py` e recipe Colab/local)*: Harness de treinamento baseado em LoRA/PEFT projetado para execução a custo zero no Google Colab T4 / Kaggle / CPU local com exportação para ONNX Runtime Int8.
  3. *Injeção Universal do System One*: Plugar o motor System One em:
     - `orchestrator/graph.py`: Pular nós dinamicamente (`should_skip_node`) e triagem de falhas (`triage_node_failure`).
     - `quality/surgical_runner.py`: Avaliação de expansão do escopo de testes para integração (`evaluate_scope_expansion`).
     - `git_utils.py`: Classificação automática de tipo de commit convencional a partir do diff (`classify_commit_type`).
     - `rag/impact.py`: Filtro e poda de contexto para redução de tokens do Sistema 2 (`prune_context`).
  4. *CLI Corporativa*: Extensão do subcomando `corporate-engineer decide` e novo subcomando `corporate-engineer dataset`.
- **Benefícios Esperados**: Redução de mais de 70% no consumo de tokens do Sistema 2, decisões determinísticas em sub-5ms em todo o ciclo de engenharia e autonomia cognitiva local a custo financeiro zero.
- **Componentes Afetados**: `src/corporate_engineer/system_one/`, `src/corporate_engineer/orchestrator/`, `src/corporate_engineer/quality/`, `src/corporate_engineer/rag/`, `src/corporate_engineer/git_utils.py`, `src/corporate_engineer/models.py`, `src/corporate_engineer/cli.py`.
- **Complexidade**: Média (M).
- **Riscos**: Dependências opcionais pesadas no ambiente corporativo padrão. Mitigação: arquitetura pura desacoplada, fallback heurístico nativo e receitas standalone para Colab.
- **Critérios de Aceite**: Modelos Pydantic v2 tipados (`TrainingSample`, `DatasetReport`), gerador de dataset funcional com exportação JSONL, métodos de integração nos módulos do framework, receita de fine-tuning gratuita e 100% dos testes passando com 0 erros de linter e tipagem.

---

### 🔹 IMP-0015: Autonomous Benchmark & Eval Harness (Heuristic vs Outlines vs ONNX)
- **Categoria**: `QUALITY` | `EFFICIENCY` | `OBSERVABILITY`
- **Status**: `IMPLEMENTED` (Ref: `PR-CORP-015.md`, `ADR-015`)
- **Data de Descoberta**: 2026-11-22
- **Problema / Limitação Atual**: Com três motores de decisão disponíveis no framework (`HeuristicDecisionEngine`, `OutlinesDecisionEngine` e `ONNXNLIDecisionEngine`), não existe um comando ou módulo padronizado de benchmark que compare quantitativamente e empiricamente a acurácia, latência (P50/P95/P99), throughput (RPS) e consumo de recursos entre eles no dataset de domínio.
- **Solução Proposta**:
  1. *Modelos DTO Pydantic v2 (`models.py`)*: `EngineLatencyStats`, `EngineBenchmarkResult`, `BenchmarkReport` com validação estrita.
  2. *Motor de Benchmark (`system_one/benchmark.py`)*: `SystemOneBenchmark` que executa baterias de testes em lote e isolados com temporização de alta precisão (`time.perf_counter`), cálculo estatístico de percentis e avaliação de acurácia contra outputs esperados.
  3. *CLI Corporativa (`cli.py`)*: Subcomando `corporate-engineer benchmark` suportando `--dataset`, `--engines`, `--iterations`, `--max-samples`, `--format [text|json|markdown]` e `--output`.
  4. *Recomendações Automáticas*: Geração de scorecard comparativo destacando o motor vencedor em latência e acurácia.
- **Benefícios Esperados**: Evidências científicas e reprodutíveis para guiar decisões de roteamento e dimensionamento de infraestrutura em produção.
- **Componentes Afetados**: `src/corporate_engineer/models.py`, `src/corporate_engineer/system_one/benchmark.py`, `src/corporate_engineer/cli.py`, `tests/test_system_one_benchmark.py`.
- **Complexidade**: Média (M).
- **Riscos**: Variação de latência em ambientes sem GPU ou com carga concorrente de CPU. Mitigação: fases de aquecimento (*warmup*) e múltiplas iterações com percentis P50/P95.
- **Critérios de Aceite**: Módulo de benchmark funcional, subcomando CLI registrado, relatórios text/json/markdown válidos, 100% dos testes unitários passando e aprovação no Pre-Flight.

---

### 🔹 IMP-0016: Multi-Agent Swarm Coordinator via MCP Hub
- **Categoria**: `ORCHESTRATION` | `INTEGRATION` | `CAPABILITY`
- **Status**: `IMPLEMENTED` (Ref: `PR-CORP-016.md`, `ADR-016`)
- **Data de Descoberta**: 2026-11-22
- **Problema / Limitação Atual**: O framework dispõe de um catálogo canônico de 8 subagentes (`architect`, `tdd-guide`, `code-reviewer`, `python-reviewer`, `security-reviewer`, etc.) e do `MCPEnterpriseHub` (IMP-0011) com circuit breakers e poda semântica. No entanto, a execução multi-agente ainda ocorre de modo sequencial ou em tarefas isoladas na DAG. Não há um **Swarm Coordinator** nativo que despache sub-tarefas especializadas em paralelo (Fan-Out/Fan-In), injete dinamicamente apenas o subset de ferramentas MCP apropriado para cada subagente com circuit breaker individual, e agregue pareceres para formação de consenso (ex.: revisão tripartite entre arquitetura, segurança e código).
- **Solução Proposta**:
  1. *Modelos DTO Pydantic v2 (`models.py`)*: `SwarmMember`, `SwarmTaskResult`, `SwarmGoalReport`.
  2. *Motor Swarm Coordinator (`orchestrator/swarm.py`)*:
     - `SwarmCoordinator` integrado ao `MCPEnterpriseHub` e ao `SystemOneRouter`.
     - Despacho paralelo concorrente (ThreadPool/Async) com barreira de sincronização (*join*) e agregação de consenso.
     - Poda seletiva de ferramentas MCP por papel do subagente (`prune_tools_for_prompt`).
     - Isolamento de falhas por Circuit Breaker individual por ferramenta/servidor.
  3. *CLI Corporativa (`cli.py`)*: Subcomando `corporate-engineer swarm` com modos `run` (Fan-Out/Fan-In para metas distribuídas) e `consensus` (revisão multi-agente concorrente com votação).
- **Benefícios Esperados**: Execução distribuída de alta velocidade para tarefas complexas de engenharia, redução de gargalos sequenciais e governança coletiva multi-perspectiva com ferramentas seguras.
- **Componentes Afetados**: `src/corporate_engineer/models.py`, `src/corporate_engineer/orchestrator/swarm.py`, `src/corporate_engineer/cli.py`, `tests/test_swarm_coordinator.py`.
- **Complexidade**: Média-Alta (M-L).
- **Riscos**: Concorrência de subprocessos stdio de ferramentas MCP no Windows. Mitigação: isolamento por membro do swarm e fallback seguro com circuit breaker.
- **Critérios de Aceite**: `SwarmCoordinator` despacha tarefas concorrentes, injeta ferramentas MCP com circuit breaker, agrega consenso e atinge 100% de testes passando e aprovação no Pre-Flight.

---

### 🔹 IMP-0018: Context-Aware Metaprompt Engine & Prompt Refiner
- **Categoria**: `INTELLIGENCE` | `ORCHESTRATION` | `QUALITY`
- **Status**: `IMPLEMENTED` (Ref: `ADR-018`, `PR-CORP-018.md`)
- **Data de Descoberta**: 2026-11-22
- **Problema / Limitação Atual**: O pipeline do framework depende da qualidade e clareza do prompt inicial do usuário. Prompts informais ou sucintos (ex.: "adicione timeout no mcp") levam a desvios de escopo, ambiguidades nos testes TDD e sobrecarga na fase de perguntas investigativas do `/grill-me_v2`. Não havia uma camada formal de pré-processamento para transformar o input humano em um metaprompt técnico ancorado no contexto real do repositório (AST, domínios e contratos).
- **Solução Proposta**:
  1. *Modelos DTO Pydantic v2 (`models.py`)*: `RevisedPromptSpec` com requisitos funcionais, não-funcionais corporativos, módulos afetados, restrições out-of-scope, cenários TDD e score de confiança.
  2. *Motor Context-Aware Refiner (`prompt/refiner.py`)*:
     - Detecção léxica de domínios corporativos (`mcp`, `orchestrator`, `quality`, `rag`, `system_one`, `cli`).
     - Fast-Path Bypass determinístico para comandos operacionais (`pytest`, `git status`, `/preflight`).
     - Síntese de metaprompt técnico em Markdown para alimentar o orquestrador e subagentes.
  3. *CLI Corporativa (`cli.py`)*: Subcomando `corporate-engineer prompt refine <prompt>` com flags `--bypass-gate`, `--format [text|json|markdown]`, `--workspace` e `--output`.
- **Benefícios Esperados**: Redução de ambiguidades na entrada do pipeline, delimitação precisa de escopo, geração antecipada de casos de teste TDD e transparência via preview de refinamento.
- **Componentes Afetados**: `src/corporate_engineer/models.py`, `src/corporate_engineer/prompt/`, `src/corporate_engineer/cli.py`, `tests/test_metaprompt_engine.py`.
- **Complexidade**: Média (M).
- **Riscos**: Reescritas desnecessárias em comandos simples. Mitigação: Fast-Path Bypass automático para comandos operacionais e queries curtas.
- **Critérios de Aceite**: `ContextAwarePromptRefiner` funcional com suporte a bypass e enriquecimento, subcomando CLI registrado, 100% dos testes unitários passando e aprovação no Pre-Flight.

---

### 🔹 IMP-0017: GitHub Actions Workflow de Auto-Remediação em PRs (`self-heal.yml`)
- **Categoria**: `AUTOMATION` | `QUALITY` | `CI/CD`
- **Status**: `IMPLEMENTED` (Ref: `ADR-017`, `PR-CORP-017.md`)
- **Data de Descoberta**: 2026-11-22
- **Problema / Limitação Atual**: O framework dispõe do motor `ASTSelfHealingFixer` (`src/corporate_engineer/eval/fixer.py`) e do subcomando `corporate-engineer fix --auto`, capazes de corrigir automaticamente violações estruturais comuns (`__init__ -> None`, mutabilidade em defaults, limpeza de declarações `pass` redundantes). Contudo, essa capacidade só é executada se o desenvolvedor rodar o comando localmente. Em Pull Requests abertos no GitHub, essas falhas podem quebrar o CI ou degradar a qualidade do código caso passem desapercebidas.
- **Solução Proposta**:
  1. *Workflow de CI (`.github/workflows/self-heal.yml`)*: Acionado em eventos `pull_request` (`opened`, `synchronize`, `reopened`).
  2. *Etapas de Execução*:
     - Checkout do repositório no branch do PR (`ref: ${{ github.head_ref }}`).
     - Setup do ambiente Python e instalação de dependências mínimas.
     - Execução de `corporate-engineer fix --auto --path src/`.
     - Verificação de diffs locais via `git status --porcelain`.
     - Se houver alterações aplicadas, commit e push automáticos no branch do PR (`chore(self-heal): apply automated AST fixes`).
     - Execução da auditoria de qualidade `corporate-engineer audit --strict` com verificação estrita.
  3. *Script / Módulo Auxiliar & Testes*: Testes automatizados em `tests/test_self_heal_workflow.py` validando sintaxe YAML do workflow, conformidade de segurança e integração com a suíte de testes.
- **Benefícios Esperados**: Manutenção contínua e autônoma da qualidade da base de código sem exigir esforço manual de revisão em detalhes sintáticos triviais.
- **Componentes Afetados**: `.github/workflows/self-heal.yml`, `tests/test_self_heal_workflow.py`.
- **Complexidade**: Baixa-Média (S-M).
- **Riscos**: Loops de trigger caso o commit do bot dispare o workflow novamente. Mitigação: usar `[skip ci]` ou token padrão `GITHUB_TOKEN` que por padrão não re-dispara workflows.
- **Critérios de Aceite**: Workflow `.github/workflows/self-heal.yml` sintaticamente válido, testado via suite automatizada, com mitigação de loops e aprovação no Pre-Flight.

---

### 🔹 IMP-0019: Autonomous End-to-End Engineering Runner & Dogfooding Pipeline (`cli run`)
- **Categoria**: `ORCHESTRATION` | `CAPABILITY` | `QUALITY`
- **Status**: `IMPLEMENTED` (Ref: `ADR-019`, `PR-CORP-019.md`)
- **Data de Descoberta**: 2026-11-22
- **Problema / Limitação Atual**: O framework dispõe da máquina de estados finitos (`AutonomousEngineeringGraph`), motor de refinamento contextual (`ContextAwarePromptRefiner`), auto-remediação de AST (`ASTSelfHealingFixer`), portão de qualidade (`QualityGateRunner`) e telemetria OpenTelemetry. Contudo, o subcomando `corporate-engineer run` apenas inicializava o grafo e imprimia o estado inicial, sem conduzir a execução autônoma completa das 5 fases de engenharia (`PLANNING` -> `TDD` -> `IMPLEMENT` -> `AUDIT` -> `DELIVER`), sem salvar checkpoints em cada transição e sem gerar relatório consolidado de entrega (`RunExecutionReport`).
- **Solução Proposta**:
  1. *Modelos DTO Pydantic v2 (`models.py`)*: `RunExecutionReport` com status, fase final, iterações, checkpoints gerados, plano refinado, arquivos de teste, contagem de alterações, status de auditoria, duração e suporte a `--dry-run`.
  2. *Motor de Execução de Ciclo de Vida Completo (`orchestrator/graph.py`)*:
     - Método `run_pipeline(dry_run=False, auto_deliver=True, strict_audit=True) -> RunExecutionReport`.
     - Fase `PLANNING`: refinamento contextual com ancoragem semântica via `ContextAwarePromptRefiner`, avanço de fase e checkpoint.
     - Fase `TDD`: identificação/execução cirúrgica de cenários de teste, avanço de fase e checkpoint.
     - Fase `IMPLEMENT`: execução de auto-remediação de AST ou registro de diffs, avanço de fase e checkpoint.
     - Fase `AUDIT`: execução de secret scan e verificação estrita via `QualityGateRunner`. Se aprovado, transição para `DELIVER`; se reprovado, transição e triagem de falhas.
     - Fase `DELIVER`: fechamento com spans de rastreamento OpenTelemetry e exportação do relatório.
  3. *CLI Corporativa (`cli.py`)*: Subcomando `corporate-engineer run` atualizado com suporte a `--dry-run`, `--strict-audit`, `--format [text|json|markdown]` e `--output`.
- **Benefícios Esperados**: Capacidade real de dogfooding end-to-end do framework em repositórios corporativos, rastreabilidade determinística por checkpoints e relatórios executivos estruturados.
- **Componentes Afetados**: `src/corporate_engineer/models.py`, `src/corporate_engineer/orchestrator/graph.py`, `src/corporate_engineer/cli.py`, `tests/test_autonomous_runner.py`.
- **Complexidade**: Média (M).
- **Riscos**: Execução indevida de alterações no código em modo dogfooding. Mitigação: flag `--dry-run` para simulação segura e idempotente sem mutações de arquivos de código.
- **Critérios de Aceite**: Suíte de testes automatizados com cobertura do ciclo completo, suporte a `--dry-run`, geração de checkpoints válidos, aprovação no Pre-Flight e relatório de execução emitido com sucesso.

---

### 🔹 IMP-0020: Blindagem de Concorrência & Thread-Safety no Swarm e Tracer (RLock & ContextVars)
- **Categoria**: `RELIABILITY` | `OBSERVABILITY` | `ORCHESTRATION`
- **Status**: `IMPLEMENTED` (Ref: `ADR-021`, `PR-CORP-020.md`)
- **Data de Descoberta**: 2026-11-22
- **Problema / Limitação Atual**:
  1. No `SwarmCoordinator` (`src/corporate_engineer/orchestrator/swarm.py:93-119`), o status dos membros (`member.status = "WORKING" / "COMPLETED"`) é mutado concorrentemente em threads do `ThreadPoolExecutor` sem controle de concorrência ou sincronização, gerando potenciais *race conditions*.
  2. No `AgentTracer` (`src/corporate_engineer/telemetry/tracer.py:42-43`), a pilha de spans ativos `_active_stack` e a lista `spans` não são thread-safe. Quando múltiplos nós paralelos no DAG ou tarefas concorrentes compartilham o mesmo tracer, a manipulação de spans pode colidir. Além disso, em `export_trace` (L131-L141), se um span possuir tanto `tokens` quanto `gen_ai.usage.total_tokens`, os tokens são somados em duplicidade.
  3. No `CircuitBreaker` (`src/corporate_engineer/mcp/circuit_breaker.py:48-55`), as transições de estado (`OPEN`, `HALF_OPEN`) não possuem locks de thread.
- **Solução Proposta**:
  1. *Swarm Imutável*: Tratar `SwarmMember` como DTO Pydantic imutável (`member.model_copy(update={"status": ...})`) e proteger acessos ao hub com `threading.Lock`.
  2. *Tracer Context-Aware*: Proteger manipuladores de spans com `threading.RLock()` ou `contextvars.ContextVar` para pilhas isoladas por contexto/thread. Corrigir cálculo de métricas em `export_trace` com ordem de precedência explícita (`gen_ai.usage.total_tokens` prioritário com break).
  3. *Circuit Breaker*: Adicionar `threading.RLock()` para proteger `record_success`, `record_failure`, `can_execute` e `state`.
- **Benefícios Esperados**: Execução concorrente 100% thread-safe sem corrupção de estado interno, isolamento real entre threads no Swarm/DAG e métricas precisas de consumo de tokens OTel.
- **Componentes Afetados**: `src/corporate_engineer/orchestrator/swarm.py`, `src/corporate_engineer/telemetry/tracer.py`, `src/corporate_engineer/mcp/circuit_breaker.py`, `tests/test_swarm_coordinator.py`, `tests/test_tracer.py`.
- **Complexidade**: Média (M).
- **Riscos**: Mínimos, desde que os locks sejam reentrantes (`RLock`) evitando deadlocks.
- **Critérios de Aceite**: Testes com concorrência paralela sob carga passando sem race conditions e verificação estrita de contagem única de tokens no tracer.

---

### 🔹 IMP-0021: Isolamento Atômico do Motor de Testes de Mutação (Safe Sandbox & Atomic Reversion)
- **Categoria**: `QUALITY` | `RELIABILITY`
- **Status**: `IMPLEMENTED` (Ref: `ADR-022`, `PR-CORP-021.md`)
- **Data de Descoberta**: 2026-11-22
- **Problema / Limitação Atual**: O motor `MutationTestingEngine` (`src/corporate_engineer/quality/mutation.py:198-257`) sobrescreve diretamente os arquivos de código-fonte no disco (`target_path.write_text(mutated_code)`). Caso o processo seja interrompido abruptamente (SIGINT/Ctrl+C, timeout, queda de energia ou crash do pytest), o código de produção permanece mutado/corrompido no disco sem reversão automática.
- **Solução Proposta**:
  1. Implementar mecanismo de sandbox atômico via `tempfile.TemporaryDirectory` ou context manager com garantia de backup (`.bak`) e reversão atômica em bloco `try/finally`.
  2. Registrar e capturar sinais de SO (`signal.SIGINT`, `signal.SIGTERM`) durante a execução de mutações para garantir reversão imediata antes do encerramento do processo.
  3. No `_SingleNodeMutator`, evitar dessincronização de contagem de nós em geradores/comprehensions e capturar erros de sintaxe com logging explícito em vez de engolir exceções.
- **Benefícios Esperados**: Blindagem contra corrupção acidental do repositório durante testes de mutação e maior confiabilidade no cálculo do Mutation Score.
- **Componentes Afetados**: `src/corporate_engineer/quality/mutation.py`, `tests/test_mutation_testing.py`.
- **Complexidade**: Média (M).
- **Riscos**: Overhead de I/O em disco ao criar cópias temporárias. Mitigação: usar cópia atômica em memória ou backup localizado pontual.
- **Critérios de Aceite**: Simulação de interrupção abrupta comprova reversão 100% confiável do código original.

---

### 🔹 IMP-0022: Tratamento Robusto de Timeouts Git e Eliminação de Erros Silenciosos no Pre-Flight
- **Categoria**: `RELIABILITY` | `QUALITY`
- **Status**: `IMPLEMENTED` (Ref: `ADR-024`, `PR-CORP-022.md`)
- **Data de Descoberta**: 2026-11-22
- **Problema / Limitação Atual**:
  1. Em `src/corporate_engineer/git_utils.py:107, 122, 157`, comandos como `git ls-remote` e `git push` usam timeouts agressivos de 2s-3s e capturam genericamente `(OSError, subprocess.SubprocessError): return False`. Em caso de latência de rede, VPN ou autenticação pendente, a falha é mascarada como "branch não existe" ou "push falhou sem motivo".
  2. Em `src/corporate_engineer/quality/surgical_runner.py:48, 71`, comandos `git status` e `git diff` falham silenciosamente com `pass` em caso de erro, gerando lista vazia de arquivos e abortando testes cirúrgicos sem aviso.
  3. Em `src/corporate_engineer/quality/gate.py:65-73`, `subprocess.run(actual_cmd, shell=True)` usa interpolação de string e timeout hardcoded de 120s.
- **Solução Proposta**:
  1. Capturar explicitamente `subprocess.TimeoutExpired` em `git_utils.py`, emitindo logs com `logger.warning` / `logger.error` e mensagens de erro estruturadas.
  2. Permitir configuração de timeout ajustável para operações remotas (ex: 15s padrão).
  3. No `surgical_runner.py`, emitir aviso ou erro claro quando `git status`/`diff` falhar (ex: `.git/index.lock` presente).
  4. No `gate.py`, migrar para `shell=False` com lista de argumentos e timeout configurável.
- **Benefícios Esperados**: Diagnósticos transparentes de conectividade Git, eliminação de falsos negativos no pipeline e redução de risco de segurança por shell injection.
- **Componentes Afetados**: `src/corporate_engineer/git_utils.py`, `src/corporate_engineer/quality/surgical_runner.py`, `src/corporate_engineer/quality/gate.py`.
- **Complexidade**: Baixa-Média (S-M).
- **Riscos**: Mínimos.
- **Critérios de Aceite**: Falhas de timeout no git geram logs descritivos; `gate.py` executa via `shell=False`.

---

### 🔹 IMP-0023: Modularização da CLI Corporativa (Decomposição do Monólito de 1661 Linhas)
- **Categoria**: `MAINTAINABILITY` | `ARCHITECTURE`
- **Status**: `IMPLEMENTED` (Ref: `ADR-026`, `PR-CORP-023.md`)
- **Data de Descoberta**: 2026-11-22
- **Problema / Limitação Atual**: O arquivo `src/corporate_engineer/cli.py` atingiu 1661 linhas, concentrando o parsing de argumentos, formatação de saída e execução lógica de mais de 15 subcomandos (`audit`, `index`, `dag`, `mcp`, `eval`, `blast-radius`, `telemetry`, `test-surgical`, `decide`, `dataset`, `fix`, `clean`, `benchmark`, `swarm`, `prompt`, `run`). Isso viola as regras de design corporativo (limite suave de 800 linhas por arquivo), dificulta revisões de código e obriga o uso de imports tardios espalhados pelo arquivo.
- **Solução Proposta**:
  1. Criar o subpacote `src/corporate_engineer/cli/commands/`:
     - `cmd_audit.py`, `cmd_index.py`, `cmd_dag.py`, `cmd_mcp.py`, `cmd_swarm.py`, `cmd_run.py`, etc.
  2. Manter em `src/corporate_engineer/cli.py` (ou `cli/main.py`) apenas o parser central, configuração de subparsers e despacho limpo.
  3. Assegurar compatibilidade retroativa total de todos os subcomandos e argumentos existentes.
- **Benefícios Esperados**: Redução do tamanho do arquivo principal para <200 linhas, alta coesão e baixo acoplamento por subcomando, facilidade para adição de novos comandos sem risco de merge conflicts.
- **Componentes Afetados**: `src/corporate_engineer/cli.py`, `src/corporate_engineer/cli/commands/`, `tests/test_cli.py`.
- **Complexidade**: Média-Alta (M-L).
- **Riscos**: Quebra inadvertida de algum subcomando ou flag. Mitigação: suíte abrangente de testes CLI existentes (`tests/test_cli.py`) executada como gate antes e depois da refatoração.
- **Critérios de Aceite**: CLI decomposta em módulos dedicados, 100% dos testes CLI verdes sem quebra de interface e `cli.py` reduzido para <250 linhas.

---

### 🔹 IMP-0024: Gemini LoRA Modular Pipeline para Motion Graphics & Tool Calling (DarkFactory)
- **Categoria**: `CAPABILITY` | `INTELLIGENCE` | `QUALITY`
- **Status**: `IMPLEMENTED` (Ref: `ADR-020`, `PR-CORP-020.md`)
- **Data de Descoberta**: 2026-11-22
- **Problema / Limitação Atual**: O projeto DarkFactory necessitava de modelos capazes de gerar motion graphics de alta fidelidade visual (Remotion, Manim, Blender Python) e chamadas de ferramentas determinísticas para orquestração. O Gemini 3.8 Flash zero-shot genérico apresentava falhas esporádicas de sintaxe e interpolação. Faltava no framework um pipeline de dados especializado em preparar, validar e exportar datasets de fine-tuning (LoRA/PEFT) no formato canônico da Vertex AI.
- **Solução Proposta**:
  1. *Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)*:
     - `LoraDomain`: `MOTION_REMOTION`, `MOTION_MANIM`, `MOTION_BLENDER`, `TOOL_CALLING`.
     - `LoraTrainingSample`, `LoraDatasetConfig`, `LoraValidationReport`, `LoraExportResult`.
  2. *Gerador de Datasets Sintéticos (`src/corporate_engineer/lora/generator.py`)*:
     - Geração de templates com estética cyber-industrial da DarkFactory, curvas de mola (*spring mechanics*), interpolações e schemas JSON multi-turn.
  3. *Validador de Sintaxe & AST (`src/corporate_engineer/lora/validator.py`)*:
     - `ast.parse` para Python (Manim e Blender `bpy`), validação estrutural de TSX/JSX para Remotion e validação estrita de JSON Schema para Tool Calling.
  4. *Formatador e Exportador Vertex AI (`src/corporate_engineer/lora/exporter.py`)*:
     - Exportação em JSONL no padrão Google Cloud Vertex AI / AI Studio SFT com Zero-Secret Guard integrado (`[REDACTED_SECRET]`), particionamento determinístico 80/20 train/validation e estimativa de tokens.
  5. *CLI Corporativa (`src/corporate_engineer/cli.py`)*:
     - Subcomando `corporate-engineer lora` com ações `generate`, `validate` e `export`.
- **Benefícios Esperados**: Viabilidade real de especialização modular de LLMs leves (Gemini Flash) para geração de código de motion no nível de modelos de fronteira e orquestração de ferramentas 100% determinística.
- **Componentes Afetados**: `src/corporate_engineer/models.py`, `src/corporate_engineer/lora/`, `src/corporate_engineer/cli.py`, `tests/test_gemini_lora_pipeline.py`.
- **Complexidade**: Média-Alta (M-L).
- **Critérios de Aceite**: 29 testes unitários passando em `tests/test_gemini_lora_pipeline.py`, 0 erros Ruff/Mypy, Zero-Secret Guard ativo e CLI funcional.

---

### 🔹 IMP-0025: Autonomous Proactive Intelligence & Full E2E Lifecycle Hook Suite
- **Categoria**: `ORCHESTRATION` | `INTELLIGENCE` | `AUTOMATION` | `TRANSCENDENCE`
- **Status**: `IN_PROGRESS` (Ref: `ADR-023`)
- **Data de Descoberta**: 2026-11-22
- **Problema / Limitação Atual**: O projeto desenvolveu dezenas de componentes autônomos (prompt refiner, System 1 router, AST self-healing fixer, blast radius calculator, OTel tracer, safe storage cleaner, git link generator), mas muitos operavam sob demanda via CLI manual. Faltava integrá-los de forma 100% automática e contínua nos eventos de ciclo de vida do Antigravity (`SessionStart`, `PreInvocation`, `PreToolUse`, `PostToolUse`, `Stop`) e no Git local (`pre-commit`, `pre-push`), mantendo o orquestrador sempre 2 passos à frente.
- **Solução Proposta**:
  1. *Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)*:
     - `AnticipationStep`, `AnticipationPlan`.
  2. *Motor de Antecipação Proativa (`src/corporate_engineer/orchestrator/anticipator.py`)*:
     - `ProactiveAnticipator`: integra `ContextAwarePromptRefiner` e `SystemOneRouter`, formula passo +1 (imediato) e passo +2 (subsequente) e gera relatórios de orientação em tempo real.
  3. *Suíte de Hooks do Ciclo de Vida (`.agents/orchestration/hooks/`)*:
     - `session_start.py` (diagnóstico de saúde, disco via `SafeStorageCleaner`, branch e living state).
     - `proactive_advisor.py` (PreInvocation: inteligência 2 passos à frente e link PR 1-clique).
     - `pre_tool_security_guard.py` (PreToolUse: Zero-Secret Guard em `write_file|edit_file`).
     - `post_tool_auto_healer.py` (PostToolUse: AST self-healing fixer, ruff format e cálculo de blast radius).
     - `session_turnover_gate.py` (Stop: portão de integridade de `state.md`).
  4. *Ativação em `.agents/hooks.json`*:
     - Mapeamento oficial dos 5 hooks com isolamento e timeouts seguros.
  5. *Git Hooks Locais (`scripts/install_git_hooks.py`)*:
     - Instalação de hooks `pre-commit` e `pre-push` garantindo pre-flight limpo antes de qualquer commit ou push.
  6. *CLI Corporativa (`src/corporate_engineer/cli.py`)*:
     - Subcomando `corporate-engineer anticipate <prompt>`.
- **Benefícios Esperados**: Sistema completamente unificado, auto-reflexivo e proativo, antecipando riscos e dependências em tempo real.
- **Componentes Afetados**: `src/corporate_engineer/models.py`, `src/corporate_engineer/orchestrator/anticipator.py`, `.agents/orchestration/hooks/`, `.agents/hooks.json`, `scripts/install_git_hooks.py`, `src/corporate_engineer/cli.py`, `tests/test_proactive_pipeline.py`.
- **Complexidade**: Média-Alta (M-L).
- **Critérios de Aceite**: Suíte de testes TDD verde, 0 erros Ruff/Mypy, todos os 5 hooks testados com sucesso, pre-flight 100% aprovado.

---

### 🔹 IMP-0026: Tri-Phase Adversarial Loop (Red Team 1.5 → Transcendência 1.6 → Verificação 1.7)
- **Categoria**: `ORCHESTRATION` | `QUALITY` | `SECURITY` | `TRANSCENDENCE`
- **Status**: `IMPLEMENTED` (Ref: `ADR-028`, `PR-CORP-026.md`)
- **Data de Descoberta**: 2026-11-22
- **Problema / Limitação Atual**: O fluxo de planejamento atual (Fase 1) elabora planos e metaprompts que seguem diretamente para execução/delegação (Fase 4 e Swarm). Embora eficiente, esse design sofre com a sicoferência (*sycophancy*) dos LLMs: planos com premissas frágeis de rede, concorrência, permissões de ferramentas MCP ou edge cases patológicos são aceitos sem contestação agressiva. Quando despachados para um Swarm multi-agente, esses planos defeituosos geram desperdício de dezenas de milhares de tokens, conflitos no Fan-In e mocks ilusórios para forçar testes a passar.
- **Solução Proposta (Loop Dialético Tri-Fásico Always-On)**:
  1. *Fase 1.5 - Adversarial Red Team Attack (Passada 1)*:
     - Ataque agressivo ao plano arquitetural, DTOs e metaprompt antes de qualquer linha de código.
     - Executa modelagem de ameaças e estresse estrutural: premissas frágeis de performance, limites de concorrência/deadlocks, privilégios excessivos de ferramentas MCP, acoplamento e pontos únicos de falha (SPOF).
     - Emite `RedTeamAttackReport` com severidades (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) e lista de vulnerabilidades conceituais.
  2. *Fase 1.6 - Architecture Transcendence & Hardening (Transcendência)*:
     - Em vez de aplicar remendos pontuais (*band-aids*), o motor sintetiza e **transcende** os pontos fracos apontados pelo Red Team.
     - Eleva o nível de abstração: substitui pontos de falha por invariantes formais, estruturas imutáveis, fallbacks determinísticos, idempotência ou desacoplamento por camadas com contenção de blast radius.
     - Emite `TranscendencePlan` com matriz de resolução formal de cada vulnerabilidade.
  3. *Fase 1.7 - Adversarial Re-Verification (Passada 2)*:
     - O Red Team executa uma segunda passada atacando diretamente a síntese transcendida.
     - Valida se as vulnerabilidades críticas foram erradicadas sem introdução de complexidade acidental.
     - Emite o veredito final (`VERIFIED` ou `HARDEN_REQUIRED` com limite de 2 voltas) e gera a **Matriz Obrigatória de Chaos Tests** (cenários de falha e caminhos negativos que o `tdd-guide` DEVE implementar antes da codificação).
  4. *Integração Always-On com Hooks e Master Orchestrator*:
     - Acionamento automático pelo `ProactiveAnticipator` e `AutonomousEngineeringGraph.run_pipeline` quando o nível de risco for `HIGH` ou `CRITICAL`, ou quando houver alocação de `SwarmCoordinator`.
     - Fast-Path bypass automático via Sistema 1 para tarefas rotineiras de baixo risco (`LOW`), garantindo zero latência desnecessária.
     - Hook de pré-execução bloqueando despacho para Swarm sem selo `VERIFIED` da Fase 1.7.
- **Benefícios Esperados**: Eliminação do retrabalho por planos furados, economia de milhares de tokens no Swarm, geração automatizada de testes de caos para o TDD e arquiteturas à prova de bala por design dialético.
- **Componentes Afetados**:
  - `src/corporate_engineer/models.py` (`RedTeamVulnerability`, `RedTeamAttackReport`, `TranscendencePlan`, `ChaosTestCase`, `RedTeamVerdict`).
  - `src/corporate_engineer/orchestrator/adversarial.py` (`AdversarialRedTeam`, `ArchitectureTranscender`, `AdversarialLoopCoordinator`).
  - `src/corporate_engineer/orchestrator/graph.py` (injeção das fases 1.5, 1.6 e 1.7 no `run_pipeline`).
  - `src/corporate_engineer/orchestrator/swarm.py` (gate adversarial pré-fan-out).
  - `src/corporate_engineer/cli.py` (subcomando `corporate-engineer plan dialectic`).
  - `tests/test_adversarial_dialectical_loop.py`.
- **Complexidade**: Média-Alta (M-L).
- **Critérios de Aceite**: Suíte de testes TDD cobrindo ataque, transcendência e verificação, 0 erros Ruff/Mypy, integração com `run_pipeline` e bloqueio de despacho de swarm para planos com falhas críticas.

---

### 🔹 IMP-0027: Conexão Total de Módulos Desconectados, Unificação de Cache AST SHA-256 e Enriquecimento E2E
- **Categoria**: `ORCHESTRATION` | `EFFICIENCY` | `ARCHITECTURE` | `QUALITY` | `TRANSCENDENCE`
- **Status**: `IMPLEMENTED` (Ref: `ADR-025`, `PR-CORP-027.md`)
- **Data de Descoberta**: 2026-11-22 (via Swarm Max de Auditoria Técnica)
- **Problema / Limitação Atual**: O framework desenvolveu 25 melhorias de alta fidelidade, mas a auditoria concorrente com 4 agentes do Swarm Max revelou desconexões críticas: `BlastRadiusAnalyzer` re-parseava o repositório sem usar o `CachedASTCodebaseIndexer` (SHA-256); `AutonomousEngineeringGraph.run_pipeline` não consumia `ProactiveAnticipator`, `ASTSelfHealingFixer`, `SurgicalTestRunner`, `SemanticCodeEvaluator` nem `generate_pr_url` com push remoto; `QualityGateRunner` possuía scanner de segredos reduzido e desconectado de `SemanticCodeEvaluator` e `SafeStorageCleaner`; e pacotes com `__init__.py` omitiam exports públicos.
- **Solução Proposta**:
  1. *Unificação de Cache AST*: Conectar `CachedASTCodebaseIndexer` ao `BlastRadiusAnalyzer` e ao `ContextAwarePromptRefiner.find_ast_symbols()`.
  2. *Amarração no AutonomousEngineeringGraph.run_pipeline*: Acionar `ProactiveAnticipator` (PLANNING), `SurgicalTestRunner` (TDD), `ASTSelfHealingFixer` (IMPLEMENT), `SemanticCodeEvaluator` (AUDIT) e `generate_pr_url(ensure_pushed=True)` (DELIVER).
  3. *Unificação de Scanners e Gates*: Canonizar `SecretScanner` em `quality/` e enriquecer `QualityGateRunner`.
  4. *Limpeza e API Pública*: Exportar símbolos em `__init__.py` e remover código morto.
- **Benefícios Esperados**: Operação 100% sinérgica e unificada do framework, ganho substancial de desempenho em I/O e ciclo de vida autônomo completo de ponta a ponta.
- **Componentes Afetados**: `src/corporate_engineer/rag/impact.py`, `src/corporate_engineer/prompt/refiner.py`, `src/corporate_engineer/orchestrator/graph.py`, `src/corporate_engineer/quality/gate.py`, `src/corporate_engineer/models.py`, `src/corporate_engineer/__init__.py`.
- **Complexidade**: Média-Alta (M-L).
- **Critérios de Aceite**: Suíte de testes TDD verde, 0 erros Ruff/Mypy, `run_pipeline` acionando os motores unificados e pre-flight 100% aprovado.

---

### 🔹 IMP-0028: Resiliência Universal de Hooks do Ciclo de Vida e Ativação Permanente de Regras Always-On
- **Categoria**: `AUTOMATION` | `ARCHITECTURE` | `RELIABILITY`
- **Status**: `IMPLEMENTED` (Ref: `ADR-027`)
- **Data de Descoberta**: 2026-11-24
- **Problema / Limitação Atual**: Falhas de amnésia do sistema ocorriam por dois motivos: a regra principal `corp-pipeline-orchestrator.md` não continha o frontmatter `trigger: always_on`, impedindo sua injeção automática no contexto; e os comandos de hooks configurados em `.agents/hooks.json` usavam caminhos relativos ao subdiretório `.agents/`, falhando silenciosamente com `[Errno 2] No such file or directory` quando disparados a partir da raiz do repositório pelo Antigravity.
- **Solução Proposta**:
  1. *Ativação Always-On*: Inserção do frontmatter `trigger: always_on` no topo de `corp-pipeline-orchestrator.md`.
  2. *Dispatcher Universal de Hooks*: Criação de `.agents/orchestration/hooks/run_hook.py` capaz de resolver agnosticamente o workspace root, localizar o interpretador `.venv\Scripts\python.exe` e gerenciar execução in-process ou via subprocesso seguro.
  3. *Reconfiguração de Hooks*: Atualização de todos os 5 eventos em `.agents/hooks.json` (`SessionStart`, `PreInvocation`, `PreToolUse`, `PostToolUse`, `Stop`) para apontarem para o dispatcher universal.
- **Benefícios Esperados**: Eliminação completa de amnésia operacional, injeção de contexto garantida em 100% das sessões e resiliência total na execução de hooks.
- **Componentes Afetados**: `.agents/rules/corp-pipeline-orchestrator.md`, `.agents/orchestration/hooks/run_hook.py`, `.agents/hooks.json`, `tests/test_hook_resilience_and_rule_triggers.py`.
- **Complexidade**: Baixa-Média (S-M).
- **Critérios de Aceite**: 100% dos testes em `test_hook_resilience_and_rule_triggers.py` passando, 0 erros Ruff/Mypy, hooks executando sem erro.

---

### 🔹 IMP-0029: Continuous Capability Auto-Wiring & Invariante de Potência Máxima (Zero Código Órfão)
- **Categoria**: `QUALITY` | `ARCHITECTURE` | `ORCHESTRATION` | `TRANSCENDENCE`
- **Status**: `IMPLEMENTED` (Ref: `ADR-029`, `PR-CORP-029.md`)
- **Data de Descoberta**: 2026-11-24
- **Problema / Limitação Atual**: Módulos e recursos recém-criados corriam o risco de permanecer desconectados (sem re-exportação em `__init__.py`, sem flags na CLI, sem testes associados ou sem integração ao pipeline autônomo), gerando "dívida de desconexão" e operando abaixo do potencial máximo.
- **Solução Proposta**:
  1. *Invariante 9*: Estabelecer no `AGENTS.md` e `GEMINI.md` a regra mandatória de que toda nova implementação deve estar conectada nos 5 elos (contratos DTO, exportação pública, CLI, prompt refiner e pipeline autônomo).
  2. *Auditor Estático de Auto-Conexão*: Implementar `CapabilityWiringAuditor` em `src/corporate_engineer/quality/wiring_auditor.py` para verificar AST, imports, exports públicos, cobertura de testes e orfandade de código.
  3. *CLI Flag e Pipeline Integration*: Adicionar flag `--wiring` ao comando `audit` e acoplar a verificação ao `QualityGateRunner` e à fase de `AUDIT` do `AutonomousEngineeringGraph.run_pipeline`.
  4. *Auto-Conexão Ativa*: Conectar e exportar todos os 9 módulos que estavam desconectados em `orchestrator`, `quality`, `system_one` e no módulo raiz.
- **Benefícios Esperados**: Garantia automatizada de 100% de potência em todas as capacidades do framework, zero módulos órfãos e feedback preventivo imediato no pre-flight.
- **Componentes Afetados**: `src/corporate_engineer/models.py`, `src/corporate_engineer/quality/wiring_auditor.py`, `src/corporate_engineer/quality/gate.py`, `src/corporate_engineer/cli/commands/quality.py`, `src/corporate_engineer/orchestrator/graph.py`, `AGENTS.md`, `GEMINI.md`, `.agents/rules/corporate-quality-gate.md`, `tests/test_auto_wiring_integrity.py`.
- **Complexidade**: Média-Alta (M-L).
- **Critérios de Aceite**: 100% dos testes em `test_auto_wiring_integrity.py` passando, comando `audit --wiring` validando 0 módulos desconectados, pre-flight 100% aprovado.

---

### 🔹 IMP-0030: Resiliência de Concorrência, Sincronização & Eliminação de Erros Silenciosos (Pacote 1)
- **Categoria**: `RELIABILITY` | `ARCHITECTURE` | `ORCHESTRATION`
- **Status**: `IMPLEMENTED` (Ref: `ADR-030`, `PR-CORP-030.md`)
- **Data de Descoberta**: 2026-11-24
- **Problema / Limitação Atual**: A auditoria sênior identificou vulnerabilidades críticas em protocolos e concorrência:
  1. `git_utils.py:158-171`: `is_branch_pushed()` retorna `True` quando `git rev-parse` falha com erro não-zero, falsificando sincronização com origin.
  2. `mcp/client.py:255-273`: `call_tool()` no cliente SSE extrai `res.get("result", {}).get("isError")`, mas erros JSON-RPC 2.0 vêm na chave raiz `error`, fazendo com que erros do servidor MCP sejam reportados como sucesso (`is_error=False`).
  3. `orchestrator/swarm.py:95-133, 189-196`: `dispatch_task()` inicializa `success = True` e nunca atualiza para `False` quando a chamada falha, fazendo `run_fan_out()` aprovar deliberações mesmo com falhas de ferramentas.
  4. `telemetry/tracer.py:44-56`: `AgentTracer` usa `threading.local` para `_active_stack`, causando vazamento de contexto e corrupção de hierarquia entre coroutines assíncronas concorrentes na mesma thread.
  5. `mcp/hub.py:22-147`: Falta de travas de concorrência (`_lock`) causando race conditions e `RuntimeError` durante iteração/modificação simultânea de servidores e ferramentas por múltiplos agentes.
  6. `orchestrator/swarm.py:44`: Uso de `threading.Lock` não-reentrante ao invés de `threading.RLock`.
- **Solução Proposta**:
  1. Validar `proc_head.returncode != 0` em `is_branch_pushed()` retornando `False` com warning explicativo.
  2. Inspecionar envelope de erro `if "error" in res:` no cliente MCP, marcando `is_error=True`.
  3. Setar `success = False` em `dispatch_task()` do Swarm quando a ferramenta falhar e checar `r.success and not r.error` em `run_fan_out()`.
  4. Migrar `_active_stack` no `AgentTracer` de `threading.local` para `contextvars.ContextVar`.
  5. Implementar `self._lock = threading.RLock()` em `MCPEnterpriseHub` e migrar `SwarmCoordinator` para `RLock`.
- **Benefícios Esperados**: Concorrência 100% thread-safe e async-safe, eliminação de falsos sucessos operacionais e garantia estrita do protocolo de push remoto.
- **Componentes Afetados**: `src/corporate_engineer/git_utils.py`, `src/corporate_engineer/mcp/client.py`, `src/corporate_engineer/mcp/hub.py`, `src/corporate_engineer/orchestrator/swarm.py`, `src/corporate_engineer/telemetry/tracer.py`.
- **Complexidade**: Média-Alta (M-L).
- **Critérios de Aceite**: Suíte TDD cobrindo todos os cenários com 100% PASS, 0 erros de linter e tipagem estrita.

---

### 🔹 IMP-0031: Blindagem de Qualidade, Segurança & Sandboxing de Mutação (Pacote 2)
- **Categoria**: `QUALITY` | `SECURITY`
- **Status**: `SAVED_NOT_APPROVED`
- **Data de Descoberta**: 2026-11-24
- **Problema / Limitação Atual**: O sandbox temporário de mutação omite `src/` do PYTHONPATH, testando código não-mutado; o scanner de segredos possui bypass para chaves de projeto da OpenAI (`sk-proj-...` com `_`) e Anthropic (`sk-ant-api03-...`); o Storage Cleaner julga raízes de disco (`C:\`, `/`) e diretório home como seguros para deleção; a re-verificação da Fase 1.7 Adversarial é mockada sem ataque real.
- **Solução Proposta**: Injetar `src/` no PYTHONPATH do sandbox de mutação; corrigir regexes no scanner de segredos; bloquear estritamente raízes de sistema no Storage Cleaner; implementar re-verificação real de endurecimentos no Adversarial Red Team.
- **Benefícios Esperados**: Blindagem contra acidentes catastróficos no SO, eficácia real dos testes de mutação e erradicação de falsos negativos em vazamentos de credenciais.
- **Componentes Afetados**: `src/corporate_engineer/quality/mutation.py`, `src/corporate_engineer/quality/secret_scanner.py`, `src/corporate_engineer/quality/storage_cleaner.py`, `src/corporate_engineer/orchestrator/adversarial.py`.
- **Complexidade**: Média-Alta (M-L).
- **Critérios de Aceite**: Testes unitários validando cada guardrail de segurança com 100% PASS.

---

### 🔹 IMP-0032: Integridade da CLI, Output Contratos & Dynamic Hook Dispatching (Pacote 3)
- **Categoria**: `ARCHITECTURE` | `AUTOMATION`
- **Status**: `SAVED_NOT_APPROVED`
- **Data de Descoberta**: 2026-11-24
- **Problema / Limitação Atual**: O `run_hook.py` possui whitelist estática rejeitando hooks dinâmicos em `.venv`; comandos CLI vazam texto informativo no `stdout` quando `--format json` é solicitado com `--output`; o comando `eval` aprova diretórios inexistentes com nota 100%; o comando `mcp` sem ação retorna 0 silenciosamente.
- **Solução Proposta**: Implementar descoberta dinâmica de hooks via `runpy.run_path`; redirecionar logs informativos para `sys.stderr` em saídas JSON; validar existência de alvos em `eval`; tornar subcomando `mcp` obrigatório.
- **Benefícios Esperados**: Conformidade estrita com padrões POSIX CLI, usabilidade e suporte universal a qualquer hook de ciclo de vida.
- **Componentes Afetados**: `.agents/orchestration/hooks/run_hook.py`, `src/corporate_engineer/cli/commands/rag.py`, `src/corporate_engineer/cli/commands/mcp.py`, `src/corporate_engineer/cli/commands/prompt.py`.
- **Complexidade**: Média (M).
- **Critérios de Aceite**: Testes CLI cobrindo saídas JSON válidas, exit codes corretos e disparo dinâmico de hooks.

---

### 🔹 IMP-0033: AI Systems, RAG Cache Starvation & Unificação de Dívidas Técnicas (Pacote 4)
- **Categoria**: `EFFICIENCY` | `MAINTAINABILITY`
- **Status**: `SAVED_NOT_APPROVED`
- **Data de Descoberta**: 2026-11-24
- **Problema / Limitação Atual**: Em `CachedASTCodebaseIndexer.get_all_symbol_names()`, se um arquivo está em cache, o rastreamento da base inteira é pulado; a acurácia no Benchmark divide por `successful_runs` ao invés de `total_runs`; o validador LoRA de Remotion confunde generics TS com JSX unclosed tags; `prompt/refiner.py` mantém referência ao monólito deletado `cli.py`.
- **Solução Proposta**: Corrigir starvation de cache AST; corrigir fórmula de acurácia estatística no Benchmark; aprimorar regex de tags JSX em Remotion; limpar referências a arquivos mortos e unificar helpers de formatação CLI.
- **Benefícios Esperados**: Precisão do índice AST, métricas confiáveis de benchmark e eliminação de dívidas técnicas acumuladas.
- **Componentes Afetados**: `src/corporate_engineer/rag/cached_ast_indexer.py`, `src/corporate_engineer/system_one/benchmark.py`, `src/corporate_engineer/lora/validator.py`, `src/corporate_engineer/prompt/refiner.py`.
- **Complexidade**: Média-Alta (M-L).
- **Critérios de Aceite**: Testes de RAG e benchmark aprovados, zero referências obsoletas.













