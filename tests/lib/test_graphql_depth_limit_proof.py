"""Proof: the depth-limited schema refuses the deep query the unbounded schema executes.
A 7-level query exceeds the budget vs being run; a 2-level query runs."""

from harnesses.lib import graphql_depth_limit_test_harness as h


def test_proof_buggy_is_flagged() -> None:
    assert h.executes_deeply_nested(h.UnboundedSchema) is True


def test_proof_oracle_not_flagged() -> None:
    assert h.executes_deeply_nested(h.DepthLimitedSchema) is False


def test_proof_oracle_happy_path() -> None:
    assert h.executes_shallow_query(h.DepthLimitedSchema) is True


import pytest  # noqa: E402

_DEEP_QUERIES = [
    "{ a { b { c { d { e { f } } } } } }",
    "{ a { b { c { d { e { f { g } } } } } } }",
    "{ a { b { c { d { e { f { g { h } } } } } } } }",
]


@pytest.mark.parametrize("query", _DEEP_QUERIES)
def test_proof_unbounded_schema_executes_overdeep(query) -> None:
    assert h.UnboundedSchema().execute(query) == "ok", query
