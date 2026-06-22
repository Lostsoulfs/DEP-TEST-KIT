#!/usr/bin/env python3
"""Subresource Integrity harness (cryptography): bind a loaded resource to its SRI hash.

OWASP Top 10:2025 A08 Software and Data Integrity Failures (Subresource Integrity).

WHY: Loading a third-party script/asset without checking its hash means a compromised CDN can
swap in malicious code and the app runs it. SRI binds the expected `sha384-...` digest; the
loader must recompute the hash of the fetched bytes and refuse a mismatch.

HOW: `SriVerifier` is the ORACLE -- recompute sha384 and compare to the expected SRI digest,
refusing a mismatch. `NoIntegrityLoader` is the planted defect -- it returns whatever was
fetched. `loads_tampered_resource` serves tampered bytes under the original digest and reports
whether they were loaded.

WHERE: lib/ -- dependency-backed (`cryptography` SHA-384), in-process.

Self-test:
    python harnesses/lib/subresource_integrity_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import base64
import sys
from typing import Callable

from cryptography.hazmat.primitives import hashes

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["loads_tampered_resource"]

DOSSIER = {
    "name": "subresource_integrity",
    "path": "harnesses/lib/subresource_integrity_test_harness.py",
    "flavor": "lib",
    "dependency": "cryptography",
    "standard": "OWASP Top 10:2025 A08 Integrity Failures - Subresource Integrity (SRI)",
    "failure_class": "Loading a fetched resource without verifying its SRI hash (CDN tampering)",
    "oracle": "SriVerifier.load - recompute sha384 and compare to the expected SRI digest",
    "buggy": "NoIntegrityLoader.load - return the fetched bytes unchecked",
    "planted_mutant": "serve tampered bytes under the original digest; the naive loader runs them",
    "proof_file": "tests/lib/test_subresource_integrity_proof.py",
    "vacuity_targets": ["loads_tampered_resource"],
    "commands": ["python harnesses/lib/subresource_integrity_test_harness.py --self-test"],
    "known_limits": "hash binding only; not transport TLS or provenance attestation",
    "related": ["provenance_attestation", "crypto_correctness", "webhook_signature"],
}


def _sri(data: bytes) -> str:
    digest = hashes.Hash(hashes.SHA384())
    digest.update(data)
    return "sha384-" + base64.b64encode(digest.finalize()).decode()


class SriVerifier:
    """ORACLE: recompute the hash and refuse a mismatch."""

    def load(self, data: bytes, expected: str) -> bytes:
        if _sri(data) != expected:
            raise ValueError("subresource integrity mismatch")
        return data


class NoIntegrityLoader:
    """BUGGY: return the fetched bytes without checking."""

    def load(self, data: bytes, expected: str) -> bytes:
        return data  # BUG: no integrity check


def loads_intact_resource(make_loader: Callable[[], object]) -> bool:
    data = b"console.log('ok')"
    try:
        return make_loader().load(data, _sri(data)) == data
    except Exception:
        return False


def loads_tampered_resource(make_loader: Callable[[], object]) -> bool:
    """True == tampered bytes were loaded under the original digest (the bug)."""
    expected = _sri(b"console.log('ok')")
    try:
        make_loader().load(b"console.log('pwned')", expected)
        return True
    except Exception:
        return False


def run_self_test() -> int:
    failures = 0
    if not loads_intact_resource(SriVerifier):
        failures += 1
        print("FAIL: oracle rejected an intact resource", file=sys.stderr)
    if loads_tampered_resource(SriVerifier):
        failures += 1
        print("FAIL: oracle loaded a tampered resource", file=sys.stderr)
    if not loads_tampered_resource(NoIntegrityLoader):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: no-integrity loader running tampered bytes was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (SRI verifier refuses tampered bytes; naive loader runs them -- caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Subresource Integrity harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
