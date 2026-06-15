#!/usr/bin/env python3
"""RBAC authorization differential test harness (Hypothesis).

WHY:   Authorization bugs hide in the cases nobody wrote an example for. A role-based
       access check that looks right on "admin can delete, viewer cannot" can silently
       grant a viewer *write* on a resource it may only *read* — the action half of the
       (resource, action) decision is dropped. Example-based tests pass; the privilege
       escalation ships. The verified way to catch this is the Cedar/Lean
       verification-guided-development pattern: keep a tiny, obviously-correct REFERENCE
       authorizer and assert the implementation agrees with it across *randomly
       generated* policies and requests (differential / model-based testing).

HOW:   ``reference_allow`` is the ground-truth model: allow iff some role the user holds
       grants exactly the requested (resource, action). Hypothesis generates random
       policies (role -> set of granted (resource, action)) and random (roles, resource,
       action) requests, and asserts the implementation under test matches the reference
       on every one. The ORACLE ``oracle_allow`` is an independent but correct
       implementation (no divergence). The BUGGY ``buggy_allow`` checks only that the
       *resource* is reachable and ignores the action — so it diverges (grants more than
       the reference), and Hypothesis shrinks to a minimal escalating request.

WHERE: lib/ — dependency-backed (hypothesis), fully in-process, deterministic. No
       services. Uses the ``hypothesis`` already in the ``lib`` extra.

Self-test:
  python harnesses/lib/rbac_authz_differential_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable, FrozenSet, Mapping, Tuple

from hypothesis import given, settings
from hypothesis import strategies as st

RESOURCES = ("doc", "billing", "config")
ACTIONS = ("read", "write", "delete")
ROLES = ("viewer", "editor", "admin")

Perm = Tuple[str, str]                       # (resource, action)
Policy = Mapping[str, FrozenSet[Perm]]       # role -> granted perms
Authorizer = Callable[[Policy, FrozenSet[str], str, str], bool]

# Symbols the vacuous-green meta-gate (Phase A) neuters to confirm this harness has teeth.
VACUITY_TARGETS = ["reference_allow"]


# --- REFERENCE: the ground-truth authorization model ----------------------------
def reference_allow(policy: Policy, user_roles: FrozenSet[str], resource: str, action: str) -> bool:
    """Allow iff some role the user holds grants exactly this (resource, action)."""
    return any((resource, action) in policy.get(role, frozenset()) for role in user_roles)


# --- ORACLE: an independent, correct implementation -----------------------------
def oracle_allow(policy: Policy, user_roles: FrozenSet[str], resource: str, action: str) -> bool:
    requested: Perm = (resource, action)
    for role in user_roles:
        for granted in policy.get(role, frozenset()):
            if granted == requested:
                return True
    return False


# --- BUGGY: ignores the action — resource access implies every action -----------
def buggy_allow(policy: Policy, user_roles: FrozenSet[str], resource: str, action: str) -> bool:
    for role in user_roles:
        if any(res == resource for (res, _act) in policy.get(role, frozenset())):
            return True  # BUG: never checks `action` — viewer's read becomes write/delete
    return False


_perm = st.tuples(st.sampled_from(RESOURCES), st.sampled_from(ACTIONS))
_policy = st.dictionaries(st.sampled_from(ROLES), st.frozensets(_perm, max_size=4), max_size=3)
_roles = st.frozensets(st.sampled_from(ROLES), max_size=3)
_request = st.tuples(st.sampled_from(RESOURCES), st.sampled_from(ACTIONS))


def divergence_from_reference(impl: Authorizer) -> tuple | None:
    """Run `impl` against the reference over random policies/requests. Return the first
    counterexample (policy, roles, request) where they disagree, or None if they agree."""
    found: dict[str, tuple] = {}

    @settings(max_examples=300)
    @given(_policy, _roles, _request)
    def check(policy: Policy, roles: FrozenSet[str], request: Perm) -> None:
        resource, action = request
        if impl(policy, roles, resource, action) != reference_allow(policy, roles, resource, action):
            found["case"] = (dict(policy), set(roles), request)
            raise AssertionError(found["case"])

    try:
        check()
    except AssertionError:
        return found.get("case")
    return None


def run_self_test() -> int:
    failures = 0
    oracle_div = divergence_from_reference(oracle_allow)
    if oracle_div is not None:
        failures += 1
        print(f"FAIL: oracle authorizer diverged from the reference at {oracle_div}", file=sys.stderr)
    buggy_div = divergence_from_reference(buggy_allow)
    if buggy_div is None:
        failures += 1
        print("FAIL: buggy authorizer matched the reference everywhere — vacuous green", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print(f"self-test: OK (oracle agrees with reference; buggy caught at -> {buggy_div})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RBAC authorization differential harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
