"""Tests for the circuit breaker state machine."""

import time
import pytest
from agent_governance.circuit_breaker import (
    CircuitBreaker, CircuitBreakerState, CircuitBreakerOpenError,
)


class TestClosedState:
    def test_starts_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitBreakerState.CLOSED

    def test_successful_call(self):
        cb = CircuitBreaker()
        result = cb.call(lambda: 42)
        assert result == 42
        assert cb.state == CircuitBreakerState.CLOSED

    def test_single_failure_stays_closed(self):
        cb = CircuitBreaker(failure_threshold=3)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 1

    def test_success_resets_failure_count(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        cb.call(lambda: "ok")
        assert cb.failure_count == 0


class TestOpenState:
    def test_opens_at_threshold(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            with pytest.raises(ValueError):
                cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert cb.state == CircuitBreakerState.OPEN

    def test_open_rejects_calls(self):
        cb = CircuitBreaker(failure_threshold=1)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        with pytest.raises(CircuitBreakerOpenError):
            cb.call(lambda: "should not run")

    def test_open_error_message(self):
        cb = CircuitBreaker(failure_threshold=1)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        with pytest.raises(CircuitBreakerOpenError, match="OPEN"):
            cb.call(lambda: "nope")


class TestHalfOpenState:
    def test_transitions_to_half_open(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert cb.state == CircuitBreakerState.OPEN
        time.sleep(0.02)
        assert cb.state == CircuitBreakerState.HALF_OPEN

    def test_half_open_success_closes(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        time.sleep(0.02)
        cb.call(lambda: "recovered")
        assert cb.state == CircuitBreakerState.CLOSED

    def test_half_open_failure_reopens(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        time.sleep(0.02)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("still broken")))
        assert cb.state == CircuitBreakerState.OPEN

    def test_half_open_limits_probes(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=0.01, half_open_max_calls=1)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        time.sleep(0.02)
        cb.call(lambda: "probe 1")
        assert cb.state == CircuitBreakerState.CLOSED


class TestReset:
    def test_reset_to_closed(self):
        cb = CircuitBreaker(failure_threshold=1)
        with pytest.raises(ValueError):
            cb.call(lambda: (_ for _ in ()).throw(ValueError("fail")))
        assert cb.state == CircuitBreakerState.OPEN
        cb.reset()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.failure_count == 0
