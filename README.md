# Agent Governance

Runtime safety primitives for AI agent systems. Zero third-party dependencies.

```
pip install -e ".[test]"
python -m pytest -v
```

## What This Demonstrates

Five production-grade governance primitives for AI agent systems, extracted from a platform coordinating 12 concurrent AI agents across 3 model families. All stdlib-only. Zero third-party runtime dependencies.

```
                    +------------------+
                    |   Agent Runner   |  Orchestrates execution
                    +--------+---------+
                             |
              +--------------+--------------+
              |              |              |
    +---------v--+   +-------v------+  +----v-----------+
    | Delegation |   |   Circuit    |  |  Kill Switch   |
    |   Tokens   |   |   Breaker    |  |  (4 modes)     |
    | HMAC-SHA256|   | C/HO/O FSM  |  | HMAC-signed    |
    +------------+   +--------------+  +----------------+
              |              |              |
              +--------------+--------------+
                             |
                    +--------v---------+
                    | Governance Bus   |  Append-only JSONL
                    | (audit trail)    |  Thread-safe writes
                    +------------------+
```

## Modules

| Module | What It Does | Lines |
|--------|-------------|-------|
| `kill_switch.py` | Four-mode graduated shutdown (DISENGAGED / HALT_NONCRITICAL / HALT_ALL / EMERGENCY) with HMAC-signed persistent state and a `@kill_switch_gate` decorator | ~90 |
| `circuit_breaker.py` | CLOSED / HALF_OPEN / OPEN state machine wrapping callable targets with configurable failure thresholds and recovery probes | ~75 |
| `delegation_token.py` | HMAC-SHA256 signed capability tokens binding issuer, operations, resources, expiry. Chain depth enforcement (max 3 hops) | ~90 |
| `governance_bus.py` | Append-only JSONL audit log with SHA256 content hashing, thread-safe writes, and query by agent/type/time | ~80 |
| `agent_runner.py` | Execution harness wiring all four primitives into a single `execute()` call with full audit trail | ~60 |

## Why This Matters

These primitives address 7 of 10 risks in the [OWASP Top 10 for Agentic Applications](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/):

| OWASP Risk | Primitive |
|------------|-----------|
| ASI01: Agent Goal Hijack | Kill switch (graduated shutdown) |
| ASI03: Identity & Privilege Abuse | Delegation tokens (HMAC-signed, scoped) |
| ASI04: Supply Chain Vulnerabilities | Zero dependencies (stdlib only) |
| ASI06: Memory & Context Poisoning | Governance bus (append-only, content-hashed) |
| ASI07: Insecure Inter-Agent Communication | Delegation tokens (chain depth enforcement) |
| ASI08: Cascading Failures | Circuit breaker (isolates failing adapters) |
| ASI10: Rogue Agents | Agent runner (token verification before execution) |

## Test Suite

```
$ python -m pytest -v

tests/test_kill_switch.py       15 tests
tests/test_circuit_breaker.py   14 tests
tests/test_delegation_token.py  15 tests
tests/test_governance_bus.py    10 tests
tests/test_integration.py       10 tests
                                --------
                                64 tests, 0 dependencies
```

The integration test tells a complete story: agent starts, executes tasks successfully, encounters failures, circuit breaker trips, kill switch engages, governance bus records every event.

## Background

Built by [Reuben Bowlby](https://github.com/rpbowlby) as part of [HUMMBL](https://hummbl.io)'s AI governance platform. The production version (`pip install hummbl-governance`) has 476 tests across 20 modules. This repo is a clean-room demonstration of the core patterns.

## License

Apache-2.0
