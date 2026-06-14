"""Proof: the off-by-one expiry is caught exactly at the boundary; the oracle holds."""

import datetime as dt

import time_machine

from harnesses.lib import temporal_logic_test_harness as h


def test_proof_buggy_expiry_is_caught_at_boundary() -> None:
    # The buggy `<=` check is NOT detected as expiring correctly at the instant.
    assert h.expires_at_boundary(h.is_valid_buggy) is False


def test_proof_oracle_expiry_is_correct_at_boundary() -> None:
    assert h.expires_at_boundary(h.is_valid_oracle) is True


def test_proof_disagreement_is_only_at_the_instant() -> None:
    # At the exact expiry instant the two impls disagree — that is the whole bug.
    with time_machine.travel(h.EXPIRY, tick=False):
        assert h.is_valid_oracle(h.EXPIRY) is False
        assert h.is_valid_buggy(h.EXPIRY) is True
    # One microsecond later they agree again: both expired.
    with time_machine.travel(h.EXPIRY + dt.timedelta(microseconds=1), tick=False):
        assert h.is_valid_oracle(h.EXPIRY) is False
        assert h.is_valid_buggy(h.EXPIRY) is False
