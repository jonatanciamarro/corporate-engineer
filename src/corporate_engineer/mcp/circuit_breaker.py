"""
Circuit Breaker Pattern implementation for MCP Client and Network Adapters.
Manages failure states (CLOSED, OPEN, HALF_OPEN) and handles automatic reconnection / backoff.
"""

import time
from collections.abc import Callable
from enum import Enum
from typing import Any, TypeVar

T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenError(RuntimeError):
    """Raised when an operation is attempted while the circuit breaker is in OPEN state."""


class CircuitBreaker:
    """
    Standard state machine for the Circuit Breaker pattern.
    - CLOSED: Normal operation. Errors increment failure_count.
    - OPEN: Calls immediately rejected. After recovery_timeout, transitions to HALF_OPEN.
    - HALF_OPEN: Trial period. Success closes circuit; failure re-opens it.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        half_open_success_threshold: int = 1,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_success_threshold = half_open_success_threshold

        self._state: CircuitState = CircuitState.CLOSED
        self._failure_count: int = 0
        self._success_count: int = 0
        self._last_state_change: float = time.time()
        self._last_failure_time: float | None = None

    @property
    def state(self) -> CircuitState:
        if self._state == CircuitState.OPEN:
            elapsed = time.time() - self._last_state_change
            if elapsed >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._last_state_change = time.time()
                self._success_count = 0
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def can_execute(self) -> bool:
        """Check if execution is currently permitted by circuit state."""
        current = self.state
        return current in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    def record_success(self) -> None:
        """Record successful execution."""
        current = self.state
        if current == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.half_open_success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
                self._last_state_change = time.time()
        elif current == CircuitState.CLOSED:
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record failure during execution."""
        current = self.state
        self._last_failure_time = time.time()

        if current == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            self._last_state_change = time.time()
            self._failure_count = self.failure_threshold
        elif current == CircuitState.CLOSED:
            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                self._last_state_change = time.time()

    def execute(self, fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Wrap and execute a callable through circuit breaker protections."""
        if not self.can_execute():
            raise CircuitBreakerOpenError(
                f"Circuit breaker is OPEN: operation blocked until recovery timeout "
                f"({self.recovery_timeout:.1f}s)."
            )

        try:
            result = fn(*args, **kwargs)
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            raise

    def reset(self) -> None:
        """Reset circuit breaker to initial closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_state_change = time.time()
        self._last_failure_time = None
