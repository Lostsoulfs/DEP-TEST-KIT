#!/usr/bin/env python3
"""Cryptographic-agility / deprecated-algorithm rejection harness (cryptography).

OWASP Top 10:2025 A04 Cryptographic Failures, sharpened by the 2026 NIST/CNSA-2.0
deprecation timeline (RSA-2048 & P-256 deprecated by 2030; SHA-1 / RSA-1024 already
disallowed; "harvest now, decrypt later").

WHY: A signature can be mathematically VALID and still be unacceptable because its
algorithm is deprecated. A verifier tested only with "does this signature verify?" passes
an RSA-1024 + SHA-1 signature -- it verifies fine -- and silently keeps trusting algorithms
NIST has retired. Crypto-agility means the verifier enforces an algorithm POLICY (minimum
key size, approved hashes) and rejects a downgraded one even though the math checks out.
A mock, and a verify-only test, cannot tell the difference.

HOW: `CryptoAgileVerifier` is the ORACLE -- before trusting the signature it rejects a
sub-3072-bit RSA key or a non-SHA-2 hash, then verifies. `LegacyVerifier` is the planted
defect -- it verifies the signature and ignores algorithm strength. `accepts_deprecated_signature`
presents a genuinely-valid RSA-1024 + SHA-1 signature: the oracle rejects it on policy, the
legacy verifier accepts it.

WHERE: lib/ -- in-process, deterministic. Uses `cryptography` (already in the lib extra;
declare in the matching extra for the flavor it ships in).

Self-test:
    python harnesses/lib/crypto_agility_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable, Tuple

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["accepts_deprecated_signature"]

DOSSIER = {
    "name": "crypto_agility",
    "path": "harnesses/lib/crypto_agility_test_harness.py",
    "flavor": "lib",
    "dependency": "cryptography",
    "standard": "OWASP Top 10:2025 A04 + NIST/CNSA-2.0 2026 deprecation (RSA<3072, SHA-1)",
    "failure_class": (
        "Accepting a valid-but-deprecated signature algorithm (no crypto-agility policy)"
    ),
    "oracle": "CryptoAgileVerifier.verify — enforce min RSA size + approved hash, then verify",
    "buggy": "LegacyVerifier.verify — verify the math, ignore algorithm strength",
    "planted_mutant": "a real RSA-1024 + SHA-1 signature; oracle rejects on policy, legacy accepts",
    "proof_file": "tests/lib/test_crypto_agility_proof.py",
    "vacuity_targets": ["accepts_deprecated_signature"],
    "commands": ["python harnesses/lib/crypto_agility_test_harness.py --self-test"],
    "known_limits": (
        "policy = RSA size + hash family; full PQC migration (ML-DSA) is a larger effort"
    ),
    "related": ["crypto_correctness (AEAD)", "jwt_alg_confusion", "agent_join_replay"],
}

_MESSAGE = b"agent action: deploy release v2"


def _rsa_signed(bits: int, hash_alg, message: bytes = _MESSAGE) -> Tuple[rsa.RSAPublicKey, bytes]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=bits)
    signature = key.sign(message, padding.PKCS1v15(), hash_alg)
    return key.public_key(), signature


class CryptoAgileVerifier:
    """ORACLE: enforce an algorithm policy BEFORE trusting the signature."""

    MIN_RSA_BITS = 3072
    APPROVED_HASHES = {"sha256", "sha384", "sha512"}

    def verify(self, public_key: rsa.RSAPublicKey, signature: bytes,
               message: bytes, hash_alg) -> bool:
        if public_key.key_size < self.MIN_RSA_BITS:
            raise ValueError(f"deprecated RSA key size {public_key.key_size} (< {self.MIN_RSA_BITS})")
        if hash_alg.name not in self.APPROVED_HASHES:
            raise ValueError(f"deprecated hash {hash_alg.name}")
        public_key.verify(signature, message, padding.PKCS1v15(), hash_alg)
        return True


class LegacyVerifier:
    """BUGGY: verify the signature mathematically; never check algorithm strength."""

    def verify(self, public_key: rsa.RSAPublicKey, signature: bytes,
               message: bytes, hash_alg) -> bool:
        public_key.verify(signature, message, padding.PKCS1v15(), hash_alg)
        return True  # BUG: a valid-but-deprecated signature is accepted


def accepts_strong_signature(make_verifier: Callable[[], object]) -> bool:
    pub, sig = _rsa_signed(3072, hashes.SHA256())
    try:
        return bool(make_verifier().verify(pub, sig, _MESSAGE, hashes.SHA256()))
    except Exception:
        return False


def accepts_deprecated_signature(make_verifier: Callable[[], object]) -> bool:
    """Present a genuinely-valid RSA-1024 + SHA-1 signature. True == accepted (the bug);
    False == rejected on policy."""
    pub, sig = _rsa_signed(1024, hashes.SHA1())
    try:
        make_verifier().verify(pub, sig, _MESSAGE, hashes.SHA1())
        return True   # accepted a deprecated-but-valid signature -> not crypto-agile
    except Exception:
        return False  # rejected on policy


def run_self_test() -> int:
    failures = 0
    if not accepts_strong_signature(CryptoAgileVerifier):
        failures += 1
        print("FAIL: oracle rejected an approved RSA-3072 + SHA-256 signature", file=sys.stderr)
    if accepts_deprecated_signature(CryptoAgileVerifier):
        failures += 1
        print("FAIL: oracle accepted a deprecated RSA-1024 + SHA-1 signature", file=sys.stderr)
    if not accepts_deprecated_signature(LegacyVerifier):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print(
            "FAIL: legacy verifier was NOT caught accepting a deprecated signature",
            file=sys.stderr,
        )
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print(
        "self-test: OK (agile verifier rejects deprecated RSA-1024/SHA-1; legacy verifier caught)"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Cryptographic-agility / deprecated-algorithm harness"
    )
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
