"""Proof: the SRI verifier refuses the tampered bytes the naive loader runs.
A sha384 mismatch raises vs the bytes being returned unchecked."""

from harnesses.lib import subresource_integrity_test_harness as h


def test_proof_buggy_is_flagged() -> None:
    assert h.loads_tampered_resource(h.NoIntegrityLoader) is True


def test_proof_oracle_not_flagged() -> None:
    assert h.loads_tampered_resource(h.SriVerifier) is False


def test_proof_oracle_happy_path() -> None:
    assert h.loads_intact_resource(h.SriVerifier) is True
