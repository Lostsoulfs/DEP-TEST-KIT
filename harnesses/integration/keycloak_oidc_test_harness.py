#!/usr/bin/env python3
"""Keycloak OIDC token-verification integration test harness (testcontainers + PyJWT).

WHY: Token validation is the most-mocked boundary in a service — "assume the
token is valid." A verifier that skips signature/issuer/audience/expiry checks
accepts a FORGED token and every mock-backed test still passes. Only a real
OIDC provider (real JWKS, real RS256 tokens) proves the difference between
verifying and merely decoding (CWE-347 improper signature verification).

HOW: `TokenVerifier.verify` fetches the provider's JWKS and validates the
signature, issuer, audience, and expiry with PyJWT. `BuggyTokenVerifier.verify`
calls `jwt.decode(..., options={"verify_signature": False})` and trusts whatever
the token claims. `accepts_token` turns "did it accept?" into a boolean: the
proof feeds a real valid token (both accept) and a forged/tampered token (only
the buggy verifier accepts).

WHERE: integration/ — needs a real ephemeral Keycloak (Docker). The realm,
client, a real signed token, and a forged token are provisioned by
`tests/integration/conftest.py` (`keycloak_oidc`); the harness's own
dependency is `PyJWT`. Adds `pyjwt` to the integration extra.

Self-test:
    python harnesses/integration/keycloak_oidc_test_harness.py --self-test
    (deferred: the real proof runs under `pytest -m integration`, which needs Docker)
"""

from __future__ import annotations

import argparse
import shutil
import sys

import jwt                       # PyJWT — the harness's declared dependency
from jwt import PyJWKClient


class TokenVerifier:
    """ORACLE: full RS256 verification against the provider's JWKS."""

    def __init__(self, jwks_url: str, issuer: str, audience: str) -> None:
        self.jwks_url = jwks_url
        self.issuer = issuer
        self.audience = audience

    def verify(self, token: str) -> dict:
        signing_key = PyJWKClient(self.jwks_url).get_signing_key_from_jwt(token).key
        return jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=self.audience,
            issuer=self.issuer,
        )


class BuggyTokenVerifier(TokenVerifier):
    """BUGGY: decodes without verifying the signature — trusts forged tokens."""

    def verify(self, token: str) -> dict:
        return jwt.decode(token, options={"verify_signature": False})  # BUG


def accepts_token(verifier: TokenVerifier, token: str) -> bool:
    """True == the verifier accepted the token (no exception)."""
    try:
        verifier.verify(token)
        return True
    except Exception:
        return False


def run_self_test() -> int:
    print(
        "self-test: DEFERRED -- integration harness. "
        "Run `pytest -m integration` (needs Docker). "
        f"docker on PATH: {shutil.which('docker') is not None}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Keycloak OIDC verification integration harness")
    parser.add_argument("--self-test", action="store_true")
    parser.parse_args(argv)
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
