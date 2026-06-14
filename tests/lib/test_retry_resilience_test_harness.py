from harnesses.lib import retry_resilience_test_harness as h


def test_oracle_attempts_permanent_once() -> None:
    assert h.attempts_for_permanent(h.oracle_policy) == 1


def test_self_test_passes() -> None:
    assert h.run_self_test() == 0
