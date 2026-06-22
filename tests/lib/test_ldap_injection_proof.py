"""Proof: escaping neutralizes the filter metacharacters the raw filter lets through.
*)(uid=* is escaped vs widening the search to every entry."""

from harnesses.lib import ldap_injection_test_harness as h


def test_proof_buggy_is_flagged() -> None:
    assert h.filter_injectable(h.RawFilter) is True


def test_proof_oracle_not_flagged() -> None:
    assert h.filter_injectable(h.EscapedFilter) is False


def test_proof_oracle_happy_path() -> None:
    assert h.builds_lookup_filter(h.EscapedFilter) is True


import pytest  # noqa: E402

_LDAP_PAYLOADS = [
    "*", "*)(uid=*", "*)(|(uid=*)", "admin)(&)",
    "*)(objectClass=*)", "x)(cn=*)", "*)(mail=*)",
]


@pytest.mark.parametrize("payload", _LDAP_PAYLOADS)
def test_proof_raw_filter_injects(payload) -> None:
    assert payload in h.RawFilter().build(payload), payload
