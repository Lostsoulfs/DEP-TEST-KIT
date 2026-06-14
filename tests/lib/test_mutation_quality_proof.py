"""Proof: mutmut catches the vacuous (weak) suite and clears the strong one."""

import pytest

from harnesses.lib import mutation_quality_test_harness as h

pytestmark = pytest.mark.skipif(
    not h.mutmut_available(),
    reason="mutmut unavailable on this platform (native Windows unsupported; runs on Linux/CI/WSL)",
)


def test_proof_weak_suite_leaves_survivors() -> None:
    # The vacuous suite executes the line but lets mutants live.
    assert h.count_survivors(h.WEAK_TEST_SRC) > 0


def test_proof_strong_suite_has_no_survivors() -> None:
    assert h.count_survivors(h.STRONG_TEST_SRC) == 0
