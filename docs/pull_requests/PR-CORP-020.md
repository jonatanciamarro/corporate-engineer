# PR-CORP-020: Blindagem de Concorrência & Thread-Safety no Swarm, Circuit Breaker e Tracer (RLock & Precedência OTel)

## Tipo de Mudança
- [x] `fix`: Correção de bug / race condition
- [x] `feat`: Nova capacidade / blindagem de segurança
- [ ] `refactor`: Refatoração estrutural sem alteração de comportamento externo
- [x] `test`: Novos testes automatizados (Shift-Left TDD)
- [x] `docs`: Atualização de documentação e ADR

## Ticket / ID da Proposta
- **ID**: `IMP-0020`
- **Referência ADR**: [ADR-021](../../docs/adr/ADR-021-concurrency-thread-safety-swarm-tracer.md)
- **Status do Backlog**: `IMPLEMENTED`

---

## Descrição do Pull Request

Este Pull Request implementa a blindagem arquitetural de concorrência e thread-safety em múltiplos subsistemas corporativos após detecção de vulnerabilidades críticas na auditoria técnica profunda via Swarm (`relatorio_auditoria_swarm.md`):

1. **CircuitBreaker Thread-Safe com RLock e Monotonic Time (`src/corporate_engineer/mcp/circuit_breaker.py`)**:
   - Inclusão de `self._lock = threading.RLock()` protegendo atomicamente todas as transições de estado (`CLOSED`, `OPEN`, `HALF_OPEN`) e contadores.
   - Migração completa de `time.time()` para `time.monotonic()` para imunidade contra ajustes de relógio do sistema (NTP).

2. **AgentTracer Thread-Safe e Desduplicação de Tokens (`src/corporate_engineer/telemetry/tracer.py`)**:
   - Inclusão de `self._lock = threading.RLock()` garantindo integridade das pilhas e lista de spans em execuções multi-thread paralelas.
   - Resolução de ordem de precedência estrita no cálculo de tokens em `export_trace()`:
     - `gen_ai.usage.total_tokens` (prioritário);
     - `tokens` (legado);
     - Soma de `gen_ai.usage.prompt_tokens` + `gen_ai.usage.completion_tokens`.
   - Elimina duplicação contábil quando spans contêm múltiplas chaves de métricas simultâneas.

3. **SwarmCoordinator com Mutações Protegidas (`src/corporate_engineer/orchestrator/swarm.py`)**:
   - Inclusão de `self._lock = threading.Lock()` para orquestração de transição de status de membros (`WORKING`, `COMPLETED`, `FAILED`) em despachos paralelos com `ThreadPoolExecutor`.

4. **Suíte Abrangente de Shift-Left TDD (`tests/test_concurrency_thread_safety.py`)**:
   - 15 novos testes unitários e de estresse cobrindo 50 threads concorrentes em CircuitBreaker, 20 workers em AgentTracer, desduplicação de tokens e paralelismo real no SwarmCoordinator.
   - Suíte global expandida para **234/234 testes PASS** em 20.75s.

---

## Verificações de Pre-Flight (100% Aprovadas)

- [x] **Testes Automatizados**: `pytest` (234/234 PASS)
- [x] **Linter & Formatação**: `ruff check .` e `ruff format --check .` (0 erros)
- [x] **Tipagem Estática**: `mypy .` (0 erros em 70 arquivos)
- [x] **Pre-Flight Secret Scan**: `secret_scanner.py` (0 vazamentos)
