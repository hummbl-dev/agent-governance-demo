"""Circuit breaker (CLOSED/HALF_OPEN/OPEN) for wrapping external calls."""

from __future__ import annotations

import enum
import time
from dataclasses import dataclass, field
from typing import Any, Callable


class CircuitBreakerState(enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerOpenError(Exception):
    pass


@dataclass
class CircuitBreaker:
    failure_threshold: int = 3
    recovery_timeout: float = 30.0
    half_open_max_calls: int = 1

    _state: CircuitBreakerState = field(default=CircuitBreakerState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)
    _half_open_calls: int = field(default=0, init=False)
    _success_count: int = field(default=0, init=False)

    @property
    def state(self) -> CircuitBreakerState:
        if self._state == CircuitBreakerState.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitBreakerState.HALF_OPEN
                self._half_open_calls = 0
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    def call(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        state = self.state
        if state == CircuitBreakerState.OPEN:
            raise CircuitBreakerOpenError(
                f"Circuit breaker OPEN — {self._failure_count} failures, "
                f"recovery in {self.recovery_timeout - (time.time() - self._last_failure_time):.0f}s"
            )
        if state == CircuitBreakerState.HALF_OPEN:
            if self._half_open_calls >= self.half_open_max_calls:
                raise CircuitBreakerOpenError("Circuit breaker HALF_OPEN — probe limit reached")
            self._half_open_calls += 1
        try:
            result = fn(*args, **kwargs)
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise

    def _on_success(self) -> None:
        if self._state == CircuitBreakerState.HALF_OPEN:
            self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count += 1

    def _on_failure(self) -> None:
        self._failure_count += 1
        self._last_failure_time = time.time()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitBreakerState.OPEN

    def reset(self) -> None:
        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._half_open_calls = 0
