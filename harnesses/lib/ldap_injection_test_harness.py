#!/usr/bin/env python3
"""LDAP filter-injection harness (ldap3): escape filter metacharacters in user input.

OWASP Top 10:2025 A05 Injection (LDAP injection, CWE-90).

WHY: Building an LDAP search filter by concatenating user input lets an attacker inject filter
metacharacters -- `*)(uid=*` turns `(uid=<input>)` into `(uid=*)(uid=*)`, matching every entry
and bypassing authentication. The input must be escaped with the LDAP filter escaping rules
(`* ( ) \\ NUL` -> `\\2a \\28 \\29 \\5c \\00`) before it goes in the filter.

HOW: `EscapedFilter` is the ORACLE -- it runs the value through `ldap3`'s
`escape_filter_chars` before building the filter, so the metacharacters are neutralized.
`RawFilter` is the planted defect -- raw concatenation. `filter_injectable` builds a filter
from `*)(uid=*` and reports whether the raw injection survived.

WHERE: lib/ -- dependency-backed (`ldap3` filter escaping), in-process, no directory server.

Self-test:
    python harnesses/lib/ldap_injection_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

from ldap3.utils.conv import escape_filter_chars

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["filter_injectable"]

DOSSIER = {
    "name": "ldap_injection",
    "path": "harnesses/lib/ldap_injection_test_harness.py",
    "flavor": "lib",
    "dependency": "ldap3",
    "standard": "OWASP Top 10:2025 A05 Injection - LDAP filter injection (CWE-90)",
    "failure_class": "Unescaped filter metacharacters (*)(uid=*) widen the LDAP search to all",
    "oracle": "EscapedFilter.build - escape_filter_chars before building the filter",
    "buggy": "RawFilter.build - raw concatenation into the filter",
    "planted_mutant": "username '*)(uid=*' turns (uid=x) into a match-all filter",
    "proof_file": "tests/lib/test_ldap_injection_proof.py",
    "vacuity_targets": ["filter_injectable"],
    "commands": ["python harnesses/lib/ldap_injection_test_harness.py --self-test"],
    "known_limits": "filter-value escaping; not DN escaping or search-scope review",
    "related": ["nosql_injection", "advanced_injection", "tool_arg_validation"],
}

_PAYLOAD = "*)(uid=*"


class EscapedFilter:
    """ORACLE: escape filter metacharacters before building the filter."""

    def build(self, username: str) -> str:
        return f"(uid={escape_filter_chars(username)})"


class RawFilter:
    """BUGGY: concatenate the raw user input into the filter."""

    def build(self, username: str) -> str:
        return f"(uid={username})"  # BUG: metacharacters ride along


def builds_lookup_filter(make_filter: Callable[[], object]) -> bool:
    return make_filter().build("alice") == "(uid=alice)"


def filter_injectable(make_filter: Callable[[], object]) -> bool:
    """True == the raw injection metacharacters survived into the filter (LDAP injection)."""
    return _PAYLOAD in make_filter().build(_PAYLOAD)


def run_self_test() -> int:
    failures = 0
    if not builds_lookup_filter(EscapedFilter):
        failures += 1
        print("FAIL: oracle built a wrong filter for a benign username", file=sys.stderr)
    if filter_injectable(EscapedFilter):
        failures += 1
        print("FAIL: oracle left filter metacharacters unescaped", file=sys.stderr)
    if not filter_injectable(RawFilter):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: raw filter LDAP injection was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (escaped filter neutralizes the metacharacters; raw filter injected)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LDAP filter-injection harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
