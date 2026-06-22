#!/usr/bin/env python3
"""JWT audience-binding (confused-deputy) harness (PyJWT).

OWASP Top 10:2025 A07 Authentication Failures. A 2026-relevant token-reuse / confused-deputy
class, sharpened by multi-service agent/MCP architectures where one token is presented to
many resource servers.

WHY: A JWT minted for service A (`aud: "service-A"`) must NOT be accepted by service B. If
B's verifier checks the signature and expiry but not the audience, an attacker (or a
compromised upstream service) replays A's token at B and is treated as authenticated -- the
confused-deputy problem. A test that verifies a correctly-audienced token passes whether or
not `aud` is enforced; only a wrong-audience token exposes the gap.

HOW: `AudienceBindingVerifier` is the ORACLE -- `jwt.decode(..., audience=expected)`, which
raises `InvalidAudienceError` when the token's `aud` differs. `NoAudienceVerifier` is the
planted defect -- it decodes with `options={"verify_aud": False}`. `accepts_wrong_audience`
presents a token minted for `service-A` to a `service-B` verifier: the oracle rejects, the
no-audience verifier accepts.

WHERE: lib/ -- in-process, deterministic. Adds `pyjwt` to the matching extra (imported directly
by the harness, so NOT a deptry per-rule ignore).

Self-test:
    python harnesses/lib/jwt_audience_binding_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

import jwt

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["accepts_wrong_audience"]

DOSSIER = {
    "name": "jwt_audience_binding",
    "path": "harnesses/lib/jwt_audience_binding_test_harness.py",
    "flavor": "lib",
    "dependency": "pyjwt",
    "standard": "OWASP Top 10:2025 A07 — token reuse / confused deputy across services",
    "failure_class": "A token minted for service A accepted by service B (audience not enforced)",
    "oracle": (
        "AudienceBindingVerifier.verify — jwt.decode(audience=expected) raises on aud mismatch"
    ),
    "buggy": "NoAudienceVerifier.verify — decode with options verify_aud=False",
    "planted_mutant": "present an aud='service-A' token to a service-B verifier; oracle rejects",
    "proof_file": "tests/lib/test_jwt_audience_binding_proof.py",
    "vacuity_targets": ["accepts_wrong_audience"],
    "commands": ["python harnesses/lib/jwt_audience_binding_test_harness.py --self-test"],
    "known_limits": "checks the aud claim; full token hygiene also needs iss/azp/exp/nbf review",
    "related": ["keycloak_oidc", "oauth_pkce", "jwt_alg_confusion"],
}

_SECRET = "shared-signing-key-for-the-harness"  # allowlist secret: fixed HMAC for the deterministic test tokens, not a real credential
_FAR_FUTURE = 9_999_999_999  # exp well beyond any test clock


def _token(audience: str) -> str:
    return jwt.encode({"sub": "u1", "aud": audience, "exp": _FAR_FUTURE}, _SECRET, algorithm="HS256")


class AudienceBindingVerifier:
    """ORACLE: bind the token to this resource server's audience."""

    def __init__(self, expected_audience: str) -> None:
        self.expected_audience = expected_audience

    def verify(self, token: str) -> dict:
        return jwt.decode(token, _SECRET, algorithms=["HS256"], audience=self.expected_audience)


class NoAudienceVerifier:
    """BUGGY: verify signature/expiry but skip the audience check."""

    def __init__(self, expected_audience: str) -> None:
        self.expected_audience = expected_audience

    def verify(self, token: str) -> dict:
        # BUG
        return jwt.decode(token, _SECRET, algorithms=["HS256"], options={"verify_aud": False})


def accepts_correct_audience(make_verifier: Callable[[str], object]) -> bool:
    try:
        return make_verifier("service-B").verify(_token("service-B"))["sub"] == "u1"
    except Exception:
        return False


def accepts_wrong_audience(make_verifier: Callable[[str], object]) -> bool:
    """A service-A token presented to a service-B verifier. True == accepted (the bug);
    False == rejected on the audience check."""
    try:
        make_verifier("service-B").verify(_token("service-A"))
        return True   # accepted a token meant for another service -> confused deputy
    except Exception:
        return False  # audience binding rejected it


def run_self_test() -> int:
    failures = 0
    if not accepts_correct_audience(AudienceBindingVerifier):
        failures += 1
        print("FAIL: oracle rejected a token with the correct audience", file=sys.stderr)
    if accepts_wrong_audience(AudienceBindingVerifier):
        failures += 1
        print("FAIL: oracle accepted a token for the wrong audience", file=sys.stderr)
    if not accepts_wrong_audience(NoAudienceVerifier):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print(
            "FAIL: no-audience verifier was NOT caught accepting a wrong-audience token",
            file=sys.stderr,
        )
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print(
        "self-test: OK (audience-binding verifier rejects a wrong-aud token; no-aud verifier "
        "caught)"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="JWT audience-binding (confused-deputy) harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
