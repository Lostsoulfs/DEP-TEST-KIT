from harnesses.ai import agentic_pbt_test_harness as h


def test_oracle_satisfies_all_inferred_properties() -> None:
    assert h.falsified_property(h.ensure_prefix) is None


def test_self_test_passes() -> None:
    assert h.run_self_test() == 0
