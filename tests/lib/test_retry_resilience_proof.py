"""Proof: the buggy retry-everything policy wastes attempts on a permanent error;
the oracle attempts it exactly once."""

from harnesses.lib import retry_resilience_test_harness as h


def test_proof_buggy_retries_permanent() -> None:
    assert h.retries_permanent(h.buggy_policy) is True


def test_proof_oracle_does_not_retry_permanent() -> None:
    assert h.retries_permanent(h.oracle_policy) is False


def test_proof_buggy_attempts_equal_cap() -> None:
    assert h.attempts_for_permanent(h.buggy_policy) == h.MAX_ATTEMPTS
