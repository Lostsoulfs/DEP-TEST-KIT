from harnesses.lib import crypto_correctness_test_harness as h


def test_oracle_roundtrips() -> None:
    assert h.roundtrips(h.AeadBox()) is True


def test_oracle_rejects_tamper() -> None:
    assert h.accepts_tampered_ciphertext(h.AeadBox()) is False


def test_self_test_passes() -> None:
    assert h.run_self_test() == 0
