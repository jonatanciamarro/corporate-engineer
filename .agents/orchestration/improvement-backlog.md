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
| `IMP-0017` | GitHub Actions Workflow de Auto-Remediação em PRs (`self-heal.yml`) | `AUTOMATION` | Baixa-Média (S-M) | `SAVED_NOT_APPROVED` | `2026-11-22` |
| `IMP-0018` | Context-Aware Metaprompt Engine & Prompt Refiner | `INTELLIGENCE` | Média (M) | `IMPLEMENTED` | `2026-11-22` |

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






