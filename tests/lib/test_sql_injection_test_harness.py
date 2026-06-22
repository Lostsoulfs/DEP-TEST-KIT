"""Oracle + CLI-contract test for sql_injection (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_sql_injection_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import sql_injection_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.builds_lookup_query(h.ParameterizedQuery) is True


import pytest  # noqa: E402

_SQLI_PAYLOADS = [
    "' OR '1'='1", "'; DROP TABLE users--", "' UNION SELECT password FROM users--",
    "admin'--", "' OR 1=1#", "1' AND '1'='1", "' OR 'a'='a", "'; EXEC xp_cmdshell('dir')--",
]


@pytest.mark.parametrize("payload", _SQLI_PAYLOADS)
def test_oracle_keeps_payload_out_of_sql(payload) -> None:
    assert payload not in h.ParameterizedQuery().rendered_sql(payload), payload


_BENIGN_NAMES = ["alice", "bob", "O'Brien", "admin"]


@pytest.mark.parametrize("username", _BENIGN_NAMES)
def test_oracle_binds_value_as_parameter(username) -> None:
    rendered = h.ParameterizedQuery().rendered_sql(username)
    assert ":name" in rendered and username not in rendered, username


# === our own / batch 6 (original; reasoned vs sqlalchemy bound params) ===
# Knox (absurd/sw) + math: a bound parameter renders as ":name" -- the value never enters the
# SQL text, so no injection payload survives into the compiled statement.
def test_oracle_bound_param_keeps_injection_corpus_out_of_sql() -> None:
    payloads = ["' OR '1'='1", "'; DROP TABLE users--",
                "' UNION SELECT password FROM users--", "admin'--", "1; DELETE FROM users"]
    for p in payloads:
        rendered = h.ParameterizedQuery().rendered_sql(p)
        assert ":name" in rendered and p not in rendered, p
