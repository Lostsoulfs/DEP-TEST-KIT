"""Proof: the naive substring scanner is blind to the planted AWS key / high-entropy
token / private key; detect-secrets catches them."""

from harnesses.lib import secret_scanning_test_harness as h


def test_proof_naive_scanner_misses() -> None:
    assert h.misses_real_secrets(h.naive_secret_count) is True


def test_proof_detect_secrets_catches() -> None:
    assert h.misses_real_secrets(h.detect_secrets_count) is False
