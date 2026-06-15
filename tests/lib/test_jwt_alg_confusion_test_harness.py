from harnesses.lib import jwt_alg_confusion_test_harness as h


def test_self_test_passes() -> None:
    assert h.run_self_test() == 0


def test_strict_verifier_accepts_genuine_rs256() -> None:
    private_key, public_pem = h.keypair()
    token = h.mint_rs256(private_key)
    claims = h.StrictVerifier(public_pem).verify(token)
    assert claims["sub"] == "alice"


def test_strict_verifier_rejects_both_forgeries() -> None:
    _, public_pem = h.keypair()
    oracle = h.StrictVerifier(public_pem)
    assert h.accepts_token(oracle, h.forge_alg_none()) is False
    assert h.accepts_token(oracle, h.forge_hs256_with_public_key(public_pem)) is False


def test_pyjwt_floor_rejects_public_key_as_hmac() -> None:
    # The pyjwt[crypto]>=2.13 floor (CVE-2026-48526): a PEM public key may not be used
    # as an HMAC secret, so the confusion is rejected even if HS256 is wrongly allowed.
    _, public_pem = h.keypair()
    forged = h.forge_hs256_with_public_key(public_pem)
    assert h.pyjwt_floor_rejects_confusion(forged, public_pem) is True
