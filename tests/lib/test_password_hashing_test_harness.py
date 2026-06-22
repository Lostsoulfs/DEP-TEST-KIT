"""Oracle + CLI-contract test for password_hashing (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_password_hashing_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import password_hashing_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.verifies_correct_password(h.ScryptHasher) is True


import pytest  # noqa: E402

_PASSWORDS = ["", "hunter2", "p@ss w0rd", "uñicöde", "x" * 100]


@pytest.mark.parametrize("password", _PASSWORDS)
def test_oracle_salts_each_password(password) -> None:
    hasher = h.ScryptHasher()
    assert hasher.hash(password) != hasher.hash(password), password


_BENIGN_PASSWORDS = ["", "hunter2", "p@ss w0rd", "uñicöde", "x" * 100]


@pytest.mark.parametrize("password", _BENIGN_PASSWORDS)
def test_oracle_verifies_correct_and_rejects_nearmiss(password) -> None:
    hasher = h.ScryptHasher()
    stored = hasher.hash(password)
    assert hasher.verify(password, stored) is True
    assert hasher.verify(password + "x", stored) is False
