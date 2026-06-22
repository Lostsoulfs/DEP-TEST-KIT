#!/usr/bin/env python3
"""CORS-misconfiguration harness (idna): reflect only allowlisted origins, never arbitrary.

OWASP Top 10:2025 A02 Security Misconfiguration (permissive CORS, CWE-942).

WHY: Reflecting the request `Origin` into `Access-Control-Allow-Origin` together with
`Allow-Credentials: true` lets ANY site read authenticated responses -- a cross-origin data
leak. The allowed origins must be checked against an allowlist (host idna-canonicalized).

HOW: `AllowlistCors` is the ORACLE -- it returns ACAO only when the origin's host is in the
allowlist, otherwise no CORS headers. `ReflectingCors` is the planted defect -- it reflects any
Origin with credentials. `reflects_untrusted_origin` sends an attacker Origin and reports
whether it was reflected back as allowed.

WHERE: lib/ -- dependency-backed (`idna` host canonicalization), in-process.

Self-test:
    python harnesses/lib/cors_misconfig_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable
from urllib.parse import urlparse

import idna

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["reflects_untrusted_origin"]

DOSSIER = {
    "name": "cors_misconfig",
    "path": "harnesses/lib/cors_misconfig_test_harness.py",
    "flavor": "lib",
    "dependency": "idna",
    "standard": "OWASP Top 10:2025 A02 Security Misconfiguration - permissive CORS (CWE-942)",
    "failure_class": "Reflecting an arbitrary Origin with credentials (cross-origin data leak)",
    "oracle": "AllowlistCors.headers - ACAO only for allowlisted origin hosts",
    "buggy": "ReflectingCors.headers - reflect any Origin with Allow-Credentials",
    "planted_mutant": "an attacker Origin https://evil.com is reflected back as allowed",
    "proof_file": "tests/lib/test_cors_misconfig_proof.py",
    "vacuity_targets": ["reflects_untrusted_origin"],
    "commands": ["python harnesses/lib/cors_misconfig_test_harness.py --self-test"],
    "known_limits": "origin allowlisting; not preflight method/header negotiation review",
    "related": ["security_headers", "open_redirect", "csrf_token"],
}

_ALLOWED = {"app.example"}
_ACAO = "Access-Control-Allow-Origin"


def _host(origin: str):
    host = urlparse(origin).hostname
    if not host:
        return None
    try:
        return idna.encode(host, uts46=True).decode("ascii")
    except idna.IDNAError:
        return host.lower()


class AllowlistCors:
    """ORACLE: return ACAO only for allowlisted origin hosts."""

    def headers(self, origin: str) -> dict:
        if _host(origin) in _ALLOWED:
            return {_ACAO: origin, "Access-Control-Allow-Credentials": "true"}
        return {}


class ReflectingCors:
    """BUGGY: reflect any Origin with credentials."""

    def headers(self, origin: str) -> dict:
        return {_ACAO: origin, "Access-Control-Allow-Credentials": "true"}  # BUG


def allows_trusted_origin(make_cors: Callable[[], object]) -> bool:
    return make_cors().headers("https://app.example").get(_ACAO) == "https://app.example"


def reflects_untrusted_origin(make_cors: Callable[[], object]) -> bool:
    """True == an untrusted Origin was reflected back as allowed (permissive CORS)."""
    return make_cors().headers("https://evil.com").get(_ACAO) == "https://evil.com"


def run_self_test() -> int:
    failures = 0
    if not allows_trusted_origin(AllowlistCors):
        failures += 1
        print("FAIL: oracle did not allow a trusted origin", file=sys.stderr)
    if reflects_untrusted_origin(AllowlistCors):
        failures += 1
        print("FAIL: oracle reflected an untrusted origin", file=sys.stderr)
    if not reflects_untrusted_origin(ReflectingCors):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: reflecting CORS untrusted-origin reflection was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (allowlist CORS denies the attacker origin; reflecting CORS echoes it)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CORS-misconfiguration harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
