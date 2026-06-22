#!/usr/bin/env python3
"""API broken-function-level-authorization harness (Hypothesis).

OWASP API Security Top 10 2023 -- API5 Broken Function Level Authorization.

WHY: BFLA is the API failure where an authenticated-but-unprivileged user invokes a
function reserved for admins (delete a user, change a role) -- distinct from BOLA, which is
about another user's DATA. A test that checks "an admin can call the admin function" passes
whether or not non-admins are blocked; only checking that NO non-admin can reach an admin
function exposes the gap. Hypothesis sweeps role x function pairs and finds the escalation.

HOW: `FunctionAuthz` is the ORACLE -- admin-only functions require the admin role; user
functions are open to any authenticated user. `AuthOnlyAuthz` is the planted defect -- it
checks only that the caller is authenticated, not the function-level role. `find_function_escalation`
runs a Hypothesis property ("a non-admin can never invoke an admin function") and returns True
when falsified: the oracle holds, the auth-only policy is falsified.

WHERE: lib/ -- dependency-backed (`hypothesis`) but in-process, no service. Adds `hypothesis`
to the `lib` extra (already in the repo).

Self-test:
    python harnesses/lib/api_bfla_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys

from hypothesis import given, settings
from hypothesis import strategies as st

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["FunctionAuthz.can_invoke"]

DOSSIER = {
    "name": "api_bfla",
    "path": "harnesses/lib/api_bfla_test_harness.py",
    "flavor": "lib",
    "dependency": "hypothesis",
    "standard": "OWASP API Security Top 10 2023 - API5 Broken Function Level Authorization",
    "failure_class": (
        "A non-admin user invokes an admin-only function (function-level authz missing)"
    ),
    "oracle": "FunctionAuthz.can_invoke - admin functions require the admin role",
    "buggy": "AuthOnlyAuthz.can_invoke - any authenticated user may invoke any function",
    "planted_mutant": (
        "Hypothesis finds a non-admin invoking an admin function the auth-only policy allows"
    ),
    "proof_file": "tests/lib/test_api_bfla_proof.py",
    "vacuity_targets": ["FunctionAuthz.can_invoke"],
    "commands": ["python harnesses/lib/api_bfla_test_harness.py --self-test"],
    "known_limits": (
        "function-level role gating; object-level (BOLA) and property-level (API3) are separate"
    ),
    "related": ["agent_capability_allowlist (ASI03)", "api_object_property_authz (API3)"],
}

ADMIN_FUNCTIONS = {"delete_user", "change_role", "view_audit_log"}
USER_FUNCTIONS = {"get_profile", "update_profile"}
ALL_FUNCTIONS = sorted(ADMIN_FUNCTIONS | USER_FUNCTIONS)


class FunctionAuthz:
    """ORACLE: admin-only functions require the admin role."""

    def can_invoke(self, role: str, function: str) -> bool:
        if function in ADMIN_FUNCTIONS:
            return role == "admin"
        return function in USER_FUNCTIONS


class AuthOnlyAuthz:
    """BUGGY: any authenticated user may invoke any function."""

    def can_invoke(self, role: str, function: str) -> bool:
        return function in (ADMIN_FUNCTIONS | USER_FUNCTIONS)  # BUG: no function-level role check


def admin_can_invoke_admin(authz) -> bool:
    return authz.can_invoke("admin", "delete_user")


def find_function_escalation(authz) -> bool:
    """True == Hypothesis found a non-admin invoking an admin function (BFLA)."""
    @settings(max_examples=200)
    @given(function=st.sampled_from(ALL_FUNCTIONS))
    def prop(function: str) -> None:
        if function in ADMIN_FUNCTIONS:
            assert authz.can_invoke("user", function) is False

    try:
        prop()
    except AssertionError:
        return True
    return False


def run_self_test() -> int:
    failures = 0
    if not admin_can_invoke_admin(FunctionAuthz()):
        failures += 1
        print("FAIL: oracle denied an admin a legitimate admin function", file=sys.stderr)
    if find_function_escalation(FunctionAuthz()):
        failures += 1
        print("FAIL: oracle let a non-admin invoke an admin function", file=sys.stderr)
    if not find_function_escalation(AuthOnlyAuthz()):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: auth-only BFLA escalation was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print(
        "self-test: OK (function-level authz blocks escalation; auth-only policy caught by "
        "Hypothesis)"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="API broken-function-level-authorization harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
