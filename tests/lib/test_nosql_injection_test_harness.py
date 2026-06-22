"""Oracle + CLI-contract test for nosql_injection (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_nosql_injection_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import nosql_injection_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.builds_scalar_query(h.ScalarValidatedQuery) is True


import pytest  # noqa: E402

_OPERATOR_PAYLOADS = [
    {"$ne": None}, {"$gt": ""}, {"$regex": ".*"}, {"$where": "1==1"},
    {"$in": [1, 2]}, {"$exists": True}, {"$nin": []},
]


@pytest.mark.parametrize("payload", _OPERATOR_PAYLOADS)
def test_oracle_rejects_operator_payload(payload) -> None:
    try:
        h.ScalarValidatedQuery().build(payload)
        rejected = False
    except Exception:
        rejected = True
    assert rejected is True, payload


_SCALAR_USERNAMES = ["alice", "", "O'Brien", "a" * 100, "user@example"]


@pytest.mark.parametrize("username", _SCALAR_USERNAMES)
def test_oracle_builds_scalar_query(username) -> None:
    assert h.ScalarValidatedQuery().build(username) == {"username": username}


_NON_STRING_SCALARS = [123, 4.5, True, ["a"], None]


@pytest.mark.parametrize("value", _NON_STRING_SCALARS)
def test_oracle_rejects_non_string_scalar(value) -> None:
    with pytest.raises(Exception):
        h.ScalarValidatedQuery().build(value)
