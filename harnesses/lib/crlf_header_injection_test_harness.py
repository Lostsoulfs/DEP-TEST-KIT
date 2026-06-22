#!/usr/bin/env python3
"""HTTP header (CRLF) injection harness (requests): reject CR/LF in header values.

OWASP Top 10:2025 A05 Injection (CRLF / HTTP response splitting, CWE-113).

WHY: Building response headers by string-concatenating user input lets an attacker embed
`\r\n` and inject their own headers (Set-Cookie, redirects) or split the response. A library
that validates header values rejects the CRLF; a hand-rolled `f"{name}: {value}"` lets it ride.

HOW: `SafeHeaderWriter` is the ORACLE -- it sets the header through `requests`' header
preparation, which calls `check_header_validity` and raises `InvalidHeader` on CR/LF.
`RawHeaderWriter` is the planted defect -- it concatenates the raw string.
`header_injection_succeeds` submits a value carrying `\r\nSet-Cookie: ...` and reports whether
the injected header survived into the output.

WHERE: lib/ -- dependency-backed (`requests` header validation), in-process, no network.

Self-test:
    python harnesses/lib/crlf_header_injection_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

import requests

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["header_injection_succeeds"]

DOSSIER = {
    "name": "crlf_header_injection",
    "path": "harnesses/lib/crlf_header_injection_test_harness.py",
    "flavor": "lib",
    "dependency": "requests",
    "standard": "OWASP Top 10:2025 A05 Injection - CRLF / HTTP response splitting (CWE-113)",
    "failure_class": "Header value with embedded CR/LF injects a new header / splits the response",
    "oracle": "SafeHeaderWriter.write - set via requests' validated header preparation",
    "buggy": "RawHeaderWriter.write - f-string concatenation of name and value",
    "planted_mutant": "a value 'abc\\r\\nSet-Cookie: sid=evil' carries an injected header",
    "proof_file": "tests/lib/test_crlf_header_injection_proof.py",
    "vacuity_targets": ["header_injection_succeeds"],
    "commands": ["python harnesses/lib/crlf_header_injection_test_harness.py --self-test"],
    "known_limits": "header-value CR/LF validation; not full response-splitting body smuggling",
    "related": ["advanced_injection", "open_redirect"],
}

_PAYLOAD = "abc\r\nSet-Cookie: sid=evil"


class SafeHeaderWriter:
    """ORACLE: set the header through requests' validated preparation."""

    def write(self, name: str, value: str) -> dict:
        req = requests.PreparedRequest()
        req.prepare_headers({name: value})  # raises InvalidHeader on CR/LF
        return dict(req.headers)


class RawHeaderWriter:
    """BUGGY: concatenate the raw header line."""

    def write(self, name: str, value: str) -> dict:
        return {"_raw": f"{name}: {value}"}  # BUG: CR/LF rides along


def writes_valid_header(make_writer: Callable[[], object]) -> bool:
    try:
        make_writer().write("X-Token", "abc123")
        return True
    except Exception:
        return False


def header_injection_succeeds(make_writer: Callable[[], object]) -> bool:
    """True == the injected CRLF/header survived into the output (response splitting)."""
    try:
        result = make_writer().write("X-Token", _PAYLOAD)
    except Exception:
        return False  # rejected at validation
    return any("Set-Cookie" in str(v) or "\r\n" in str(v) for v in result.values())


def run_self_test() -> int:
    failures = 0
    if not writes_valid_header(SafeHeaderWriter):
        failures += 1
        print("FAIL: oracle rejected a benign header value", file=sys.stderr)
    if header_injection_succeeds(SafeHeaderWriter):
        failures += 1
        print("FAIL: oracle let a CRLF-injected header through", file=sys.stderr)
    if not header_injection_succeeds(RawHeaderWriter):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: raw header-writer CRLF injection was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (requests rejects the CRLF; raw concatenation injects a header -- caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CRLF header-injection harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
