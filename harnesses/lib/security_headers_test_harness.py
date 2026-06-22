#!/usr/bin/env python3
"""Security-headers harness (jsonschema): require the response hardening header set.

OWASP Top 10:2025 A02 Security Misconfiguration (missing security headers).

WHY: Shipping responses without CSP / HSTS / X-Frame-Options / X-Content-Type-Options leaves
clickjacking, MIME-sniffing, and downgrade defenses off. A functional test (does it return
200?) never notices; only checking the response against a required-header CONTRACT catches it.

HOW: `HardenedApp` is the ORACLE -- emits the full hardening header set. `LaxApp` is the
planted defect -- only the functional headers. `missing_security_headers` validates the
emitted headers against the required-header jsonschema and reports a gap.

WHERE: lib/ -- dependency-backed (`jsonschema`), in-process.

Self-test:
    python harnesses/lib/security_headers_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

from jsonschema import ValidationError, validate

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["missing_security_headers"]

DOSSIER = {
    "name": "security_headers",
    "path": "harnesses/lib/security_headers_test_harness.py",
    "flavor": "lib",
    "dependency": "jsonschema",
    "standard": "OWASP Top 10:2025 A02 Security Misconfiguration (missing security headers)",
    "failure_class": "A response missing CSP/HSTS/X-Frame-Options/X-Content-Type-Options",
    "oracle": "HardenedApp.headers - emit the full hardening header set",
    "buggy": "LaxApp.headers - functional headers only",
    "planted_mutant": "a response lacking the required security headers",
    "proof_file": "tests/lib/test_security_headers_proof.py",
    "vacuity_targets": ["missing_security_headers"],
    "commands": ["python harnesses/lib/security_headers_test_harness.py --self-test"],
    "known_limits": "header presence contract; not CSP-directive strength analysis",
    "related": ["cookie_security", "tls_verification"],
}

_REQUIRED = {
    "type": "object",
    "required": [
        "Content-Security-Policy", "Strict-Transport-Security",
        "X-Frame-Options", "X-Content-Type-Options",
    ],
}


class HardenedApp:
    """ORACLE: emit the full hardening header set."""

    def headers(self) -> dict:
        return {
            "Content-Type": "text/html",
            "Content-Security-Policy": "default-src 'self'",
            "Strict-Transport-Security": "max-age=63072000",
            "X-Frame-Options": "DENY",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
        }


class LaxApp:
    """BUGGY: functional headers only."""

    def headers(self) -> dict:
        return {"Content-Type": "text/html"}  # BUG: no security headers


def serves_content(make_app: Callable[[], object]) -> bool:
    return make_app().headers().get("Content-Type") == "text/html"


def missing_security_headers(make_app: Callable[[], object]) -> bool:
    """True == the response is missing a required security header (the bug)."""
    try:
        validate(make_app().headers(), _REQUIRED)
        return False
    except ValidationError:
        return True


def run_self_test() -> int:
    failures = 0
    if not serves_content(HardenedApp):
        failures += 1
        print("FAIL: oracle did not serve content", file=sys.stderr)
    if missing_security_headers(HardenedApp):
        failures += 1
        print("FAIL: oracle was missing a required security header", file=sys.stderr)
    if not missing_security_headers(LaxApp):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: lax app's missing security headers were NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (hardened app passes the header contract; lax app caught missing them)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Security-headers harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
