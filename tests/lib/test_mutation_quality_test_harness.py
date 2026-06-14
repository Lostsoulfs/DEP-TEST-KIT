import pytest

from harnesses.lib import mutation_quality_test_harness as h


@pytest.mark.skipif(
    not h.mutmut_available(),
    reason="mutmut unavailable on this platform (native Windows unsupported; runs on Linux/CI/WSL)",
)
def test_strong_suite_kills_all_mutants() -> None:
    assert h.count_survivors(h.STRONG_TEST_SRC) == 0


def test_self_test_passes() -> None:
    assert h.run_self_test() == 0
