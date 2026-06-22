"""Oracle + CLI-contract test for graphql_depth_limit (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_graphql_depth_limit_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import graphql_depth_limit_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.executes_shallow_query(h.DepthLimitedSchema) is True


import pytest  # noqa: E402

_DEEP_QUERIES = [
    "{ a { b { c { d { e { f } } } } } }",
    "{ a { b { c { d { e { f { g } } } } } } }",
    "{ a { b { c { d { e { f { g { h } } } } } } } }",
]
_SHALLOW_QUERIES = ["{ user { name email } }", "{ a { b { c { d } } } }"]


@pytest.mark.parametrize("query", _DEEP_QUERIES)
def test_oracle_rejects_overdeep_query(query) -> None:
    with pytest.raises(ValueError):
        h.DepthLimitedSchema().execute(query)


@pytest.mark.parametrize("query", _SHALLOW_QUERIES)
def test_oracle_accepts_within_budget_query(query) -> None:
    assert h.DepthLimitedSchema().execute(query) == "ok", query


_LEGIT_SHAPES = [
    "{ a { b } c { d } }",
    "{ user { id name email role } }",
    "{ a { b { c { d { e } } } } }",
]


@pytest.mark.parametrize("query", _LEGIT_SHAPES)
def test_oracle_accepts_legit_shapes(query) -> None:
    assert h.DepthLimitedSchema().execute(query) == "ok", query


# === our own / batch 6 (original; reasoned vs the depth counter, _MAX_DEPTH=5) ===
# Adeyemi (whimsical/psych) + math: the depth fence is exact -- a depth-5 query is accepted, a
# depth-6 query is rejected (off-by-one at the budget; hand-traced against _query_depth).
def test_oracle_depth_budget_off_by_one() -> None:
    depth5 = "{ a { b { c { d { e } } } } }"
    depth6 = "{ a { b { c { d { e { f } } } } } }"
    assert h.DepthLimitedSchema().execute(depth5) == "ok"
    try:
        h.DepthLimitedSchema().execute(depth6)
        rejected = False
    except ValueError:
        rejected = True
    assert rejected is True
