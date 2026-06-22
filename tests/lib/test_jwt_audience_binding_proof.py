"""Proof: enforcing the aud claim stops the confused-deputy token reuse the no-audience
verifier allows. A service-A token is accepted by the no-aud verifier at service B, rejected
by the audience-binding verifier."""

from harnesses.lib import jwt_audience_binding_test_harness as h


def test_proof_no_audience_accepts_wrong_aud() -> None:
    assert h.accepts_wrong_audience(h.NoAudienceVerifier) is True


def test_proof_binding_verifier_rejects_wrong_aud() -> None:
    assert h.accepts_wrong_audience(h.AudienceBindingVerifier) is False


def test_proof_binding_verifier_accepts_correct_aud() -> None:
    assert h.accepts_correct_audience(h.AudienceBindingVerifier) is True


# --- scenario coverage: the no-audience verifier accepts a token for another service ---
def test_proof_no_audience_verifier_accepts_foreign_token() -> None:
    claims = h.NoAudienceVerifier("service-B").verify(h._token("service-A"))
    assert claims["sub"] == "u1"
