"""Proof: the deterministic rubric grader catches an output that violates one hard-coded
rubric step (confidence out of [0,1]); the conformant output passes. An `assert ==` or an
inert check could not express the rubric and would pass both.
"""

from harnesses.ai import geval_rubric_test_harness as h


def test_proof_buggy_output_is_caught() -> None:
    assert h.output_satisfies_rubric(h.BUGGY_OUTPUT) is False


def test_proof_oracle_output_passes() -> None:
    assert h.output_satisfies_rubric(h.ORACLE_OUTPUT) is True
