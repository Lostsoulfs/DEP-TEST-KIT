#!/usr/bin/env python3
"""SSRF URL-guard harness (idna): connection-time IP pinning defeats DNS rebinding.

OWASP Top 10:2025 A01 Broken Access Control (which now absorbs SSRF). 2025/2026 bypasses:
DNS rebinding / TOCTOU (CVE-2025-68437) and decimal/hex/octal encodings of the cloud
metadata endpoint 169.254.169.254.

WHY: The usual SSRF mitigation -- parse the URL, resolve the host, check the IP, then hand
the HOSTNAME to an HTTP client -- is a time-of-check/time-of-use bug: the client RE-RESOLVES
the host at connect time, so an attacker whose DNS flips public->private between the two
lookups reaches internal services. A test that only feeds a literal http://169.254.169.254/
passes a string denylist and never exercises the rebind.

HOW: `PinningGuard` is the ORACLE -- it resolves the host ONCE (idna-canonicalized), rejects
any non-global resolved IP (ipaddress), and connects to that PINNED IP, so a later DNS flip
cannot move the connection. `DenylistGuard` is the planted defect -- it checks the host
string against a denylist and lets the transport re-resolve. `allows_ssrf` drives a rebinding
resolver (public for the check, link-local for the connect).

WHERE: lib/ -- dependency-backed (`idna`, IDNA2008 host canonicalization that defeats
IDN/denylist confusion) but fully in-process; the resolver is injected, so no real DNS.

Self-test:
    python harnesses/lib/ssrf_url_guard_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import ipaddress
import sys
from typing import Callable
from urllib.parse import urlparse

import idna

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["allows_ssrf"]

DOSSIER = {
    "name": "ssrf_url_guard",
    "path": "harnesses/lib/ssrf_url_guard_test_harness.py",
    "flavor": "lib",
    "dependency": "idna",
    "standard": "OWASP Top 10:2025 A01 Broken Access Control (SSRF) - DNS rebinding / TOCTOU",
    "failure_class": (
        "Validate the host then let the transport re-resolve it (rebinding reaches internal)"
    ),
    "oracle": (
        "PinningGuard.fetch - resolve once, reject non-global IPs, connect to the pinned IP"
    ),
    "buggy": "DenylistGuard.fetch - host-string denylist, then re-resolve at connect time",
    "planted_mutant": (
        "a rebinding resolver flips public->169.254.169.254 between check and connect"
    ),
    "proof_file": "tests/lib/test_ssrf_url_guard_proof.py",
    "vacuity_targets": ["allows_ssrf"],
    "commands": ["python harnesses/lib/ssrf_url_guard_test_harness.py --self-test"],
    "known_limits": (
        "models the rebinding TOCTOU; decimal/hex IP encodings are normalized by ipaddress, "
        "not separately fuzzed here"
    ),
    "related": ["tls_verification", "failopen_authz", "agent_capability_allowlist (ASI03)"],
}

_META = "169.254.169.254"  # cloud metadata / link-local target


class Blocked(Exception):
    """Raised when a fetch is refused as SSRF."""


def _canonical_host(host: str) -> str:
    try:
        return idna.encode(host, uts46=True).decode("ascii")
    except idna.IDNAError:
        return host.lower()


class PinningGuard:
    """ORACLE: resolve once, reject non-global IPs, connect to the pinned IP."""

    def fetch(self, url: str, resolver: Callable[[str], str]) -> str:
        host = _canonical_host(urlparse(url).hostname or "")
        ip = ipaddress.ip_address(resolver(host))  # resolve ONCE
        if not ip.is_global:
            raise Blocked(f"non-global IP {ip}")
        return str(ip)  # connect to the PINNED ip (no re-resolution)


class DenylistGuard:
    """BUGGY: deny by host string, then re-resolve at connect time (rebindable)."""

    _DENY = {"169.254.169.254", "localhost", "127.0.0.1"}

    def fetch(self, url: str, resolver: Callable[[str], str]) -> str:
        host = urlparse(url).hostname or ""
        if host in self._DENY:  # string denylist, no normalization
            raise Blocked("denylisted host")
        resolver(host)  # "validation" resolve (result ignored)
        return resolver(host)  # connect RE-resolves -> rebinding window


def _rebinding_resolver() -> Callable[[str], str]:
    seq = ["93.184.216.34", _META]  # public first (check), link-local second (connect)

    def resolve(host: str) -> str:
        return seq.pop(0) if seq else _META

    return resolve


def fetches_public_ok(make_guard: Callable[[], object]) -> bool:
    """True == the guard connects to a normal public host (no false positive)."""
    try:
        ip = make_guard().fetch("http://example.com/", lambda host: "93.184.216.34")
    except Blocked:
        return False
    return ip == "93.184.216.34"


def allows_ssrf(make_guard: Callable[[], object]) -> bool:
    """True == the guard ends up connected to a private/link-local IP (the SSRF bug)."""
    try:
        connected = make_guard().fetch("http://rebind.example.com/", _rebinding_resolver())
    except Blocked:
        return False
    return not ipaddress.ip_address(connected).is_global


def run_self_test() -> int:
    failures = 0
    if not fetches_public_ok(PinningGuard):
        failures += 1
        print("FAIL: oracle blocked a legitimate public fetch", file=sys.stderr)
    if allows_ssrf(PinningGuard):
        failures += 1
        print("FAIL: oracle was rebound to an internal IP", file=sys.stderr)
    if not allows_ssrf(DenylistGuard):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: denylist guard was NOT caught reaching the metadata IP", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (pinning guard stays public; denylist guard rebinds to 169.254.169.254)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SSRF URL-guard / DNS-rebinding harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
