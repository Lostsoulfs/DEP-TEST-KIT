"""Proof: the scalar-validating query rejects the operator object the raw query lets through.
{$ne: null} is refused vs reaching the filter as a match-all."""

from harnesses.lib import nosql_injection_test_harness as h


def test_proof_buggy_is_flagged() -> None:
    assert h.operator_injection(h.RawQuery) is True


def test_proof_oracle_not_flagged() -> None:
    assert h.operator_injection(h.ScalarValidatedQuery) is False


def test_proof_oracle_happy_path() -> None:
    assert h.builds_scalar_query(h.ScalarValidatedQuery) is True


import pytest  # noqa: E402

_OPERATOR_PAYLOADS = [
    {"$ne": None}, {"$gt": ""}, {"$regex": ".*"}, {"$where": "1==1"},
    {"$in": [1, 2]}, {"$exists": True}, {"$nin": []},
]


@pytest.mark.parametrize("payload", _OPERATOR_PAYLOADS)
def test_proof_raw_query_injects_operator(payload) -> None:
    assert isinstance(h.RawQuery().build(payload).get("username"), dict), payload
