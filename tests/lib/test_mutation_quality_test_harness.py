from harnesses.lib import mutation_quality_test_harness as h


def test_strong_suite_kills_all_mutants() -> None:
    assert h.count_survivors(h.STRONG_TEST_SRC) == 0


def test_self_test_passes() -> None:
    assert h.run_self_test() == 0
