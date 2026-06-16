#!/usr/bin/env python3
"""JWT algorithm-confusion rejection test harness (PyJWT + cryptography).

WHY:   The keycloak_oidc harness proves a verifier must check the signature at all
       (CWE-347). It does NOT prove the subtler, deadlier failure: algorithm
       confusion. A service issues RS256 (asymmetric) tokens, so its RSA *public* key
       is, by design, public. If a verifier trusts the token's own ``alg`` header and
       uses that one key polymorphically, an attacker signs a token with **HS256 using
       the public key as the HMAC secret** — and a "valid signature" check passes
       (CWE-347 / CVE-2026-48526). The ``alg=none`` unsigned token is the same family.
       This is the harness the repo's ``pyjwt[crypto]>=2.13`` floor exists for, and
       until now nothing proved the floor actually rejects the forgery.

HOW:   Generate a real RSA keypair (cryptography). Mint a valid RS256 token, then forge
       two attack tokens an attacker can build: (1) ``alg=none`` with an empty
       signature; (2) HS256 signed with the RSA *public* PEM as the HMAC key. The ORACLE
       ``StrictVerifier`` pins ``algorithms=["RS256"]`` via PyJWT and rejects both. The
       BUGGY ``ConfusedVerifier`` is the classic confused deputy: it reads the token's
       own ``alg`` and dispatches — HMAC-with-the-public-key for HS256, skip for none —
       so it ACCEPTS the forgeries. ``pyjwt_floor_rejects_confusion`` additionally pins
       the dependency floor: even a verifier that wrongly *allows* HS256 is saved by
       PyJWT >=2.13 refusing an asymmetric PEM as an HMAC secret.

WHERE: lib/ — dependency-backed (PyJWT + cryptography), fully in-process, no Docker. The
       keypair, tokens, and forgeries are all crafted here. Adds ``pyjwt[crypto]>=2.13``
       to the ``lib`` extra (it was integration-only).

Self-test:
  python harnesses/lib/jwt_alg_confusion_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import sys

import jwt  # PyJWT — the harness's declared dependency
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.exceptions import InvalidAlgorithmError, InvalidKeyError, InvalidSignatureError

ISSUER = "https://issuer.example"
AUDIENCE = "dep-test-kit"
CLAIMS = {"sub": "alice", "scope": "user", "iss": ISSUER, "aud": AUDIENCE}

# Symbols the vacuous-green meta-gate (Phase A) neuters to confirm this harness has teeth.
VACUITY_TARGETS = ["StrictVerifier.verify"]


# --- token + key crafting -------------------------------------------------------
def _b64u(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64u_json(obj: object) -> str:
    return _b64u(json.dumps(obj, separators=(",", ":")).encode())


def _b64u_decode(seg: str) -> bytes:
    return base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4))


def keypair() -> tuple[rsa.RSAPrivateKey, bytes]:
    """A real RSA keypair; the public key returned as PEM bytes (it is public by design)."""
    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_pem = priv.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return priv, public_pem


def mint_rs256(private_key: rsa.RSAPrivateKey) -> str:
    """A legitimately signed RS256 token."""
    return jwt.encode(CLAIMS, private_key, algorithm="RS256")


def forge_alg_none(claims: dict | None = None) -> str:
    """Attack token: ``alg=none`` with an empty signature (no key needed)."""
    claims = CLAIMS if claims is None else claims
    header = {"alg": "none", "typ": "JWT"}
    return f"{_b64u_json(header)}.{_b64u_json(claims)}."


def forge_hs256_with_public_key(public_pem: bytes, claims: dict | None = None) -> str:
    """Attack token: HS256 signed with the RSA *public* PEM as the HMAC secret. Built by
    hand (an attacker is not bound by PyJWT's asymmetric-key-as-HMAC guard)."""
    claims = CLAIMS if claims is None else claims
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = f"{_b64u_json(header)}.{_b64u_json(claims)}"
    sig = hmac.new(public_pem, signing_input.encode(), hashlib.sha256).digest()
    return f"{signing_input}.{_b64u(sig)}"


def _unverified_claims(token: str) -> dict:
    return json.loads(_b64u_decode(token.split(".")[1]))


# --- ORACLE: pins the algorithm; PyJWT rejects every forgery --------------------
class StrictVerifier:
    """The correct verifier: ``algorithms=["RS256"]`` only, validated by PyJWT."""

    def __init__(self, public_pem: bytes, issuer: str = ISSUER, audience: str = AUDIENCE) -> None:
        self.public_pem = public_pem
        self.issuer = issuer
        self.audience = audience

    def verify(self, token: str) -> dict:
        return jwt.decode(
            token,
            self.public_pem,
            algorithms=["RS256"],
            audience=self.audience,
            issuer=self.issuer,
        )


# --- BUGGY: trusts the token's own alg header (the confused deputy) --------------
class ConfusedVerifier(StrictVerifier):
    """Reads the token's ``alg`` and uses the one public key polymorphically: HMAC for
    HS256, skip for ``none``. This is the algorithm-confusion vulnerability itself."""

    def verify(self, token: str) -> dict:
        alg = jwt.get_unverified_header(token).get("alg")
        if alg == "none":
            return _unverified_claims(token)  # trusts an unsigned token
        if alg == "HS256":
            signing_input, _, sig = token.rpartition(".")
            expected = _b64u(hmac.new(self.public_pem, signing_input.encode(), hashlib.sha256).digest())
            if not hmac.compare_digest(expected, sig):
                raise InvalidSignatureError("bad HS256 signature")
            return _unverified_claims(token)  # public key used as HMAC secret — forged
        return super().verify(token)


def accepts_token(verifier: StrictVerifier, token: str) -> bool:
    """True == the verifier accepted the token (no exception raised)."""
    try:
        verifier.verify(token)
        return True
    except Exception:
        return False


def pyjwt_floor_rejects_confusion(forged_hs256: str, public_pem: bytes) -> bool:
    """Pin the dependency floor: even a verifier that wrongly ALLOWS HS256 must reject an
    HS256 token verified with an RSA public PEM. PyJWT >=2.13 (CVE-2026-48526) refuses an
    asymmetric key as an HMAC secret. Returns True if PyJWT rejects (raises)."""
    try:
        jwt.decode(
            forged_hs256,
            public_pem,
            algorithms=["RS256", "HS256"],
            audience=AUDIENCE,
            issuer=ISSUER,
        )
        return False  # PyJWT accepted the confusion — the floor is not protecting us
    except (InvalidKeyError, InvalidAlgorithmError, InvalidSignatureError):
        # Assert the INTENDED rejection cause (asymmetric PEM refused as an HMAC secret),
        # not just any error — an unexpected exception propagates and fails loud instead of
        # masking a regression of the confusion protection.
        return True


def run_self_test() -> int:
    failures = 0
    private_key, public_pem = keypair()
    valid = mint_rs256(private_key)
    none_token = forge_alg_none()
    hs256_forged = forge_hs256_with_public_key(public_pem)

    oracle = StrictVerifier(public_pem)
    buggy = ConfusedVerifier(public_pem)

    # ORACLE: accepts the genuine token, rejects both forgeries.
    if not accepts_token(oracle, valid):
        failures += 1
        print("FAIL: strict verifier rejected a genuine RS256 token", file=sys.stderr)
    # ...and returns the GENUINE claims, not merely "does not raise" — asserting the produced
    # artifact (not just accept/reject) is what gives the oracle real teeth, so the vacuity gate's
    # type-faithful mutation of verify()'s return is caught by an assertion (ADR-0007 D1).
    try:
        claims = oracle.verify(valid)
    except Exception:
        claims = {}
    if claims.get("sub") != CLAIMS["sub"] or claims.get("scope") != CLAIMS["scope"]:
        failures += 1
        print("FAIL: strict verifier did not return the genuine claims", file=sys.stderr)
    if accepts_token(oracle, none_token):
        failures += 1
        print("FAIL: strict verifier accepted an alg=none token", file=sys.stderr)
    if accepts_token(oracle, hs256_forged):
        failures += 1
        print("FAIL: strict verifier accepted an HS256-with-public-key forgery", file=sys.stderr)

    # BUGGY: must accept the forgeries, else the harness has no teeth.
    if not accepts_token(buggy, hs256_forged):
        failures += 1
        print("FAIL: confused verifier did NOT accept the forgery — vacuous green", file=sys.stderr)
    if not accepts_token(buggy, none_token):
        failures += 1
        print("FAIL: confused verifier did NOT accept the alg=none token", file=sys.stderr)

    # FLOOR: PyJWT >=2.13 rejects public-key-as-HMAC even when HS256 is allowed.
    if not pyjwt_floor_rejects_confusion(hs256_forged, public_pem):
        failures += 1
        print("FAIL: PyJWT accepted public-key-as-HMAC (CVE-2026-48526 floor breached)", file=sys.stderr)

    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (strict rejects alg=none + HS256-confusion; confused deputy accepts both)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="JWT algorithm-confusion rejection harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
