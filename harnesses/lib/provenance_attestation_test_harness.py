#!/usr/bin/env python3
"""Build-provenance digest-binding harness (cryptography Ed25519 + hashlib).

OWASP Top 10:2025 A03/A08 Software Supply Chain & Integrity, per the 2026 SLSA / Sigstore
verification rule: "the subject.digest of provenance MUST match the sha256 of the artifact
being deployed -- generating provenance is useless if you don't verify it at deploy time"
(cf. the Mini Shai-Hulud npm incident).

WHY: A build attestation can carry a perfectly valid signature and still be useless if the
verifier never binds it to the artifact actually being deployed. An attacker reuses a real,
signed attestation for a GOOD artifact and ships a DIFFERENT (malicious) artifact under it.
A test that checks "is the attestation's signature valid?" passes -- the signature IS valid.
Only verifying that the attested subject digest equals the deployed artifact's digest catches
the swap; a mock can't.

HOW: `ProvenanceVerifier` is the ORACLE -- it Ed25519-verifies the attestation, then requires
`sha256(artifact) == attestation.subject_sha256` (constant-time). `SigOnlyVerifier` is the
planted defect -- it verifies the signature and returns True without binding the digest.
`accepts_unbound_artifact` presents a malicious artifact with the GOOD artifact's valid
attestation+signature: the oracle rejects on the digest mismatch, the sig-only verifier accepts.

WHERE: lib/ -- in-process, deterministic. Uses `cryptography` (+ stdlib hashlib/hmac).

Self-test:
    python harnesses/lib/provenance_attestation_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sys
from typing import Callable, Tuple

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["accepts_unbound_artifact"]

DOSSIER = {
    "name": "provenance_attestation",
    "path": "harnesses/lib/provenance_attestation_test_harness.py",
    "flavor": "lib",
    "dependency": "cryptography (Ed25519) + stdlib hashlib",
    "standard": "OWASP Top 10:2025 A03/A08 + SLSA/Sigstore 2026 provenance verification",
    "failure_class": (
        "Verifying an attestation's signature but not binding subject.digest to the artifact"
    ),
    "oracle": (
        "ProvenanceVerifier.verify — verify sig AND require sha256(artifact)==attested digest"
    ),
    "buggy": "SigOnlyVerifier.verify — verify the signature only",
    "planted_mutant": (
        "ship a different artifact under a GOOD artifact's valid attestation; oracle rejects"
    ),
    "proof_file": "tests/lib/test_provenance_attestation_proof.py",
    "vacuity_targets": ["accepts_unbound_artifact"],
    "commands": ["python harnesses/lib/provenance_attestation_test_harness.py --self-test"],
    "known_limits": (
        "checks digest binding + signature; not a full Rekor transparency-log inclusion proof"
    ),
    "related": ["agent_tool_manifest (ASI04)", "hallucinated_dependency", "supplychain"],
}


def _attest(artifact: bytes, builder: Ed25519PrivateKey) -> Tuple[bytes, bytes]:
    digest = hashlib.sha256(artifact).hexdigest()
    attestation = json.dumps({"subject_sha256": digest, "source": "git+https://repo@abc123"},
                             sort_keys=True).encode()
    return attestation, builder.sign(attestation)


class ProvenanceVerifier:
    """ORACLE: verify the signature AND bind the attested digest to the artifact."""

    def __init__(self, builder_public_key: Ed25519PublicKey) -> None:
        self.builder_public_key = builder_public_key

    def verify(self, artifact: bytes, attestation: bytes, signature: bytes) -> bool:
        self.builder_public_key.verify(signature, attestation)  # raises on bad sig
        claimed = json.loads(attestation)["subject_sha256"]
        actual = hashlib.sha256(artifact).hexdigest()
        if not hmac.compare_digest(claimed, actual):
            raise ValueError("artifact digest does not match attested subject digest")
        return True


class SigOnlyVerifier:
    """BUGGY: verify the attestation signature; never bind it to the artifact."""

    def __init__(self, builder_public_key: Ed25519PublicKey) -> None:
        self.builder_public_key = builder_public_key

    def verify(self, artifact: bytes, attestation: bytes, signature: bytes) -> bool:
        self.builder_public_key.verify(signature, attestation)  # sig IS valid...
        return True  # BUG: the attested digest is never compared to sha256(artifact)


def verifies_bound_artifact(make_verifier: Callable[[Ed25519PublicKey], object]) -> bool:
    builder = Ed25519PrivateKey.generate()
    good = b"legit-package-1.0.0"
    attestation, sig = _attest(good, builder)
    try:
        return bool(make_verifier(builder.public_key()).verify(good, attestation, sig))
    except Exception:
        return False


def accepts_unbound_artifact(make_verifier: Callable[[Ed25519PublicKey], object]) -> bool:
    """Ship a DIFFERENT artifact under a GOOD artifact's valid attestation. True == accepted
    (the bug); False == rejected on the digest mismatch."""
    builder = Ed25519PrivateKey.generate()
    good = b"legit-package-1.0.0"
    attestation, sig = _attest(good, builder)
    malicious = b"MALICIOUS-package-with-backdoor"
    try:
        make_verifier(builder.public_key()).verify(malicious, attestation, sig)
        return True   # accepted a swapped artifact under a valid attestation -> compromised
    except Exception:
        return False  # digest binding (or sig) rejected it


def run_self_test() -> int:
    failures = 0
    if not verifies_bound_artifact(ProvenanceVerifier):
        failures += 1
        print("FAIL: oracle rejected an artifact that matches its attestation", file=sys.stderr)
    if accepts_unbound_artifact(ProvenanceVerifier):
        failures += 1
        print("FAIL: oracle accepted an artifact unbound to its attestation", file=sys.stderr)
    if not accepts_unbound_artifact(SigOnlyVerifier):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print(
            "FAIL: signature-only verifier was NOT caught accepting a swapped artifact",
            file=sys.stderr,
        )
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print(
        "self-test: OK (digest-binding verifier rejects a swapped artifact; sig-only verifier "
        "caught)"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build-provenance digest-binding harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
