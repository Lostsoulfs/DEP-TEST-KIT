"""Proof: the RFC-6238 verifier rejects the wrong code the static verifier accepts.
A non-current code fails the constant-time HMAC compare vs being accepted unconditionally."""

from harnesses.lib import totp_validation_test_harness as h


def test_proof_buggy_is_flagged() -> None:
    assert h.accepts_wrong_code(h.StaticOtpVerifier) is True


def test_proof_oracle_not_flagged() -> None:
    assert h.accepts_wrong_code(h.TotpVerifier) is False


def test_proof_oracle_happy_path() -> None:
    assert h.accepts_correct_code(h.TotpVerifier) is True
