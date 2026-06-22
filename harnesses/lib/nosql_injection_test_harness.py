#!/usr/bin/env python3
"""NoSQL operator-injection harness (jsonschema): query inputs must be scalars, not operators.

OWASP Top 10:2025 A05 Injection (NoSQL operator injection, CWE-943).

WHY: A Mongo-style lookup that drops a user-supplied value straight into the query filter lets
an attacker pass an operator object like `{"$ne": null}` for the username -- which matches ANY
document and bypasses authentication. The fix is to validate that query inputs are scalars
(strings/numbers), rejecting operator objects, before they reach the filter.

HOW: `ScalarValidatedQuery` is the ORACLE -- it validates the input against a `{"type":
"string"}` schema, so an operator dict is rejected before it can reach the filter.
`RawQuery` is the planted defect -- it drops the input straight in. `operator_injection`
submits `{"$ne": None}` and reports whether an operator object reached the query filter.

WHERE: lib/ -- dependency-backed (`jsonschema`), in-process, no database.

Self-test:
    python harnesses/lib/nosql_injection_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

from jsonschema import validate

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["operator_injection"]

DOSSIER = {
    "name": "nosql_injection",
    "path": "harnesses/lib/nosql_injection_test_harness.py",
    "flavor": "lib",
    "dependency": "jsonschema",
    "standard": "OWASP Top 10:2025 A05 Injection - NoSQL operator injection (CWE-943)",
    "failure_class": "An operator object ({\"$ne\": null}) reaches the query filter (auth bypass)",
    "oracle": "ScalarValidatedQuery.build - validate the input is a scalar string first",
    "buggy": "RawQuery.build - drop the user input straight into the filter",
    "planted_mutant": "submit {\"$ne\": None} as the username; it matches any document",
    "proof_file": "tests/lib/test_nosql_injection_proof.py",
    "vacuity_targets": ["operator_injection"],
    "commands": ["python harnesses/lib/nosql_injection_test_harness.py --self-test"],
    "known_limits": "scalar-input validation; not full query-shape or aggregation-pipeline review",
    "related": ["tool_arg_validation", "structured_output_contract", "advanced_injection"],
}

_SCALAR = {"type": "string"}


class ScalarValidatedQuery:
    """ORACLE: validate the input is a scalar string before building the filter."""

    def build(self, username) -> dict:
        validate(username, _SCALAR)  # raises if username is an operator object
        return {"username": username}


class RawQuery:
    """BUGGY: drop the user input straight into the filter."""

    def build(self, username) -> dict:
        return {"username": username}  # BUG: an operator dict rides straight in


def builds_scalar_query(make_query: Callable[[], object]) -> bool:
    return make_query().build("alice") == {"username": "alice"}


def operator_injection(make_query: Callable[[], object]) -> bool:
    """True == an operator object reached the query filter (NoSQL injection)."""
    try:
        result = make_query().build({"$ne": None})
    except Exception:
        return False  # rejected by validation
    return isinstance(result.get("username"), dict)


def run_self_test() -> int:
    failures = 0
    if not builds_scalar_query(ScalarValidatedQuery):
        failures += 1
        print("FAIL: oracle rejected a legitimate scalar query", file=sys.stderr)
    if operator_injection(ScalarValidatedQuery):
        failures += 1
        print("FAIL: oracle let an operator object into the filter", file=sys.stderr)
    if not operator_injection(RawQuery):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: raw query operator injection was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (scalar validation rejects the operator object; raw query injected)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="NoSQL operator-injection harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
