# ADR-021: Blindagem de Concorrência & Thread-Safety no Swarm e Tracer

## Status
Aceito (Accepted)

## Data
2026-11-22

## Contexto & Motivação
A auditoria técnica profunda realizada no repositório `corporate-engineer` via Swarm identificou pontos críticos de risco de concorrência e integridade em execuções multi-thread paralelas:
1. **CircuitBreaker Sem Sincronização (`src/corporate_engineer/mcp/circuit_breaker.py`)**:
   As transições de estado (`CLOSED`, `OPEN`, `HALF_OPEN`), contadores de falhas/sucessos e checagens em `can_execute()` não dispunham de travas de thread (`threading.RLock`), possibilitando *race conditions* e *state drift* quando múltiplos workers ou clientes MCP concorrentes interagem com o mesmo disjuntor. Adicionalmente, o uso de `time.time()` expunha o disjuntor a imprecisões decorrentes de ajustes de relógio do sistema (NTP).
2. **AgentTracer Concorrente e Duplicação de Tokens (`src/corporate_engineer/telemetry/tracer.py`)**:
   A manipulação das estruturas `spans` e da pilha `_active_stack` não era protegida contra acessos paralelos simultâneos em nós do DAG ou no Swarm. Além disso, a agregação de métricas em `export_trace()` iterava sobre chaves de contagem sem precedência exclusiva, somando simultaneamente `tokens` e `gen_ai.usage.total_tokens` presentes no mesmo span, inflando a contabilidade de consumo de tokens em até 100%.
3. **SwarmCoordinator e Mutações de Estado (`src/corporate_engineer/orchestrator/swarm.py`)**:
   Em `dispatch_task()`, mutações no status de `SwarmMember` (`member.status = "WORKING" / "COMPLETED"`) eram disparadas em threads paralelas sem sincronização explícita.

A iniciativa **IMP-0020** estabelece a blindagem arquitetural completa de concorrência com bloqueios reentrantes (`RLock`), temporização monotônica imune a desvios de relógio e resolução de precedência estrita na contabilidade de tokens OpenTelemetry.

## Decisão de Arquitetura

1. **Proteção Reentrante no CircuitBreaker (`src/corporate_engineer/mcp/circuit_breaker.py`)**:
   - Inclusão de `self._lock = threading.RLock()`.
   - Todas as transições de estado e verificações em `state`, `can_execute`, `record_success`, `record_failure`, `execute` e `reset` são protegidas com `with self._lock:`.
   - Migração completa de `time.time()` para `time.monotonic()` para controle de tempo decorrido no disjuntor.

2. **Thread-Safety e Desduplicação de Tokens no AgentTracer (`src/corporate_engineer/telemetry/tracer.py`)**:
   - Inclusão de `self._lock = threading.RLock()` para proteger `start_span`, `end_span`, `export_trace` e `clear`.
   - Controle seguro da pilha de spans ativos `_active_stack` por contexto de execução, prevenindo `IndexError` ou corrupção de hierarquia pai-filho em execuções concorrentes.
   - Refatoração do cálculo de `total_tokens` em `export_trace()` com ordem estrita de precedência:
     1. Se `gen_ai.usage.total_tokens` estiver presente, utiliza seu valor e interrompe (`break`).
     2. Caso contrário, se `tokens` estiver presente, utiliza seu valor e interrompe (`break`).
     3. Caso contrário, avalia e soma `gen_ai.usage.prompt_tokens` e `gen_ai.usage.completion_tokens`.

3. **Coordenação Concorrente no SwarmCoordinator (`src/corporate_engineer/orchestrator/swarm.py`)**:
   - Inclusão de `self._lock = threading.Lock()` para orquestração de despacho e atualização atômica de status dos membros durante `dispatch_task` e `run_fan_out`.

4. **Shift-Left TDD (`tests/test_concurrency_thread_safety.py`)**:
   - Teste de estresse do `CircuitBreaker` sob concorrência de 50 threads em disputa.
   - Teste de paralelismo do `AgentTracer` com 20 workers gerando spans concorrentes.
   - Teste de regressão contábil comprovando que spans com múltiplos atributos de tokens registram apenas contagem única correta.
   - Teste de fan-out thread-safe no `SwarmCoordinator`.

## Consequências

- **Positivas**:
  - Eliminação comprovada de race conditions e corrupção de estado em ambientes multi-thread.
  - Imunidade a saltos de relógio de sistema/NTP através de `time.monotonic()`.
  - Métricas contábeis de telemetria OTel 100% precisas, sem duplicação de tokens.
  - Compatibilidade retroativa integral com todos os métodos, contratos e interfaces existentes.
- **Negativas / Riscos**:
  - Leve sobrecarga de sincronização inerente aos bloqueios `RLock`, mitigada pelo escopo mínimo e atômico das seções críticas.
