# ADR-007: OpenTelemetry Agent Tracing & Span Telemetry (OTel LLMOps)

## Status
Aceito (Accepted)

## Data
2026-11-20

## Contexto & Motivação
Em sistemas autônomos de engenharia de software corporativa compostos por múltiplos agentes (Core Orchestrator, subagentes especializados, MCP tools e DAGs de execução paralela), a falta de telemetria estruturada gera o que o setor chama de *Observability Gap*:
1. Bugs distribuídos e falhas silenciosas de nós de agentes são difíceis de reproduzir sem contexto de span e parentesco.
2. Dificuldade de identificar gargalos de latência (tempo gasto em I/O, subprocessos locais vs latência de streaming MCP).
3. Ausência de auditoria unificada sobre consumo de tokens e custos por tarefa e por nó.

Conforme preconizado pelo relatório *Deep Research AI Software Engineering 2026*, sistemas modernos de agentes devem adotar o padrão **OpenTelemetry (OTel)** e as convenções semânticas de GenAI (`gen_ai.system`, `gen_ai.operation.name`, `gen_ai.usage.input_tokens`, etc.) para rastreamento ponta a ponta.

## Decisão de Arquitetura

1. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `AgentSpan`: Modela um span individual compatível com OTel (`trace_id`, `span_id`, `parent_span_id`, `name`, `start_time_iso`, `end_time_iso`, `duration_ms`, `status`, `attributes`, `events`, `error_message`).
   - `TraceReport`: Agrega todos os spans de uma execução, calculando latência agregada, total de tokens, visualização hierárquica e status global.

2. **Módulo de Telemetria (`src/corporate_engineer/telemetry/`)**:
   - `AgentTracer`: Gerenciador de rastreamento com suporte a context managers (`with tracer.span(...)`), criação hierárquica de spans raiz e filhos, timestamps precisos em UTC e convenções semânticas de GenAI.
   - Suporte a exportação local em JSON compatível com OTel e coletores de telemetria (ex.: Arize Phoenix, LangSmith, OTel Collector).

3. **Integração com Orquestrador DAG (`src/corporate_engineer/orchestrator/graph.py`)**:
   - Cada nó executado pelo `AutonomousEngineeringGraph` (sequencial ou em paralelo via `execute_parallel_tasks`) é instrumentado como um span filho do trace ativo, gravando status, duração e erros.

4. **Integração na CLI Corporativa (`src/corporate_engineer/cli.py`)**:
   - Adicionado subcomando `telemetry` para inspecionar traces e visualização em árvore cascata de latência/tokens.
   - Adicionada flag `--trace` ao subcomando `dag` para emitir telemetria do fluxo de orquestração.

## Consequências
- **Positivas**:
  - Visibilidade e rastreabilidade total de cada etapa executada pelos agentes e ferramentas.
  - Compatibilidade imediata com ecossistemas OTel e observabilidade enterprise.
  - Baixo overhead, sem dependências externas obrigatórias (implementado nativamente sobre a biblioteca padrão e Pydantic v2).
- **Limitações Mitigadas**:
  - Estrutura projetada para serialização assíncrona/em lote, sem impactar a performance crítica dos nós de computação.
