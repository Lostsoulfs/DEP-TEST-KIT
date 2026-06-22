#!/usr/bin/env python3
"""TLS verification harness (requests): a client that refuses an invalid certificate.

OWASP Top 10:2025 A02 Security Misconfiguration (moved #5 -> #2 in 2025; disabling TLS
certificate verification, e.g. `requests` with `verify=False`, is a canonical example).

WHY: `verify=False` (or an env/CA misconfig) silently turns every HTTPS call into an
unauthenticated channel open to MITM -- and it passes functional tests, because the happy
path still returns 200. The failure only shows when the server presents an INVALID
certificate: a verifying client refuses, a non-verifying client connects anyway.

HOW: `StrictClient` is the ORACLE -- it refuses cleartext `http://` and keeps
`session.verify = True`, so an invalid-cert server raises `requests` `SSLError`.
`InsecureClient` is the planted defect -- `session.verify = False`. The server is an injected
`requests` transport adapter: `_InvalidCertAdapter` raises `SSLError` when verification is on
(an honest TLS stack rejecting a bad cert) and returns 200 when it is off; `_ValidCertAdapter`
always returns 200. `accepts_invalid_cert` reports whether the bad-cert server got a 200.

WHERE: lib/ -- dependency-backed (`requests`: Session, HTTPAdapter, SSLError, the `verify`
flag) but fully in-process via a mounted fake adapter, so no socket or network is used.

Self-test:
    python harnesses/lib/tls_verification_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import SSLError
from requests.models import Response

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["accepts_invalid_cert"]

DOSSIER = {
    "name": "tls_verification",
    "path": "harnesses/lib/tls_verification_test_harness.py",
    "flavor": "lib",
    "dependency": "requests",
    "standard": "OWASP Top 10:2025 A02 Security Misconfiguration - disabled TLS verification",
    "failure_class": "An HTTP client with verify=False accepts an invalid certificate (MITM)",
    "oracle": "StrictClient.fetch - refuse cleartext, keep verify=True (SSLError on bad cert)",
    "buggy": "InsecureClient.fetch - session.verify=False",
    "planted_mutant": "an invalid-cert server returns 200 to the non-verifying client",
    "proof_file": "tests/lib/test_tls_verification_proof.py",
    "vacuity_targets": ["accepts_invalid_cert"],
    "commands": ["python harnesses/lib/tls_verification_test_harness.py --self-test"],
    "known_limits": (
        "models cert-verification on/off via an injected adapter; not weak-cipher or "
        "protocol-downgrade negotiation"
    ),
    "related": ["ssrf_url_guard", "crypto_agility", "oauth_pkce"],
}


class InsecureTransport(Exception):
    """Raised when a cleartext URL is refused."""


def _ok(url: str) -> Response:
    resp = Response()
    resp.status_code = 200
    resp.url = url
    resp._content = b"ok"
    return resp


class _InvalidCertAdapter(HTTPAdapter):
    """Server with a bad cert: an honest (verifying) client must reject it."""

    def send(self, request, *args, **kwargs):
        if kwargs.get("verify", True):
            raise SSLError("certificate verify failed: self-signed certificate")
        return _ok(request.url)


class _ValidCertAdapter(HTTPAdapter):
    """Server with a valid cert: returns 200 to a verifying client."""

    def send(self, request, *args, **kwargs):
        return _ok(request.url)


def _client_session(verify: bool, server: HTTPAdapter) -> requests.Session:
    session = requests.Session()
    session.verify = verify
    session.mount("https://", server)
    session.mount("http://", server)
    return session


class StrictClient:
    """ORACLE: refuse cleartext, keep TLS verification on."""

    def fetch(self, url: str, server: HTTPAdapter) -> int:
        if urlparse(url).scheme != "https":
            raise InsecureTransport("cleartext refused")
        return _client_session(True, server).get(url).status_code


class InsecureClient:
    """BUGGY: disable certificate verification."""

    def fetch(self, url: str, server: HTTPAdapter) -> int:
        return _client_session(False, server).get(url).status_code  # BUG: verify=False


def fetches_valid_https_ok(make_client: Callable[[], object]) -> bool:
    """True == the client completes a normal valid-cert HTTPS call (no false positive)."""
    try:
        return make_client().fetch("https://api.example/x", _ValidCertAdapter()) == 200
    except (SSLError, InsecureTransport):
        return False


def accepts_invalid_cert(make_client: Callable[[], object]) -> bool:
    """True == the client got a 200 from an invalid-cert server (the bug)."""
    try:
        return make_client().fetch("https://bank.example/api", _InvalidCertAdapter()) == 200
    except (SSLError, InsecureTransport):
        return False


def run_self_test() -> int:
    failures = 0
    if not fetches_valid_https_ok(StrictClient):
        failures += 1
        print("FAIL: oracle rejected a valid-cert HTTPS call", file=sys.stderr)
    if accepts_invalid_cert(StrictClient):
        failures += 1
        print("FAIL: oracle accepted an invalid certificate", file=sys.stderr)
    if not accepts_invalid_cert(InsecureClient):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: verify=False client was NOT caught accepting a bad cert", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (verifying client rejects the bad cert; verify=False client accepts it)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TLS certificate-verification harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
