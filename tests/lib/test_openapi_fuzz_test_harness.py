from harnesses.lib import openapi_fuzz_test_harness as h


def test_oracle_app_conforms() -> None:
    assert h.conforms_to_contract(h.ORACLE_COUNT) is True


def test_self_test_passes() -> None:
    assert h.run_self_test() == 0
