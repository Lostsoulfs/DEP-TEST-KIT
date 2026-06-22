#!/usr/bin/env python3
"""Fail-closed authorization harness (requests): deny-by-default when the policy backend errors.

OWASP Top 10:2025 A10 Mishandling of Exceptional Conditions (new in 2025). The canonical
example the category cites: "authorization checks that default to permit when the policy
engine throws an exception" -- CWE-636 Not Failing Securely ('Failing Open').

WHY: An authorization point that calls a remote policy service must decide what to do when
that call raises (timeout, 5xx, network error). Failing OPEN -- treating the error as "allow"
-- silently disables access control under exactly the conditions an attacker can induce. The
happy path passes tests; the exceptional path is where the breach lives.

HOW: `FailClosedAuthz` is the ORACLE -- on any `requests` exception it returns False (deny).
`FailOpenAuthz` is the planted defect -- on the same exception it returns True. The policy
client is injected: `_HealthyClient` returns a decision, `_ErroringClient` raises a `requests`
`Timeout`. `fails_open_on_error` drives the erroring client and reports whether access was
granted.

WHERE: lib/ -- dependency-backed (`requests.exceptions`; the decision hinges on catching the
real exception type) and fully in-process via an injected client, so no network is used.

Self-test:
    python harnesses/lib/failopen_authz_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

from requests.exceptions import RequestException, Timeout

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["fails_open_on_error"]

DOSSIER = {
    "name": "failopen_authz",
    "path": "harnesses/lib/failopen_authz_test_harness.py",
    "flavor": "lib",
    "dependency": "requests",
    "standard": (
        "OWASP Top 10:2025 A10 Mishandling of Exceptional Conditions - fail open (CWE-636)"
    ),
    "failure_class": "Authorization defaults to ALLOW when the policy backend errors (fail open)",
    "oracle": "FailClosedAuthz.allow - deny-by-default when the policy call raises",
    "buggy": "FailOpenAuthz.allow - return True when the policy call raises",
    "planted_mutant": "the policy client times out; the decision returns allow",
    "proof_file": "tests/lib/test_failopen_authz_proof.py",
    "vacuity_targets": ["fails_open_on_error"],
    "commands": ["python harnesses/lib/failopen_authz_test_harness.py --self-test"],
    "known_limits": "models fail-open on transport error; not full policy-engine semantics",
    "related": [
        "retry_resilience (A10 retries)",
        "agent_circuit_breaker (ASI08)",
        "ssrf_url_guard",
    ],
}


class _Resp:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def json(self) -> dict:
        return self._payload


class _HealthyClient:
    """Policy backend that returns a decision."""

    def __init__(self, allow: bool) -> None:
        self._allow = allow

    def get(self, url: str, **kwargs) -> _Resp:
        return _Resp({"allow": self._allow})


class _ErroringClient:
    """Policy backend that is down."""

    def get(self, url: str, **kwargs) -> _Resp:
        raise Timeout("policy backend timed out")


class FailClosedAuthz:
    """ORACLE: deny-by-default when the policy call raises."""

    def __init__(self, client) -> None:
        self._client = client

    def allow(self, user: str, action: str) -> bool:
        try:
            resp = self._client.get(f"https://policy.internal/decide?u={user}&a={action}")
        except RequestException:
            return False  # fail closed
        return bool(resp.json().get("allow", False))


class FailOpenAuthz:
    """BUGGY: grant access when the policy call raises."""

    def __init__(self, client) -> None:
        self._client = client

    def allow(self, user: str, action: str) -> bool:
        try:
            resp = self._client.get(f"https://policy.internal/decide?u={user}&a={action}")
        except RequestException:
            return True  # BUG: fail open
        return bool(resp.json().get("allow", False))


def allows_when_permitted(make_authz: Callable[..., object]) -> bool:
    """True == a healthy backend's allow=True decision is honored (no false positive)."""
    return make_authz(_HealthyClient(allow=True)).allow("alice", "read")


def fails_open_on_error(make_authz: Callable[..., object]) -> bool:
    """True == access is granted despite the policy backend being down (the bug)."""
    return make_authz(_ErroringClient()).allow("mallory", "delete_all")


def run_self_test() -> int:
    failures = 0
    if not allows_when_permitted(FailClosedAuthz):
        failures += 1
        print("FAIL: oracle denied an explicitly permitted request", file=sys.stderr)
    if fails_open_on_error(FailClosedAuthz):
        failures += 1
        print("FAIL: oracle failed open on a backend error", file=sys.stderr)
    if not fails_open_on_error(FailOpenAuthz):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: fail-open authz was NOT caught granting on error", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (fail-closed denies on backend error; fail-open grants -- caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail-closed authorization harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
