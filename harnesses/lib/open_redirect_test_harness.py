#!/usr/bin/env python3
"""Open-redirect harness (idna): same-site / allowlist redirect validation.

OWASP Top 10:2025 A01 Broken Access Control (Unvalidated Redirects and Forwards).

WHY: A login flow that bounces the browser to a user-supplied `next=` parameter without
validating it sends victims to attacker phishing pages under the app's trust. Naive string
checks (startswith('/'), 'app.example' in url) are bypassed by `//evil.com`, `https:evil.com`,
`/\evil.com`, and suffix tricks like `https://app.example.evil.com`.

HOW: `AllowlistRedirect` is the ORACLE -- it parses the target, idna-canonicalizes the host,
and returns the target only when it is a same-origin RELATIVE path or its host is in the
allowlist; otherwise it falls back to "/". `OpenRedirect` is the planted defect -- it returns
the target unchanged. `redirects_offsite` feeds an off-site target and reports whether the
browser would leave the allowed origin.

WHERE: lib/ -- dependency-backed (`idna` host canonicalization), in-process.

Self-test:
    python harnesses/lib/open_redirect_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable
from urllib.parse import urlparse

import idna

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["redirects_offsite"]

DOSSIER = {
    "name": "open_redirect",
    "path": "harnesses/lib/open_redirect_test_harness.py",
    "flavor": "lib",
    "dependency": "idna",
    "standard": "OWASP Top 10:2025 A01 Broken Access Control (open redirect)",
    "failure_class": "Redirecting the browser to a user-supplied off-site URL (phishing)",
    "oracle": "AllowlistRedirect.resolve - same-site relative or allowlisted host, else '/'",
    "buggy": "OpenRedirect.resolve - return the target unchanged",
    "planted_mutant": "feed https://evil.example/phish; the naive redirect follows it",
    "proof_file": "tests/lib/test_open_redirect_proof.py",
    "vacuity_targets": ["redirects_offsite"],
    "commands": ["python harnesses/lib/open_redirect_test_harness.py --self-test"],
    "known_limits": (
        "host allowlist + relative-path check; not full URL-parser-differential fuzzing"
    ),
    "related": ["ssrf_url_guard", "jwt_audience_binding"],
}

_ALLOWED = {"app.example"}


def _host(url: str):
    host = urlparse(url).hostname
    if not host:
        return None
    try:
        return idna.encode(host, uts46=True).decode("ascii")
    except idna.IDNAError:
        return host.lower()


class AllowlistRedirect:
    """ORACLE: allow same-site relative paths or allowlisted hosts; else fall back to '/'."""

    def resolve(self, target: str) -> str:
        parsed = urlparse(target)
        host = _host(target)
        if host is None and not parsed.netloc:
            if target.startswith("/") and not target.startswith("//") and "\\" not in target:
                return target
            return "/"
        if host in _ALLOWED:
            return target
        return "/"


class OpenRedirect:
    """BUGGY: redirect to whatever was supplied."""

    def resolve(self, target: str) -> str:
        return target  # BUG: no validation


def allows_same_site(make_redirect: Callable[[], object]) -> bool:
    return make_redirect().resolve("/dashboard") == "/dashboard"


def redirects_offsite(make_redirect: Callable[[], object]) -> bool:
    """True == the browser is sent to an off-allowlist host (open redirect)."""
    result = make_redirect().resolve("https://evil.example/phish")
    host = _host(result)
    return host is not None and host not in _ALLOWED


def run_self_test() -> int:
    failures = 0
    if not allows_same_site(AllowlistRedirect):
        failures += 1
        print("FAIL: oracle blocked a legitimate same-site redirect", file=sys.stderr)
    if redirects_offsite(AllowlistRedirect):
        failures += 1
        print("FAIL: oracle followed an off-site redirect", file=sys.stderr)
    if not redirects_offsite(OpenRedirect):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: open redirect was NOT caught following off-site", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (allowlist keeps same-origin; naive redirect follows off-site -- caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Open-redirect validation harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
