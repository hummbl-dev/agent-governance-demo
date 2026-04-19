# Agent Governance

[![CI](https://github.com/hummbl-dev/agent-governance-demo/actions/workflows/ci.yml/badge.svg)](https://github.com/hummbl-dev/agent-governance-demo/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)]()
[![Tests](https://img.shields.io/badge/tests-58%20passing-brightgreen)]()
[![Dependencies](https://img.shields.io/badge/dependencies-0-brightgreen)]()
[![License](https://img.shields.io/badge/license-Apache%202.0-blue)](LICENSE)

Runtime safety primitives for AI agent systems. Zero third-party dependencies.

```bash
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

## OWASP Coverage

These five primitives address 7 of 10 risks in the [OWASP Top 10 for Agentic Applications](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/):

| OWASP Risk | Primitive | How |
|------------|-----------|-----|
| **ASI01** Agent Goal Hijack | [kill_switch.py](src/agent_governance/kill_switch.py) | 4-mode graduated shutdown stops hijacked agents mid-execution |
| **ASI03** Identity & Privilege Abuse | [delegation_token.py](src/agent_governance/delegation_token.py) | HMAC-signed scoped tokens with chain-depth limits (max 3 hops) |
| **ASI04** Supply Chain | Zero dependencies | Stdlib-only. No transitive dependency tree to compromise |
| **ASI06** Memory & Context Poisoning | [governance_bus.py](src/agent_governance/governance_bus.py) | Append-only JSONL with SHA256 content hashing; tamper-evident |
| **ASI07** Insecure Inter-Agent Comms | [delegation_token.py](src/agent_governance/delegation_token.py) | Chain depth enforcement prevents privilege escalation across agents |
| **ASI08** Cascading Failures | [circuit_breaker.py](src/agent_governance/circuit_breaker.py) | CLOSED/HALF_OPEN/OPEN FSM isolates failing components |
| **ASI10** Rogue Agents | [agent_runner.py](src/agent_governance/agent_runner.py) | Token verification before every execution; audit trail on every action |

**Need 10/10?** The production library [`hummbl-governance`](https://github.com/hummbl-dev/hummbl-governance) covers all 10 risks with 20 primitives, 583 tests, and the same zero-dependency guarantee. See the [full OWASP mapping](https://hummbl.io/owasp.html).

## Test Suite

```
$ python -m pytest -v

tests/test_kill_switch.py       15 tests
tests/test_circuit_breaker.py   14 tests
tests/test_delegation_token.py  11 tests
tests/test_governance_bus.py     8 tests
tests/test_integration.py       10 tests
                                --------
                                58 tests, 0 dependencies
```

The integration test tells a complete story: agent starts, executes tasks successfully, encounters failures, circuit breaker trips, kill switch engages, governance bus records every event.

## Background

Built by [Reuben Bowlby](https://github.com/rpbowlby) as part of [HUMMBL](https://hummbl.io)'s AI governance platform. The production version ([`pip install hummbl-governance`](https://pypi.org/project/hummbl-governance/)) has 583 tests across 20 modules. This repo is a clean-room demonstration of the core patterns.

For the formal governance primitive underlying these mitigations, see [The Governance Tuple](https://doi.org/10.5281/zenodo.19646940) (Bowlby, 2026).

## License

Apache 2.0 — see [LICENSE](LICENSE).
