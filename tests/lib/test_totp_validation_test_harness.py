"""Oracle + CLI-contract test for totp_validation (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_totp_validation_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import totp_validation_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.accepts_correct_code(h.TotpVerifier) is True


import pytest  # noqa: E402


def test_oracle_rejects_wrong_code() -> None:
    verifier = h.TotpVerifier()
    current = verifier.current(1000)
    wrong = "000001" if current != "000001" else "111111"
    assert verifier.verify(wrong, 1000) is False


def test_oracle_rejects_replayed_step() -> None:
    verifier = h.TotpVerifier()
    code = verifier.current(1000)
    assert verifier.verify(code, 1000) is True
    assert verifier.verify(code, 1000) is False


def test_oracle_rejects_stale_step() -> None:
    assert h.TotpVerifier().verify("123456", 999999) is False


@pytest.mark.parametrize("now", [0, 1000, 55, 1234567, 9999999])
def test_oracle_accepts_current_code(now) -> None:
    verifier = h.TotpVerifier()
    assert verifier.verify(verifier.current(now), now) is True


@pytest.mark.parametrize("bad", ["abc", ""])
def test_oracle_rejects_malformed_code(bad) -> None:
    assert h.TotpVerifier().verify(bad, 1000) is False


# === our own / batch 1 (original) ===
# Brandt (absurd/psych): no drift window -- a one-step-old code is already a stranger.
def test_oracle_no_drift_adjacent_step_rejected() -> None:
    verifier = h.TotpVerifier()
    prev_step_code = verifier.current(970)            # step 32
    assert verifier.verify(prev_step_code, 1000) is False   # current step is 33


# Adeyemi (whimsical/psych): poke the 30s fence -- 1019 and 1020 fall in different steps.
def test_oracle_step_boundary_off_by_one() -> None:
    verifier = h.TotpVerifier()
    code_step33 = verifier.current(1019)
    assert verifier.verify(code_step33, 1020) is False   # 1020 // 30 == 34, a new step


def test_oracle_independent_step_after_burn() -> None:
    verifier = h.TotpVerifier()
    assert verifier.verify(verifier.current(1000), 1000) is True   # burns step 33
    assert verifier.verify(verifier.current(1040), 1040) is True   # step 34 untouched
