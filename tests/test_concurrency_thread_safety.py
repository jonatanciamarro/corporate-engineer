"""
Suíte Shift-Left TDD para Validação de Concorrência e Thread-Safety (IMP-0020 / ADR-021).

Testes cobrindo:
1. CircuitBreaker sob alta concorrência (50 threads), transições atômicas via threading.RLock,
   imunidade a desvios de relógio com time.monotonic().
2. AgentTracer sob concorrência multi-worker (20 threads), isolamento de pilha ativa,
   prevenção de race conditions e integridade de hierarquia de spans pai-filho.
3. AgentTracer.export_trace com ordem de precedência estrita para contabilidade de tokens
   (eliminação de contagem duplicada).
4. SwarmCoordinator.run_fan_out sob paralelismo concorrente real com mutação thread-safe.
"""

from __future__ import annotations

import concurrent.futures
import threading
import time
from typing import Any

import pytest

from corporate_engineer.mcp.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
)
from corporate_engineer.orchestrator.swarm import SwarmCoordinator
from corporate_engineer.telemetry.tracer import AgentTracer

# ============================================================================
# 1. Testes de Concorrência & Thread-Safety no CircuitBreaker
# ============================================================================


def test_circuit_breaker_has_reentrant_lock() -> None:
    """Verifica que o CircuitBreaker inicializa e utiliza um threading.RLock para sincronização."""
    cb = CircuitBreaker(failure_threshold=5, recovery_timeout=1.0)
    assert hasattr(cb, "_lock"), "CircuitBreaker deve possuir atributo de trava `_lock`"
    # threading.RLock é uma factory function que retorna _RLock
    assert isinstance(cb._lock, type(threading.RLock())), (
        "O atributo _lock do CircuitBreaker deve ser uma instância de threading.RLock"
    )


def test_circuit_breaker_concurrent_failures_atomicity() -> None:
    """
    Executa 50 threads concorrentes chamando `record_failure` simultaneamente.
    Garante que não há lost updates no contador de falhas e o estado transiciona para OPEN.
    """
    total_threads = 50
    cb = CircuitBreaker(failure_threshold=total_threads, recovery_timeout=10.0)
    barrier = threading.Barrier(total_threads)

    def worker_fail() -> None:
        barrier.wait()
        cb.record_failure()

    threads = [threading.Thread(target=worker_fail) for _ in range(total_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    assert cb.failure_count == total_threads, (
        f"Esperado {total_threads} falhas registradas atomicamente, obtido {cb.failure_count}"
    )
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False


def test_circuit_breaker_high_concurrency_state_machine() -> None:
    """
    50 threads executando operações concorrentes variadas (can_execute, record_failure,
    record_success, state) simultaneamente sem gerar corrupção ou deadlock.
    """
    num_threads = 50
    cb = CircuitBreaker(failure_threshold=10, recovery_timeout=0.05)
    barrier = threading.Barrier(num_threads)
    observed_states: list[CircuitState] = []
    lock = threading.Lock()

    def mixed_worker(worker_id: int) -> None:
        barrier.wait()
        for i in range(20):
            st = cb.state
            with lock:
                observed_states.append(st)

            if worker_id % 3 == 0:
                cb.record_failure()
            elif worker_id % 3 == 1:
                cb.record_success()
            else:
                _ = cb.can_execute()

            if i == 10:
                time.sleep(0.01)

    threads = [threading.Thread(target=mixed_worker, args=(i,)) for i in range(num_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)

    assert len(observed_states) == num_threads * 20
    assert all(isinstance(s, CircuitState) for s in observed_states)
    assert cb.state in (CircuitState.CLOSED, CircuitState.OPEN, CircuitState.HALF_OPEN)


def test_circuit_breaker_monotonic_time_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verifica que o CircuitBreaker calcula tempos com base em time.monotonic(),
    garantindo imunidade contra retrocessos de relógio de sistema (NTP drift).
    """
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1.0)
    cb.record_failure()
    assert cb.state == CircuitState.OPEN

    # Simula retrocesso drástico de relógio de parede no sistema (time.time recua 1000s)
    # Se estivesse usando time.time(), o disjuntor travaria eternamente em OPEN.
    monkeypatch.setattr(time, "time", lambda: 1000.0)

    # Com tempo monotônico avançado artificialmente por monotonic mock
    fake_mono = time.monotonic() + 2.0
    monkeypatch.setattr(time, "monotonic", lambda: fake_mono)

    assert cb.can_execute() is True
    assert cb.state == CircuitState.HALF_OPEN


def test_circuit_breaker_concurrent_execute_wrapper() -> None:
    """
    Executa 20 threads concorrentes através do método `execute()`,
    assegurando que nenhuma chamada levanta CircuitBreakerOpenError quando fechado.
    """
    cb = CircuitBreaker(failure_threshold=10, recovery_timeout=1.0)
    counter = 0
    counter_lock = threading.Lock()

    def work(val: int) -> int:
        nonlocal counter
        with counter_lock:
            counter += 1
        return val * 2

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(cb.execute, work, i) for i in range(40)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == 40
    assert counter == 40
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


# ============================================================================
# 2. Testes de Concorrência & Thread-Safety no AgentTracer
# ============================================================================


def test_agent_tracer_has_reentrant_lock() -> None:
    """Verifica que o AgentTracer inicializa e utiliza um threading.RLock para sincronização."""
    tracer = AgentTracer()
    assert hasattr(tracer, "_lock"), "AgentTracer deve possuir atributo de trava `_lock`"
    assert isinstance(tracer._lock, type(threading.RLock())), (
        "O atributo _lock do AgentTracer deve ser uma instância de threading.RLock"
    )


def test_agent_tracer_concurrent_spans_multiple_threads() -> None:
    """
    20 workers simultâneos gerando spans concorrentemente com hierarquia pai-filho.
    Garante que a pilha de spans ativos não seja corrompida entre threads e
    a coleção de spans permaneça íntegra sem lançar IndexError ou atribuir pais incorretos.
    """
    num_workers = 20
    tracer = AgentTracer(service_name="test-concurrent-tracer")
    barrier = threading.Barrier(num_workers)
    thread_spans: dict[int, list[str]] = {i: [] for i in range(num_workers)}

    def worker_run(worker_id: int) -> None:
        barrier.wait()
        parent_name = f"worker.{worker_id}.root"
        child_name = f"worker.{worker_id}.task"

        with tracer.span(parent_name, attributes={"worker_id": worker_id}) as p_span:
            thread_spans[worker_id].append(p_span.span_id)
            time.sleep(0.005)
            with tracer.span(child_name, attributes={"worker_id": worker_id}) as c_span:
                thread_spans[worker_id].append(c_span.span_id)
                time.sleep(0.005)

    threads = [threading.Thread(target=worker_run, args=(i,)) for i in range(num_workers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10.0)

    report = tracer.export_trace()
    # Esperado: 20 pais + 20 filhos = 40 spans
    assert report.total_spans == num_workers * 2
    assert len(tracer.spans) == num_workers * 2

    # Verifica integridade de cada par pai-filho criado por cada worker
    spans_by_id = {s.span_id: s for s in report.spans}
    for w_id in range(num_workers):
        p_id, c_id = thread_spans[w_id]
        parent_span = spans_by_id[p_id]
        child_span = spans_by_id[c_id]

        assert parent_span.parent_span_id is None, (
            f"Worker {w_id}: Root span {p_id} não deveria ter parent_span_id"
        )
        assert child_span.parent_span_id == p_id, (
            f"Worker {w_id}: Child span {c_id} deveria apontar para parent {p_id}, "
            f"mas aponta para {child_span.parent_span_id}"
        )
        assert parent_span.attributes.get("worker_id") == w_id
        assert child_span.attributes.get("worker_id") == w_id


# ============================================================================
# 3. Testes de Deduplicação de Tokens e Precedência em AgentTracer.export_trace
# ============================================================================


def test_agent_tracer_export_trace_precedence_total_tokens_over_tokens() -> None:
    """
    Quando um span possui `gen_ai.usage.total_tokens` e `tokens` simultaneamente,
    apenas `gen_ai.usage.total_tokens` deve ser contabilizado, eliminando a soma duplicada.
    """
    tracer = AgentTracer()
    span = tracer.start_span("agent.call")
    # Caso real de telemetria onde duas bibliotecas inserem a contagem
    span.attributes["gen_ai.usage.total_tokens"] = 150
    span.attributes["tokens"] = 100
    tracer.end_span(span)

    report = tracer.export_trace()
    # Sem a correção, o tracer somava 150 + 100 = 250
    assert report.total_tokens == 150, (
        f"Esperado 150 tokens pela precedência de `gen_ai.usage.total_tokens`, obtido {report.total_tokens}"
    )


def test_agent_tracer_export_trace_precedence_tokens_over_prompt_and_completion() -> None:
    """
    Quando um span não possui `gen_ai.usage.total_tokens`, mas possui `tokens` e também
    `gen_ai.usage.prompt_tokens` / `completion_tokens`, utiliza `tokens` com precedência.
    """
    tracer = AgentTracer()
    span = tracer.start_span("agent.call")
    span.attributes["tokens"] = 80
    span.attributes["gen_ai.usage.prompt_tokens"] = 30
    span.attributes["gen_ai.usage.completion_tokens"] = 50
    tracer.end_span(span)

    report = tracer.export_trace()
    # Sem a correção, o tracer somava 80 + 30 + 50 = 160
    assert report.total_tokens == 80, (
        f"Esperado 80 tokens pelo uso prioritário de `tokens`, obtido {report.total_tokens}"
    )


def test_agent_tracer_export_trace_prompt_and_completion_fallback() -> None:
    """
    Quando o span possui apenas `gen_ai.usage.prompt_tokens` e `completion_tokens`,
    deve somar ambos corretamente como fallback.
    """
    tracer = AgentTracer()
    span = tracer.start_span("agent.call")
    span.attributes["gen_ai.usage.prompt_tokens"] = 45
    span.attributes["gen_ai.usage.completion_tokens"] = 55
    tracer.end_span(span)

    report = tracer.export_trace()
    assert report.total_tokens == 100, (
        f"Esperado 100 tokens pela soma de prompt e completion, obtido {report.total_tokens}"
    )


def test_agent_tracer_export_trace_full_priority_chain() -> None:
    """
    Span contendo todos os 4 campos possíveis simultaneamente.
    Garante estrita precedência para `gen_ai.usage.total_tokens` sem acumular nenhum dos outros 3.
    """
    tracer = AgentTracer()
    span = tracer.start_span("agent.call.all_attrs")
    span.attributes["gen_ai.usage.total_tokens"] = 300
    span.attributes["tokens"] = 250
    span.attributes["gen_ai.usage.prompt_tokens"] = 100
    span.attributes["gen_ai.usage.completion_tokens"] = 150
    tracer.end_span(span)

    report = tracer.export_trace()
    # Sem precedência somaria 300 + 250 + 100 + 150 = 800!
    assert report.total_tokens == 300, (
        f"Esperado 300 tokens com precedência estrita, obtido {report.total_tokens}"
    )


def test_agent_tracer_token_aggregation_across_distinct_spans() -> None:
    """
    Múltiplos spans com diferentes formatos de contabilidade em um mesmo trace.
    Garante a soma agregada correta e precisa de todos os nós.
    """
    tracer = AgentTracer()

    # Span 1: total_tokens prioritário (120)
    s1 = tracer.start_span("span.1")
    s1.attributes["gen_ai.usage.total_tokens"] = 120
    s1.attributes["tokens"] = 90
    tracer.end_span(s1)

    # Span 2: tokens prioritário (60)
    s2 = tracer.start_span("span.2")
    s2.attributes["tokens"] = 60
    s2.attributes["gen_ai.usage.prompt_tokens"] = 20
    s2.attributes["gen_ai.usage.completion_tokens"] = 40
    tracer.end_span(s2)

    # Span 3: fallback prompt + completion (15 + 25 = 40)
    s3 = tracer.start_span("span.3")
    s3.attributes["gen_ai.usage.prompt_tokens"] = 15
    s3.attributes["gen_ai.usage.completion_tokens"] = 25
    tracer.end_span(s3)

    # Span 4: sem contagem de tokens (0)
    s4 = tracer.start_span("span.4")
    tracer.end_span(s4)

    report = tracer.export_trace()
    # 120 + 60 + 40 + 0 = 220
    assert report.total_tokens == 220, (
        f"Esperado total consolidado de 220 tokens, obtido {report.total_tokens}"
    )


# ============================================================================
# 4. Testes de Concorrência no SwarmCoordinator.run_fan_out
# ============================================================================


def test_swarm_coordinator_has_lock() -> None:
    """Verifica que o SwarmCoordinator inicializa uma trava para proteção de despacho."""
    coordinator = SwarmCoordinator()
    assert hasattr(coordinator, "_lock"), "SwarmCoordinator deve possuir atributo de trava `_lock`"


def test_swarm_coordinator_run_fan_out_concurrency_and_status() -> None:
    """
    Executa `run_fan_out` sob paralelismo real (8 tarefas, max_workers=4).
    Verifica que o status de todos os membros e a agregação dos resultados
    ocorrem de maneira thread-safe e determinística.
    """
    coordinator = SwarmCoordinator()

    subtasks = [
        {"role": "architect", "task": f"Validação estrutural da tarefa {i}"} for i in range(4)
    ] + [
        {"role": "code-reviewer", "task": f"Revisão de conformidade da tarefa {i}"}
        for i in range(4)
    ]

    report = coordinator.run_fan_out(
        goal="Execução Concorrente Thread-Safe de Engenharia",
        subtasks=subtasks,
        max_workers=4,
    )

    assert report.total_agents == 8
    assert report.successful_tasks == 8
    assert report.failed_tasks == 0
    assert "APPROVED" in report.aggregated_consensus
    assert len(report.results) == 8

    # Cada resultado deve ser válido e ter tempo medido
    for res in report.results:
        assert res.success is True
        assert res.execution_time_ms >= 0.0
        assert res.agent_id != ""
        assert res.role in ("architect", "code-reviewer")


def test_swarm_coordinator_concurrent_dispatch_task() -> None:
    """
    Múltiplas threads disparando `dispatch_task` simultaneamente.
    Verifica que as mutações no membro ocorrem sem erros de concorrência.
    """
    coordinator = SwarmCoordinator()
    members = coordinator.create_swarm(
        name="test-swarm",
        roles=["architect", "security-reviewer", "tdd-guide", "code-reviewer"],
    )

    def worker_dispatch(idx: int) -> Any:
        m = members[idx % len(members)]
        return coordinator.dispatch_task(m, f"Execução concorrente {idx}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(worker_dispatch, i) for i in range(16)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == 16
    for res in results:
        if res.role == "tdd-guide":
            assert res.success is False
            assert res.status == "SKIPPED"
        else:
            assert res.success is True
            assert res.status == "COMPLETED"
    for m in members:
        expected_status = "SKIPPED" if m.role == "tdd-guide" else "COMPLETED"
        assert m.status == expected_status
