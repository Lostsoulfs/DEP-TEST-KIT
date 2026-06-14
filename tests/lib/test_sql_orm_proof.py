"""Proof: a real engine (even in-memory SQLite) exposes the missing-UNIQUE bug
that a mocked Session hides."""

from harnesses.lib import sql_orm_test_harness as h


def test_proof_buggy_allows_duplicate() -> None:
    assert h.allows_duplicate(unique=False) is True


def test_proof_oracle_blocks_duplicate() -> None:
    assert h.allows_duplicate(unique=True) is False
