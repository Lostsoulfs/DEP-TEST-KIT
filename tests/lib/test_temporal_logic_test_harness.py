from harnesses.lib import temporal_logic_test_harness as h


def test_oracle_expires_at_boundary() -> None:
    assert h.expires_at_boundary(h.is_valid_oracle) is True


def test_self_test_passes() -> None:
    assert h.run_self_test() == 0
