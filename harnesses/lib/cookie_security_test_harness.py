#!/usr/bin/env python3
"""Cookie-security harness (jsonschema): session cookies need Secure/HttpOnly/SameSite.

OWASP Top 10:2025 A02 Security Misconfiguration (insecure cookie flags, CWE-1004/614).

WHY: A session cookie without `Secure` leaks over cleartext, without `HttpOnly` is readable by
XSS, and without `SameSite` rides cross-site requests (CSRF). Setting the cookie "works" either
way; only checking the attribute CONTRACT catches the missing flags.

HOW: `SecureCookieSetter` is the ORACLE -- emits Secure + HttpOnly + SameSite=Strict.
`InsecureCookieSetter` is the planted defect -- name/value only. `cookie_missing_flags`
validates the attributes against the required-flags jsonschema.

WHERE: lib/ -- dependency-backed (`jsonschema`), in-process.

Self-test:
    python harnesses/lib/cookie_security_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

from jsonschema import ValidationError, validate

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["cookie_missing_flags"]

DOSSIER = {
    "name": "cookie_security",
    "path": "harnesses/lib/cookie_security_test_harness.py",
    "flavor": "lib",
    "dependency": "jsonschema",
    "standard": "OWASP Top 10:2025 A02 Security Misconfiguration (cookie flags CWE-1004/614)",
    "failure_class": "A session cookie missing Secure / HttpOnly / SameSite",
    "oracle": "SecureCookieSetter.set - Secure + HttpOnly + SameSite=Strict",
    "buggy": "InsecureCookieSetter.set - name/value only",
    "planted_mutant": "a session cookie set without the security flags",
    "proof_file": "tests/lib/test_cookie_security_proof.py",
    "vacuity_targets": ["cookie_missing_flags"],
    "commands": ["python harnesses/lib/cookie_security_test_harness.py --self-test"],
    "known_limits": "flag presence contract; not __Host- prefix or cookie-scope analysis",
    "related": ["security_headers", "csrf_token"],
}

_REQUIRED = {"type": "object", "required": ["Secure", "HttpOnly", "SameSite"]}


class SecureCookieSetter:
    """ORACLE: set the session cookie with the hardening flags."""

    def set(self, value: str) -> dict:
        return {"name": "sid", "value": value, "Secure": True, "HttpOnly": True,
                "SameSite": "Strict"}


class InsecureCookieSetter:
    """BUGGY: set name/value only."""

    def set(self, value: str) -> dict:
        return {"name": "sid", "value": value}  # BUG: no security flags


def sets_the_cookie(make_setter: Callable[[], object]) -> bool:
    return make_setter().set("abc").get("value") == "abc"


def cookie_missing_flags(make_setter: Callable[[], object]) -> bool:
    """True == the session cookie is missing a required security flag (the bug)."""
    try:
        validate(make_setter().set("abc"), _REQUIRED)
        return False
    except ValidationError:
        return True


def run_self_test() -> int:
    failures = 0
    if not sets_the_cookie(SecureCookieSetter):
        failures += 1
        print("FAIL: oracle did not set the cookie value", file=sys.stderr)
    if cookie_missing_flags(SecureCookieSetter):
        failures += 1
        print("FAIL: oracle cookie was missing a security flag", file=sys.stderr)
    if not cookie_missing_flags(InsecureCookieSetter):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: insecure cookie's missing flags were NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (secure setter passes the flag contract; insecure cookie caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cookie-security harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
