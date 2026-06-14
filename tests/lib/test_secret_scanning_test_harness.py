from harnesses.lib import secret_scanning_test_harness as h


def test_oracle_finds_secrets() -> None:
    assert h.detect_secrets_count(h.BLOB) > 0


def test_self_test_passes() -> None:
    assert h.run_self_test() == 0
