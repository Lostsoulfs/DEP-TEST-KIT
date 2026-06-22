#!/usr/bin/env python3
"""Password-reset token-design harness (cryptography): unforgeable, expiring, single-use.

OWASP Top 10:2025 A06 Insecure Design. Current guidance: reset tokens must be
cryptographically random, HMAC-signed with a timing-safe compare, short-lived, and single-use;
encrypted user-IDs or MD5(email) tokens are predictable and forgeable.

WHY: A reset flow that derives the token from public input -- md5(email + counter) -- looks
fine in a functional test (issue then verify round-trips), but an attacker who knows the
scheme recomputes a victim's token and takes the account. The defect is in the DESIGN, not a
single call, so only a forgeability probe exposes it.

HOW: `SignedTokenDesign` is the ORACLE -- payload binds email + purpose + expiry + a random
nonce, signed with a server-secret HMAC (cryptography), verified timing-safe and consumed
once. `PredictableTokenDesign` is the planted defect -- md5(email:counter), no expiry,
replayable. `token_forgeable` lets an attacker recompute the token from public knowledge only
(no server secret) and asks whether it verifies.

WHERE: lib/ -- dependency-backed (`cryptography` HMAC-SHA256 with constant-time verify) and
fully in-process.

Self-test:
    python harnesses/lib/reset_token_design_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import hashlib
import secrets
import sys
import time
from typing import Callable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, hmac

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["token_forgeable"]

DOSSIER = {
    "name": "reset_token_design",
    "path": "harnesses/lib/reset_token_design_test_harness.py",
    "flavor": "lib",
    "dependency": "cryptography",
    "standard": "OWASP Top 10:2025 A06 Insecure Design - password-reset token design",
    "failure_class": "Predictable/unsigned reset token an attacker can forge or replay",
    "oracle": "SignedTokenDesign - HMAC-signed, expiring, single-use, purpose-bound token",
    "buggy": "PredictableTokenDesign - md5(email:counter), no expiry, replayable",
    "planted_mutant": "attacker recomputes md5(email:1) and the token verifies",
    "proof_file": "tests/lib/test_reset_token_design_proof.py",
    "vacuity_targets": ["token_forgeable"],
    "commands": ["python harnesses/lib/reset_token_design_test_harness.py --self-test"],
    "known_limits": (
        "models forgeability/predictability; not delivery-channel or rate-limit controls"
    ),
    "related": ["agent_message_auth (HMAC)", "oauth_pkce", "secret_scanning"],
}


def _sign(secret: bytes, msg: bytes) -> str:
    mac = hmac.HMAC(secret, hashes.SHA256())
    mac.update(msg)
    return mac.finalize().hex()


def _verify(secret: bytes, msg: bytes, tag_hex: str) -> bool:
    mac = hmac.HMAC(secret, hashes.SHA256())
    mac.update(msg)
    try:
        mac.verify(bytes.fromhex(tag_hex))  # constant-time
        return True
    except (InvalidSignature, ValueError):
        return False


class SignedTokenDesign:
    """ORACLE: HMAC-signed, expiring, single-use, purpose-bound reset token."""

    def __init__(self) -> None:
        self._secret = secrets.token_bytes(32)
        self._used: set = set()

    def issue(self, email: str) -> str:
        payload = f"{email}|pwreset|{int(time.time()) + 1200}|{secrets.token_hex(8)}"
        return payload + "|" + _sign(self._secret, payload.encode())

    def verify(self, email: str, token: str) -> bool:
        try:
            payload, tag = token.rsplit("|", 1)
        except ValueError:
            return False
        if not _verify(self._secret, payload.encode(), tag):
            return False
        try:
            who, purpose, exp, nonce = payload.split("|")
        except ValueError:
            return False
        if who != email or purpose != "pwreset" or int(exp) < int(time.time()):
            return False
        if nonce in self._used:
            return False  # single-use
        self._used.add(nonce)
        return True

    @staticmethod
    def forge(email: str) -> str:
        payload = f"{email}|pwreset|{int(time.time()) + 1200}|{secrets.token_hex(8)}"
        return payload + "|" + hashlib.sha256(payload.encode()).hexdigest()  # no server secret


class PredictableTokenDesign:
    """BUGGY: md5(email:counter), no expiry, replayable."""

    def __init__(self) -> None:
        self._counter = 0

    def issue(self, email: str) -> str:
        self._counter += 1
        return hashlib.md5(f"{email}:{self._counter}".encode()).hexdigest()

    def verify(self, email: str, token: str) -> bool:
        return any(
            token == hashlib.md5(f"{email}:{c}".encode()).hexdigest() for c in range(1, 1001)
        )

    @staticmethod
    def forge(email: str) -> str:
        return hashlib.md5(f"{email}:1".encode()).hexdigest()  # guess counter=1


def legit_token_verifies(make_design: Callable[[], object]) -> bool:
    """True == a freshly issued token verifies for its owner (no false positive)."""
    design = make_design()
    token = design.issue("user@example.com")
    return design.verify("user@example.com", token)


def token_forgeable(make_design: Callable[[], object]) -> bool:
    """True == an attacker forges a valid token from public knowledge (the bug)."""
    design = make_design()
    design.issue("victim@example.com")
    forged = type(design).forge("victim@example.com")
    return design.verify("victim@example.com", forged)


def run_self_test() -> int:
    failures = 0
    if not legit_token_verifies(SignedTokenDesign):
        failures += 1
        print("FAIL: oracle rejected a legitimately issued token", file=sys.stderr)
    if token_forgeable(SignedTokenDesign):
        failures += 1
        print("FAIL: oracle accepted a forged token", file=sys.stderr)
    if not token_forgeable(PredictableTokenDesign):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: predictable token design was NOT caught being forgeable", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (signed token resists forgery; md5(email:counter) token forged)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Password-reset token-design harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
