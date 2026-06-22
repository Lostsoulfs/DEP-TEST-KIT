#!/usr/bin/env python3
"""Agent cascading-failure isolation harness (pybreaker).

OWASP Top 10 for Agentic Applications 2026 -- ASI08 Cascading Failures.

WHY: In a high-fan-out agent system, one failing dependency can be hammered by every task
in the pipeline, turning a single fault into a system-wide cascade (a retry storm). A test
where the dependency is healthy passes whether or not the orchestrator isolates failures;
the cascade only shows when the dependency is DOWN and the orchestrator keeps calling it.
The 2026 mitigation is a circuit breaker (and fan-out caps): after N failures the breaker
opens and stops calling the dead dependency.

HOW: `IsolatedOrchestrator` is the ORACLE -- it wraps the dependency in a `pybreaker`
circuit breaker, so after `fail_max` failures the breaker opens and further calls short-circuit
WITHOUT hitting the dependency. `NoBreakerOrchestrator` is the planted defect -- every task
calls the dead dependency. `cascades_on_failure` fans out 100 tasks against a down dependency
and counts how many actually reached it: the oracle bounds it (breaker open), the no-breaker
orchestrator lets all 100 through.

WHERE: ai/ -- in-process, deterministic. Adds `pybreaker` to the `ai` extra.

Self-test:
    python harnesses/ai/agent_circuit_breaker_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

import pybreaker

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["cascades_on_failure"]

DOSSIER = {
    "name": "agent_circuit_breaker",
    "path": "harnesses/ai/agent_circuit_breaker_test_harness.py",
    "flavor": "ai",
    "dependency": "pybreaker",
    "standard": "OWASP Top 10 for Agentic Applications 2026 - ASI08 Cascading Failures",
    "failure_class": (
        "One failing dependency hammered by high fan-out -> system-wide cascade / retry storm"
    ),
    "oracle": (
        "IsolatedOrchestrator.fan_out - circuit breaker opens after fail_max, short-circuits "
        "further calls"
    ),
    "buggy": "NoBreakerOrchestrator.fan_out - every task calls the dead dependency",
    "planted_mutant": (
        "fan out 100 tasks at a down dependency; no-breaker orchestrator makes all 100 calls"
    ),
    "proof_file": "tests/ai/test_agent_circuit_breaker_proof.py",
    "vacuity_targets": ["cascades_on_failure"],
    "commands": ["python harnesses/ai/agent_circuit_breaker_test_harness.py --self-test"],
    "known_limits": (
        "models the breaker; real isolation also needs fan-out caps + per-tenant bulkheads"
    ),
    "related": ["retry_resilience", "rate_limit"],
}

FAN_OUT = 100
CASCADE_THRESHOLD = 10  # calls to a known-dead dependency above this == no isolation


class IsolatedOrchestrator:
    """ORACLE: a circuit breaker stops calling a failing dependency."""

    def __init__(self, fail_max: int = 3) -> None:
        self.breaker = pybreaker.CircuitBreaker(fail_max=fail_max)
        self.calls = 0

    def _dependency(self) -> None:
        self.calls += 1
        raise RuntimeError("dependency down")

    def fan_out(self, n: int) -> int:
        for _ in range(n):
            try:
                self.breaker.call(self._dependency)
            except Exception:
                pass
        return self.calls


class NoBreakerOrchestrator:
    """BUGGY: no circuit breaker -- every task hits the dead dependency."""

    def __init__(self, fail_max: int = 3) -> None:
        self.calls = 0

    def _dependency(self) -> None:
        self.calls += 1
        raise RuntimeError("dependency down")

    def fan_out(self, n: int) -> int:
        for _ in range(n):
            try:
                self._dependency()
            except Exception:
                pass
        return self.calls


def cascades_on_failure(make_orchestrator: Callable[[], object]) -> bool:
    """True == the dead dependency was called more than the cascade threshold (no isolation)."""
    return make_orchestrator().fan_out(FAN_OUT) > CASCADE_THRESHOLD


def run_self_test() -> int:
    failures = 0
    if cascades_on_failure(IsolatedOrchestrator):
        failures += 1
        print("FAIL: oracle cascaded despite the circuit breaker", file=sys.stderr)
    if not cascades_on_failure(NoBreakerOrchestrator):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: no-breaker orchestrator cascade was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (breaker bounds calls to a dead dependency; no-breaker cascade caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Agent cascading-failure isolation harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
