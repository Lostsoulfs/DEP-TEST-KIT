#!/usr/bin/env python3
"""Authenticated-encryption correctness test harness (cryptography).

WHY: A happy-path "encrypt then decrypt, assert equal" example test passes just
as well for an UNAUTHENTICATED cipher (AES-CTR/CBC) as for an authenticated
one (AES-GCM). The difference only shows when an attacker TAMPERS with the
ciphertext: authenticated encryption rejects it (InvalidTag); unauthenticated
encryption silently returns attacker-influenced plaintext. That is the real,
high-severity failure class (CWE-327/CWE-353) a fixed round-trip example can
never surface.

HOW: `AeadBox` is the ORACLE — AES-128-GCM via `cryptography`, fresh 12-byte
nonce per message; `decrypt` raises on any tampering. `BuggyBox` is the
planted defect — the SAME interface implemented with unauthenticated AES-CTR,
so a flipped ciphertext byte decrypts to silent garbage with no error. The
harness proves a tampered ciphertext is ACCEPTED by the buggy box and
REJECTED by the oracle; a mock/example test catches neither.

WHERE: lib/ — dependency-backed (`cryptography`) but fully in-process, no service.
Adds `cryptography` to the `lib` extra in pyproject.toml.

Self-test:
    python harnesses/lib/crypto_correctness_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Tuple

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# --- ORACLE: authenticated encryption (AES-GCM) ---------------------------------
class AeadBox:
    """Correct AEAD: integrity-protected; decrypt() raises on tamper."""

    def __init__(self, key: bytes | None = None) -> None:
        # `is None`, not `or`: an explicit empty b"" key must be honored, not replaced.
        self.key = AESGCM.generate_key(bit_length=128) if key is None else key

    def encrypt(self, plaintext: bytes) -> Tuple[bytes, bytes]:
        nonce = os.urandom(12)
        ct = AESGCM(self.key).encrypt(nonce, plaintext, None)
        return nonce, ct

    def decrypt(self, nonce: bytes, ct: bytes) -> bytes:
        return AESGCM(self.key).decrypt(nonce, ct, None)  # raises InvalidTag on tamper


# --- BUGGY: unauthenticated encryption (AES-CTR) — no integrity ------------------
class BuggyBox:
    """Plausible-but-wrong: confidentiality without integrity. Same interface."""

    def __init__(self, key: bytes | None = None) -> None:
        # `is None`, not `or`: an explicit empty b"" key must be honored, not replaced.
        self.key = os.urandom(16) if key is None else key

    def encrypt(self, plaintext: bytes) -> Tuple[bytes, bytes]:
        nonce = os.urandom(16)
        enc = Cipher(algorithms.AES(self.key), modes.CTR(nonce)).encryptor()
        return nonce, enc.update(plaintext) + enc.finalize()

    def decrypt(self, nonce: bytes, ct: bytes) -> bytes:
        dec = Cipher(algorithms.AES(self.key), modes.CTR(nonce)).decryptor()
        return dec.update(ct) + dec.finalize()  # never raises: tamper goes undetected


def roundtrips(box) -> bool:
    """True if encrypt->decrypt is the identity for an untampered message."""
    msg = b"transfer $100 to alice"
    nonce, ct = box.encrypt(msg)
    try:
        return box.decrypt(nonce, ct) == msg
    except Exception:
        return False


def accepts_tampered_ciphertext(box) -> bool:
    """Flip one ciphertext byte and try to decrypt. True == the box accepted the
    forgery (the bug); False == it rejected the tamper (authenticated)."""
    nonce, ct = box.encrypt(b"transfer $100 to alice")
    tampered = bytes([ct[0] ^ 0x01]) + ct[1:]
    try:
        box.decrypt(nonce, tampered)
        return True   # decrypted a forged ciphertext without error -> vulnerable
    except Exception:
        return False  # InvalidTag (or similar) -> integrity enforced


def run_self_test() -> int:
    failures = 0
    if not roundtrips(AeadBox()):
        failures += 1
        print("FAIL: oracle AEAD does not round-trip", file=sys.stderr)
    if accepts_tampered_ciphertext(AeadBox()):
        failures += 1
        print("FAIL: oracle AEAD accepted a tampered ciphertext", file=sys.stderr)
    if not accepts_tampered_ciphertext(BuggyBox()):
        failures += 1  # the planted bug must be caught — else vacuous green
        print("FAIL: buggy unauthenticated box was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (AEAD rejects tamper; unauthenticated box caught accepting a forgery)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Authenticated-encryption correctness harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
