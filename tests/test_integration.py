"""Integration test: agent runs task through full governance stack."""

import pytest
from agent_governance import (
    KillSwitch, KillSwitchMode,
    CircuitBreaker,
    TokenAuthority,
    GovernanceBus,
    AgentRunner,
)


@pytest.fixture
def governance_stack():
    ks = KillSwitch()
    cb = CircuitBreaker(failure_threshold=2)
    ta = TokenAuthority(secret="integration-test")
    bus = GovernanceBus()
    runner = AgentRunner("test-agent", ks, cb, ta, bus)
    token = ta.issue("admin", "test-agent", {"read", "write"}, {"repo", "bus"})
    return runner, ks, cb, ta, bus, token


class TestHappyPath:
    def test_agent_executes_task(self, governance_stack):
        runner, ks, cb, ta, bus, token = governance_stack
        result = runner.execute(lambda: "done", "read", "repo", token)
        assert result.success
        assert result.output == "done"
        assert bus.count == 2  # START + COMPLETE

    def test_bus_records_lifecycle(self, governance_stack):
        runner, ks, cb, ta, bus, token = governance_stack
        runner.execute(lambda: "done", "write", "repo", token)
        entries = bus.query(agent="test-agent")
        assert entries[0].event_type == "START"
        assert entries[1].event_type == "COMPLETE"


class TestKillSwitchIntegration:
    def test_kill_switch_blocks_execution(self, governance_stack):
        runner, ks, cb, ta, bus, token = governance_stack
        ks.engage(KillSwitchMode.HALT_ALL, "incident", "operator")
        result = runner.execute(lambda: "should not run", "read", "repo", token)
        assert not result.success
        assert "Kill switch" in result.error
        blocked = bus.query(event_type="BLOCKED")
        assert len(blocked) == 1

    def test_emergency_blocks_critical(self, governance_stack):
        runner, ks, cb, ta, bus, token = governance_stack
        ks.engage(KillSwitchMode.EMERGENCY, "meltdown", "operator")
        result = runner.execute(lambda: "nope", "read", "repo", token, critical=True)
        assert not result.success


class TestTokenIntegration:
    def test_invalid_token_denied(self, governance_stack):
        runner, ks, cb, ta, bus, token = governance_stack
        bad_ta = TokenAuthority(secret="wrong-secret")
        bad_token = bad_ta.issue("hacker", "test-agent", {"read"}, {"repo"})
        result = runner.execute(lambda: "nope", "read", "repo", bad_token)
        assert not result.success
        assert "Token verification failed" in result.error
        denied = bus.query(event_type="DENIED")
        assert len(denied) == 1

    def test_unpermitted_operation_denied(self, governance_stack):
        runner, ks, cb, ta, bus, token = governance_stack
        result = runner.execute(lambda: "nope", "delete", "repo", token)
        assert not result.success
        assert "Not permitted" in result.error


class TestCircuitBreakerIntegration:
    def test_circuit_opens_after_failures(self, governance_stack):
        runner, ks, cb, ta, bus, token = governance_stack

        def failing_task():
            raise ConnectionError("service down")

        for _ in range(2):
            result = runner.execute(failing_task, "read", "repo", token)
            assert not result.success

        result = runner.execute(lambda: "after break", "read", "repo", token)
        assert not result.success
        assert "OPEN" in result.error
        circuit_entries = bus.query(event_type="CIRCUIT_OPEN")
        assert len(circuit_entries) == 1


class TestFullScenario:
    def test_agent_lifecycle(self, governance_stack):
        """Full story: agent works, fails, circuit opens, kill switch engages."""
        runner, ks, cb, ta, bus, token = governance_stack

        r1 = runner.execute(lambda: "task 1", "read", "repo", token)
        assert r1.success

        r2 = runner.execute(lambda: "task 2", "write", "repo", token)
        assert r2.success

        def flaky():
            raise TimeoutError("upstream timeout")

        r3 = runner.execute(flaky, "read", "repo", token)
        assert not r3.success
        r4 = runner.execute(flaky, "read", "repo", token)
        assert not r4.success

        r5 = runner.execute(lambda: "should fail", "read", "repo", token)
        assert not r5.success
        assert "OPEN" in r5.error

        ks.engage(KillSwitchMode.EMERGENCY, "too many failures", "operator")
        r6 = runner.execute(lambda: "blocked", "read", "repo", token, critical=True)
        assert not r6.success
        assert "Kill switch" in r6.error

        assert bus.count >= 8
