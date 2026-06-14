"""Proof: the inferred properties catch the buggy impl; the oracle holds."""

from harnesses.ai import agentic_pbt_test_harness as h


def test_proof_buggy_is_caught() -> None:
    assert h.falsified_property(h.buggy_ensure_prefix) is not None


def test_proof_buggy_breaks_idempotence_concretely() -> None:
    # Always-prepend is not idempotent; the oracle is.
    assert h.buggy_ensure_prefix(h.buggy_ensure_prefix("a")) != h.buggy_ensure_prefix("a")
    assert h.ensure_prefix(h.ensure_prefix("a")) == h.ensure_prefix("a")
