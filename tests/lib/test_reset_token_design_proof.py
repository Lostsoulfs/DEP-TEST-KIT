"""Proof: the HMAC-signed token resists the forgery the md5(email:counter) design accepts.
The attacker recomputes the predictable token; the signed token rejects the wrong MAC."""

from harnesses.lib import reset_token_design_test_harness as h


def test_proof_buggy_is_flagged() -> None:
    assert h.token_forgeable(h.PredictableTokenDesign) is True


def test_proof_oracle_not_flagged() -> None:
    assert h.token_forgeable(h.SignedTokenDesign) is False


def test_proof_oracle_happy_path() -> None:
    assert h.legit_token_verifies(h.SignedTokenDesign) is True


# --- scenario coverage: the predictable design is replayable and unexpiring ---
def test_proof_buggy_allows_replay() -> None:
    design = h.PredictableTokenDesign()
    token = design.issue("u@example.com")
    assert design.verify("u@example.com", token) is True
    assert design.verify("u@example.com", token) is True


def test_proof_buggy_has_no_expiry_or_binding() -> None:
    import hashlib
    design = h.PredictableTokenDesign()
    guess = hashlib.md5(b"u@example.com:1").hexdigest()
    assert design.verify("u@example.com", guess) is True
