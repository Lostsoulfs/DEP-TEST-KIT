#!/usr/bin/env python3
"""Password-hashing harness (cryptography): salted slow KDF, not a fast unsalted digest.

OWASP Top 10:2025 A02 Security Misconfiguration / A07 Authentication Failures (CWE-916).

WHY: Storing passwords with a fast unsalted digest (md5/sha1) means two users with the same
password get the SAME stored hash -- trivially rainbow-tabled and revealing shared passwords.
A password store must use a per-password random salt and a deliberately slow KDF (scrypt).

HOW: `ScryptHasher` is the ORACLE -- scrypt with a random 16-byte salt, verified in constant
time, so the same password hashes differently each time. `WeakHasher` is the planted defect --
unsalted md5. `identical_hash_for_same_password` hashes one password twice and reports whether
the two stored values collide.

WHERE: lib/ -- dependency-backed (`cryptography` Scrypt KDF + constant-time verify), in-process.

Self-test:
    python harnesses/lib/password_hashing_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import hashlib
import secrets
import sys
from typing import Callable

from cryptography.exceptions import InvalidKey
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["identical_hash_for_same_password"]

DOSSIER = {
    "name": "password_hashing",
    "path": "harnesses/lib/password_hashing_test_harness.py",
    "flavor": "lib",
    "dependency": "cryptography",
    "standard": "OWASP Top 10:2025 A02/A07 - password storage (CWE-916 weak hash)",
    "failure_class": "Unsalted fast digest: same password -> same hash (rainbow-tableable)",
    "oracle": "ScryptHasher - scrypt with a random per-password salt, constant-time verify",
    "buggy": "WeakHasher - unsalted md5",
    "planted_mutant": "hash one password twice; the unsalted digest collides",
    "proof_file": "tests/lib/test_password_hashing_proof.py",
    "vacuity_targets": ["identical_hash_for_same_password"],
    "commands": ["python harnesses/lib/password_hashing_test_harness.py --self-test"],
    "known_limits": "salt + slow-KDF property; not parameter-tuning or pepper/HSM storage",
    "related": ["crypto_correctness", "crypto_agility", "secret_scanning"],
}


class ScryptHasher:
    """ORACLE: scrypt with a random salt; same password hashes differently each time."""

    def hash(self, password: str) -> str:
        salt = secrets.token_bytes(16)
        derived = Scrypt(salt=salt, length=32, n=2 ** 14, r=8, p=1).derive(password.encode())
        return salt.hex() + ":" + derived.hex()

    def verify(self, password: str, stored: str) -> bool:
        salt_hex, derived_hex = stored.split(":")
        kdf = Scrypt(salt=bytes.fromhex(salt_hex), length=32, n=2 ** 14, r=8, p=1)
        try:
            kdf.verify(password.encode(), bytes.fromhex(derived_hex))
            return True
        except InvalidKey:
            return False


class WeakHasher:
    """BUGGY: unsalted md5."""

    def hash(self, password: str) -> str:
        return hashlib.md5(password.encode()).hexdigest()

    def verify(self, password: str, stored: str) -> bool:
        return hashlib.md5(password.encode()).hexdigest() == stored


def verifies_correct_password(make_hasher: Callable[[], object]) -> bool:
    hasher = make_hasher()
    return hasher.verify("hunter2", hasher.hash("hunter2"))


def identical_hash_for_same_password(make_hasher: Callable[[], object]) -> bool:
    """True == hashing the same password twice collides (no salt -- the bug)."""
    hasher = make_hasher()
    return hasher.hash("hunter2") == hasher.hash("hunter2")


def run_self_test() -> int:
    failures = 0
    if not verifies_correct_password(ScryptHasher):
        failures += 1
        print("FAIL: oracle failed to verify the correct password", file=sys.stderr)
    if identical_hash_for_same_password(ScryptHasher):
        failures += 1
        print("FAIL: oracle produced identical hashes (no salt)", file=sys.stderr)
    if not identical_hash_for_same_password(WeakHasher):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: unsalted hasher collision was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (salted scrypt differs each time; unsalted md5 collides -- caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Password-hashing harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
