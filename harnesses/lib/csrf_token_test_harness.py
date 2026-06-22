#!/usr/bin/env python3
"""CSRF synchronizer-token harness (cryptography): session-bound, unforgeable CSRF tokens.

OWASP Top 10:2025 A01 Broken Access Control (Cross-Site Request Forgery).

WHY: A CSRF defense that issues a STATIC or non-session-bound token is no defense: every user
gets the same token, so an attacker reads their own and replays it in a forged cross-site
request against a victim. The token must be bound to the victim's session and verified with a
server secret the attacker never sees.

HOW: `SynchronizerCsrf` is the ORACLE -- the token is HMAC(secret, session_id), compared in
constant time, so a token minted for the attacker's session does not validate against the
victim's. `StaticCsrf` is the planted defect -- one global token for everyone.
`accepts_cross_session_token` mints a token for the attacker session and submits it against
the victim session: the oracle rejects, the static scheme accepts.

WHERE: lib/ -- dependency-backed (`cryptography` HMAC-SHA256 + constant-time verify), in-process.

Self-test:
    python harnesses/lib/csrf_token_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import secrets
import sys
from typing import Callable

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, hmac

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["accepts_cross_session_token"]

DOSSIER = {
    "name": "csrf_token",
    "path": "harnesses/lib/csrf_token_test_harness.py",
    "flavor": "lib",
    "dependency": "cryptography",
    "standard": "OWASP Top 10:2025 A01 Broken Access Control (CSRF)",
    "failure_class": "A non-session-bound (static) CSRF token an attacker can replay cross-session",
    "oracle": "SynchronizerCsrf - token = HMAC(secret, session_id), constant-time verify",
    "buggy": "StaticCsrf - one global token for every session",
    "planted_mutant": "mint a token for the attacker session; submit it against the victim session",
    "proof_file": "tests/lib/test_csrf_token_proof.py",
    "vacuity_targets": ["accepts_cross_session_token"],
    "commands": ["python harnesses/lib/csrf_token_test_harness.py --self-test"],
    "known_limits": "synchronizer-token binding only; not double-submit-cookie or SameSite config",
    "related": ["reset_token_design", "oauth_pkce", "jwt_audience_binding"],
}


class SynchronizerCsrf:
    """ORACLE: HMAC(secret, session_id) token, constant-time verified."""

    def __init__(self) -> None:
        self._secret = secrets.token_bytes(32)

    def issue(self, session_id: str) -> str:
        mac = hmac.HMAC(self._secret, hashes.SHA256())
        mac.update(session_id.encode())
        return mac.finalize().hex()

    def validate(self, session_id: str, token: str) -> bool:
        mac = hmac.HMAC(self._secret, hashes.SHA256())
        mac.update(session_id.encode())
        try:
            mac.verify(bytes.fromhex(token))
            return True
        except (InvalidSignature, ValueError):
            return False


class StaticCsrf:
    """BUGGY: one global token, not bound to the session."""

    _TOKEN = "csrf-token-v1"

    def issue(self, session_id: str) -> str:
        return self._TOKEN

    def validate(self, session_id: str, token: str) -> bool:
        return token == self._TOKEN  # BUG: the same token validates for ANY session


def legit_token_validates(make_csrf: Callable[[], object]) -> bool:
    csrf = make_csrf()
    token = csrf.issue("session-victim")
    return csrf.validate("session-victim", token)


def accepts_cross_session_token(make_csrf: Callable[[], object]) -> bool:
    """True == a token minted for the attacker session validates the victim session (CSRF)."""
    csrf = make_csrf()
    attacker_token = csrf.issue("session-attacker")
    return csrf.validate("session-victim", attacker_token)


def run_self_test() -> int:
    failures = 0
    if not legit_token_validates(SynchronizerCsrf):
        failures += 1
        print("FAIL: oracle rejected a legitimate session token", file=sys.stderr)
    if accepts_cross_session_token(SynchronizerCsrf):
        failures += 1
        print("FAIL: oracle accepted a cross-session token", file=sys.stderr)
    if not accepts_cross_session_token(StaticCsrf):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: static CSRF cross-session replay was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (session-bound token resists cross-session replay; static token caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="CSRF synchronizer-token harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
