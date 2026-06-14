from harnesses.lib import sql_orm_test_harness as h


def test_oracle_rejects_duplicate() -> None:
    assert h.allows_duplicate(unique=True) is False


def test_self_test_passes() -> None:
    assert h.run_self_test() == 0
