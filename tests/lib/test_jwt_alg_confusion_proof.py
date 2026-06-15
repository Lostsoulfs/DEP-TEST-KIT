"""Proof: the harness has teeth — the confused deputy is caught and the strict verifier clears."""

from harnesses.lib import jwt_alg_confusion_test_harness as h


def test_proof_confused_verifier_accepts_hs256_forgery() -> None:
    # The planted vulnerability: an HS256 token signed with the RSA public key is accepted.
    _, public_pem = h.keypair()
    buggy = h.ConfusedVerifier(public_pem)
    assert h.accepts_token(buggy, h.forge_hs256_with_public_key(public_pem)) is True


def test_proof_confused_verifier_accepts_alg_none() -> None:
    _, public_pem = h.keypair()
    buggy = h.ConfusedVerifier(public_pem)
    assert h.accepts_token(buggy, h.forge_alg_none()) is True


def test_proof_strict_verifier_rejects_what_confused_accepts() -> None:
    _, public_pem = h.keypair()
    forged = h.forge_hs256_with_public_key(public_pem)
    assert h.accepts_token(h.ConfusedVerifier(public_pem), forged) is True
    assert h.accepts_token(h.StrictVerifier(public_pem), forged) is False
