# Pull Request: feat: add opentelemetry agent tracing and span telemetry engine (IMP-0009)

## 📋 Identificação da Demanda
- **Ticket / Issue**: `IMP-0009` (Ref: `CORP-007`)
- **Tipo**: `feat`
- **Módulos Afetados**:
  - `src/corporate_engineer/models.py`
  - `src/corporate_engineer/telemetry/tracer.py`
  - `src/corporate_engineer/telemetry/__init__.py`
  - `src/corporate_engineer/orchestrator/graph.py`
  - `src/corporate_engineer/cli.py`
  - `docs/adr/ADR-007-opentelemetry-agent-tracing.md`
  - `.agents/orchestration/improvement-backlog.md`
  - `tests/test_telemetry.py`
  - `state.md`
- **Classificação de Risco**: `[x] Baixo` | `[ ] Médio` | `[ ] Alto` | `[ ] Crítico`
- **Branch**: `feat/IMP-0009-opentelemetry-agent-tracing` ➔ `main`

---

## 🎯 Resumo Executivo da Mudança

Esta entrega implementa formalmente a proposta **`IMP-0009`** do backlog contínuo de melhorias (`improvement-backlog.md`), introduzindo o motor de **OpenTelemetry Agent Tracing & Span Telemetry (OTel LLMOps)** no framework `corporate-engineer`.

O sistema viabiliza observabilidade em nível de produção para fluxos de engenharia de software autônoma com agentes de IA. Ele rastreia hierarquias de execução (pais e filhos), latência de cada etapa, chamadas de subagentes, consumo de tokens (`gen_ai.usage.*`) e captura granular de falhas e exceções em conformidade com as convenções semânticas de GenAI do OpenTelemetry.

### Principais Entregas:
1. **Modelos DTO Pydantic v2 (`src/corporate_engineer/models.py`)**:
   - `AgentSpan`: Contrato fortemente tipado para spans OTel (`trace_id` de 32-hex, `span_id` de 16-hex, `parent_span_id`, `name`, `start_time_iso`, `end_time_iso`, `duration_ms`, `status`: `OK` | `ERROR`, `error_message`, `attributes`).
   - `TraceReport`: Contrato consolidado agregando métricas de trace (`trace_id`, `root_span_name`, `total_spans`, `total_duration_ms`, `total_tokens`, `spans`, `status`).

2. **Motor OpenTelemetry Tracer (`src/corporate_engineer/telemetry/tracer.py`)**:
   - Classe `AgentTracer` com suporte a `start_span`, `end_span` e context manager `with tracer.span(name, attributes)`.
   - Gerenciamento automático de pilha de escopo ativo (`_active_stack`) garantindo herança pai-filho sem necessidade de passar manualmente IDs de span.
   - Medição de duração de alta resolução com `time.monotonic()` e `datetime.UTC`.
   - Exportação estruturada para JSON (`export_json`) com persistência em disco.

3. **Integração no Grafo de Orquestração (`src/corporate_engineer/orchestrator/graph.py`)**:
   - `AutonomousEngineeringGraph` agora instancia um `AgentTracer` por execução.
   - Instrumentação nativa de etapas do DAG: `step_plan`, `step_tdd`, `step_review` e tarefas paralelas em `execute_parallel_tasks`.
   - Método `get_trace_report()` para extração instantânea do relatório consolidado de telemetria do grafo.

4. **Integração na CLI Corporativa (`src/corporate_engineer/cli.py`)**:
   - Adicionada flag `--trace` ao subcomando `corporate-engineer dag`, gerando resumo visual de traces após a execução.
   - Novo subcomando dedicado `corporate-engineer telemetry --file <path> [--format text|json]`, permitindo inspecionar e renderizar relatórios salvos de traces.

5. **Arquitetura Formal (ADR-007)**:
   - Formalizada em `docs/adr/ADR-007-opentelemetry-agent-tracing.md`.

---

## 🧪 Evidências de Teste (Shift-Left TDD)

- [x] **Certificação RED**: Testes em `tests/test_telemetry.py` foram criados previamente e falharam antes da implementação.
- [x] **Certificação GREEN**: 100% dos testes aprovados após a implementação.
- [x] **Expansão da Suíte**: De 88 para **94 testes passando** em 11.49s.
- [x] **Cobertura Global**: **90%** de cobertura de código (`pytest-cov`).

---

## 🛡️ Quality Gate & Pre-Flight Verification

- [x] **Unit & PBT Tests**: 94/94 PASS (`pytest`)
- [x] **Code Linter**: 0 violações (`ruff check .`)
- [x] **Code Formatter**: 56 arquivos verificados e formatados (`ruff format --check .`)
- [x] **Static Type Checker**: 0 erros em 34 arquivos (`mypy .`)
- [x] **Secret Scanner**: 0 credenciais ou tokens expostos (`secret_scanner.py`)
