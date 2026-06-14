"""Proof: the buggy (volatile) responder's answer changes under a meaning-preserving
perturbation; the oracle (normalized) is invariant. A single-phrasing example test would
miss the instability — only the metamorphic relation across perturbations exposes it.
"""

from harnesses.ai import metamorphic_stability_test_harness as h


def test_proof_buggy_is_unstable() -> None:
    assert h.unstable_under_perturbation(h.respond_volatile) is not None


def test_proof_oracle_is_stable() -> None:
    assert h.unstable_under_perturbation(h.respond_stable) is None
