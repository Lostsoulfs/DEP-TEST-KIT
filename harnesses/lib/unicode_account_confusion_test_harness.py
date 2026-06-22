#!/usr/bin/env python3
"""Unicode account-confusion harness (idna): canonicalize identifiers before uniqueness.

OWASP Top 10:2025 A07 Identification and Authentication Failures (CWE-1007 homograph).

WHY: A registry that compares usernames/emails byte-for-byte lets an attacker register a
Unicode look-alike of an existing account (fullwidth/compatibility characters, mixed scripts),
then impersonate or hijack flows keyed on the "same" name. Identifiers must be canonicalized
(NFKC + casefold for the local part, IDNA/UTS-46 for the domain) before the uniqueness check.

HOW: `CanonicalizingRegistry` is the ORACLE -- it NFKC-normalizes + casefolds the local part
and idna-encodes the domain, so a look-alike collides with the existing account.
`RawRegistry` is the planted defect -- it compares raw strings. `confusable_impersonation`
registers `admin@app.example`, then a fullwidth look-alike, and reports whether it was accepted
as a distinct account.

WHERE: lib/ -- dependency-backed (`idna` UTS-46 domain canonicalization) + stdlib unicodedata.

Self-test:
    python harnesses/lib/unicode_account_confusion_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
import unicodedata
from typing import Callable

import idna

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["confusable_impersonation"]

DOSSIER = {
    "name": "unicode_account_confusion",
    "path": "harnesses/lib/unicode_account_confusion_test_harness.py",
    "flavor": "lib",
    "dependency": "idna",
    "standard": "OWASP Top 10:2025 A07 Authentication Failures - homograph (CWE-1007)",
    "failure_class": "A Unicode look-alike of an existing account registers as a distinct user",
    "oracle": "CanonicalizingRegistry - NFKC+casefold local, IDNA domain, then uniqueness",
    "buggy": "RawRegistry - compare raw identifier strings",
    "planted_mutant": "register a fullwidth look-alike of admin@app.example as 'distinct'",
    "proof_file": "tests/lib/test_unicode_account_confusion_proof.py",
    "vacuity_targets": ["confusable_impersonation"],
    "commands": ["python harnesses/lib/unicode_account_confusion_test_harness.py --self-test"],
    "known_limits": "NFKC + IDNA folding; not a full cross-script confusable-skeleton table",
    "related": ["secret_scanning", "jwt_audience_binding"],
}


def _canon(email: str) -> str:
    local, _, domain = email.partition("@")
    local = unicodedata.normalize("NFKC", local).casefold()
    try:
        domain = idna.encode(domain, uts46=True).decode("ascii")
    except idna.IDNAError:
        domain = domain.lower()
    return f"{local}@{domain}"


class CanonicalizingRegistry:
    """ORACLE: canonicalize (NFKC + IDNA) before the uniqueness check."""

    def __init__(self) -> None:
        self._taken: set = set()

    def register(self, email: str) -> str:
        key = _canon(email)
        if key in self._taken:
            raise ValueError("confusable with an existing account")
        self._taken.add(key)
        return key


class RawRegistry:
    """BUGGY: compare raw identifier strings."""

    def __init__(self) -> None:
        self._taken: set = set()

    def register(self, email: str) -> str:
        if email in self._taken:
            raise ValueError("exists")
        self._taken.add(email)
        return email


def registers_distinct_users(make_registry: Callable[[], object]) -> bool:
    registry = make_registry()
    registry.register("alice@app.example")
    try:
        registry.register("bob@app.example")
        return True
    except Exception:
        return False


def confusable_impersonation(make_registry: Callable[[], object]) -> bool:
    """True == a look-alike of an existing account registered as distinct (impersonation)."""
    registry = make_registry()
    registry.register("admin@app.example")
    lookalike = "adｍin@app.example"  # fullwidth 'm' -> NFKC 'admin'
    try:
        registry.register(lookalike)
        return True
    except ValueError:
        return False


def run_self_test() -> int:
    failures = 0
    if not registers_distinct_users(CanonicalizingRegistry):
        failures += 1
        print("FAIL: oracle rejected two genuinely distinct users", file=sys.stderr)
    if confusable_impersonation(CanonicalizingRegistry):
        failures += 1
        print("FAIL: oracle accepted a confusable look-alike", file=sys.stderr)
    if not confusable_impersonation(RawRegistry):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: raw registry confusable impersonation was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (canonicalizing registry folds the look-alike; raw registry caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Unicode account-confusion harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
