"""Agent execution harness wiring all governance primitives together."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from agent_governance.kill_switch import KillSwitch
from agent_governance.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError
from agent_governance.delegation_token import DelegationToken, TokenAuthority
from agent_governance.governance_bus import GovernanceBus


@dataclass
class TaskResult:
    success: bool
    output: Any
    error: Optional[str] = None


class AgentRunner:
    def __init__(
        self,
        agent_id: str,
        kill_switch: KillSwitch,
        circuit_breaker: CircuitBreaker,
        token_authority: TokenAuthority,
        bus: GovernanceBus,
    ):
        self.agent_id = agent_id
        self.ks = kill_switch
        self.cb = circuit_breaker
        self.ta = token_authority
        self.bus = bus

    def execute(
        self,
        task: Callable[..., Any],
        operation: str,
        resource: str,
        token: DelegationToken,
        critical: bool = False,
    ) -> TaskResult:
        if self.ks.is_halted(critical=critical):
            self.bus.post(self.agent_id, "BLOCKED", f"Kill switch {self.ks.mode.name}: {operation}")
            return TaskResult(success=False, output=None, error=f"Kill switch: {self.ks.mode.name}")

        if not self.ta.verify(token):
            self.bus.post(self.agent_id, "DENIED", f"Invalid token for {operation} on {resource}")
            return TaskResult(success=False, output=None, error="Token verification failed")

        if not token.permits(operation, resource):
            self.bus.post(self.agent_id, "DENIED", f"Token does not permit {operation} on {resource}")
            return TaskResult(success=False, output=None, error=f"Not permitted: {operation} on {resource}")

        self.bus.post(self.agent_id, "START", f"{operation} on {resource}")

        try:
            result = self.cb.call(task)
            self.bus.post(self.agent_id, "COMPLETE", f"{operation} on {resource}")
            return TaskResult(success=True, output=result)
        except CircuitBreakerOpenError as e:
            self.bus.post(self.agent_id, "CIRCUIT_OPEN", str(e))
            return TaskResult(success=False, output=None, error=str(e))
        except Exception as e:
            self.bus.post(self.agent_id, "ERROR", f"{operation} failed: {e}")
            return TaskResult(success=False, output=None, error=str(e))
