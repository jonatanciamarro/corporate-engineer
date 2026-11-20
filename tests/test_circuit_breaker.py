import time

import pytest

from corporate_engineer.mcp.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
)
from corporate_engineer.mcp.client import RemoteMCPSSEClient


def test_circuit_breaker_initial_state():
    cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1.0)
    assert cb.state == CircuitState.CLOSED
    assert cb.can_execute() is True
    assert cb.failure_count == 0


def test_circuit_breaker_transitions_to_open_on_failures():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.5)

    cb.record_failure()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 1

    cb.record_failure()
    assert cb.state == CircuitState.OPEN
    assert cb.can_execute() is False

    with pytest.raises(CircuitBreakerOpenError):
        cb.execute(lambda: "should not run")


def test_circuit_breaker_recovers_to_half_open_and_closed():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

    cb.record_failure()
    assert cb.state == CircuitState.OPEN

    # Wait for recovery timeout
    time.sleep(0.15)
    assert cb.can_execute() is True
    assert cb.state == CircuitState.HALF_OPEN

    # Successful call in half open closes the circuit
    cb.record_success()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0


def test_circuit_breaker_half_open_failure_reopens():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)
    cb.record_failure()
    assert cb.state == CircuitState.OPEN

    time.sleep(0.15)
    assert cb.can_execute() is True
    assert cb.state == CircuitState.HALF_OPEN

    cb.record_failure()
    assert cb.state == CircuitState.OPEN


def test_circuit_breaker_execute_wrapper():
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1.0)

    # Success call
    res = cb.execute(lambda x, y: x + y, 2, 3)
    assert res == 5
    assert cb.state == CircuitState.CLOSED

    # Failing call
    def faulty():
        raise ConnectionError("Timeout")

    with pytest.raises(ConnectionError):
        cb.execute(faulty)
    assert cb.failure_count == 1

    with pytest.raises(ConnectionError):
        cb.execute(faulty)
    assert cb.state == CircuitState.OPEN

    # Next execution blocked by circuit breaker
    with pytest.raises(CircuitBreakerOpenError):
        cb.execute(lambda: "blocked")


def test_circuit_breaker_reset():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10.0)
    cb.record_failure()
    assert cb.state == CircuitState.OPEN

    cb.reset()
    assert cb.state == CircuitState.CLOSED
    assert cb.failure_count == 0
    assert cb.can_execute() is True


def test_remote_mcp_client_with_circuit_breaker():
    cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1.0)
    client = RemoteMCPSSEClient(endpoint="http://invalid.mcp.host:9999", circuit_breaker=cb)

    # First call will fail due to connection error, tripping the circuit breaker
    res1 = client.call_tool("some_tool", {})
    assert res1.is_error is True
    assert cb.state == CircuitState.OPEN

    # Second call should immediately be rejected by circuit breaker without network call
    res2 = client.call_tool("some_tool", {})
    assert res2.is_error is True
    assert "Circuit breaker is OPEN" in res2.content
