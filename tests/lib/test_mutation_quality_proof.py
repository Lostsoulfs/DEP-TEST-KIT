"""Proof: mutmut catches the vacuous (weak) suite and clears the strong one."""

from harnesses.lib import mutation_quality_test_harness as h


def test_proof_weak_suite_leaves_survivors() -> None:
    # The vacuous suite executes the line but lets mutants live.
    assert h.count_survivors(h.WEAK_TEST_SRC) > 0


def test_proof_strong_suite_has_no_survivors() -> None:
    assert h.count_survivors(h.STRONG_TEST_SRC) == 0
