"""Proof: bound parameters keep the payload out of the SQL the f-string inlines.
' OR '1'='1 stays a placeholder value vs appearing verbatim in the query text."""

from harnesses.lib import sql_injection_test_harness as h


def test_proof_buggy_is_flagged() -> None:
    assert h.query_is_injectable(h.StringFormatQuery) is True


def test_proof_oracle_not_flagged() -> None:
    assert h.query_is_injectable(h.ParameterizedQuery) is False


def test_proof_oracle_happy_path() -> None:
    assert h.builds_lookup_query(h.ParameterizedQuery) is True


import pytest  # noqa: E402

_SQLI_PAYLOADS = [
    "' OR '1'='1", "'; DROP TABLE users--", "' UNION SELECT password FROM users--",
    "admin'--", "' OR 1=1#", "1' AND '1'='1", "' OR 'a'='a", "'; EXEC xp_cmdshell('dir')--",
]


@pytest.mark.parametrize("payload", _SQLI_PAYLOADS)
def test_proof_fstring_inlines_payload(payload) -> None:
    assert payload in h.StringFormatQuery().rendered_sql(payload), payload
