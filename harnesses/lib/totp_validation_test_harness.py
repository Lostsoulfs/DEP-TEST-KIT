#!/usr/bin/env python3
"""TOTP / MFA verification harness (cryptography): RFC-6238 codes, replay-protected.

OWASP Top 10:2025 A07 Identification and Authentication Failures (MFA bypass).

WHY: A second factor that accepts a static code, or accepts ANY code, is no factor. A correct
TOTP verifier recomputes the HMAC-based one-time code for the current time step, compares in
constant time, and refuses a step that was already used (replay).

HOW: `TotpVerifier` is the ORACLE -- HMAC-SHA1 over the time step (RFC 6238), constant-time
compare, single-use per step. `StaticOtpVerifier` is the planted defect -- it accepts anything.
`accepts_wrong_code` submits a code that is NOT the current one and reports acceptance.

WHERE: lib/ -- dependency-backed (`cryptography` HMAC), in-process.

Self-test:
    python harnesses/lib/totp_validation_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import hmac as _stdhmac
import secrets
import struct
import sys
from typing import Callable

from cryptography.hazmat.primitives import hashes, hmac

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["accepts_wrong_code"]

DOSSIER = {
    "name": "totp_validation",
    "path": "harnesses/lib/totp_validation_test_harness.py",
    "flavor": "lib",
    "dependency": "cryptography",
    "standard": "OWASP Top 10:2025 A07 Authentication Failures - TOTP/MFA (RFC 6238)",
    "failure_class": "An MFA verifier that accepts a wrong/static code or replays a used step",
    "oracle": "TotpVerifier.verify - RFC-6238 HMAC code, constant-time, single-use step",
    "buggy": "StaticOtpVerifier.verify - accept any code",
    "planted_mutant": "submit a code that is not the current TOTP; the static verifier accepts",
    "proof_file": "tests/lib/test_totp_validation_proof.py",
    "vacuity_targets": ["accepts_wrong_code"],
    "commands": ["python harnesses/lib/totp_validation_test_harness.py --self-test"],
    "known_limits": "code correctness + single-step replay; not rate-limiting or drift tuning",
    "related": ["webhook_signature", "csrf_token", "jwt_audience_binding"],
}


def _totp(secret: bytes, step: int) -> str:
    mac = hmac.HMAC(secret, hashes.SHA1())
    mac.update(struct.pack(">Q", step))
    digest = mac.finalize()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return f"{code % 1000000:06d}"


class TotpVerifier:
    """ORACLE: RFC-6238 HMAC code, constant-time compare, single-use per step."""

    def __init__(self) -> None:
        self._secret = secrets.token_bytes(20)
        self._used: set = set()

    def current(self, now: int) -> str:
        return _totp(self._secret, now // 30)

    def verify(self, code: str, now: int) -> bool:
        step = now // 30
        if step in self._used:
            return False
        if _stdhmac.compare_digest(_totp(self._secret, step), code):
            self._used.add(step)
            return True
        return False


class StaticOtpVerifier:
    """BUGGY: accept any code."""

    def current(self, now: int) -> str:
        return "000000"

    def verify(self, code: str, now: int) -> bool:
        return True  # BUG: no actual verification


def accepts_correct_code(make_verifier: Callable[[], object]) -> bool:
    verifier = make_verifier()
    return verifier.verify(verifier.current(1000), 1000)


def accepts_wrong_code(make_verifier: Callable[[], object]) -> bool:
    """True == a code that is NOT the current TOTP was accepted (the bug)."""
    verifier = make_verifier()
    correct = verifier.current(1000)
    wrong = "000000" if correct != "000000" else "111111"
    return verifier.verify(wrong, 1000)


def run_self_test() -> int:
    failures = 0
    if not accepts_correct_code(TotpVerifier):
        failures += 1
        print("FAIL: oracle rejected the correct TOTP code", file=sys.stderr)
    if accepts_wrong_code(TotpVerifier):
        failures += 1
        print("FAIL: oracle accepted a wrong TOTP code", file=sys.stderr)
    if not accepts_wrong_code(StaticOtpVerifier):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: static OTP verifier accepting any code was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (TOTP verifier rejects the wrong code; static verifier accepts -- caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="TOTP/MFA verification harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
