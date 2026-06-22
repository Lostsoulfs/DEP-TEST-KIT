"""Oracle + CLI-contract test for ldap_injection (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_ldap_injection_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import ldap_injection_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.builds_lookup_filter(h.EscapedFilter) is True


import pytest  # noqa: E402

_LDAP_PAYLOADS = [
    "*", "*)(uid=*", "*)(|(uid=*)", "admin)(&)",
    "*)(objectClass=*)", "x)(cn=*)", "*)(mail=*)",
]


@pytest.mark.parametrize("payload", _LDAP_PAYLOADS)
def test_oracle_escapes_filter_metacharacters(payload) -> None:
    assert payload not in h.EscapedFilter().build(payload), payload


_BENIGN_NAMES = ["alice", "bob", "user.name", "admin2", "Jane Doe"]


@pytest.mark.parametrize("name", _BENIGN_NAMES)
def test_oracle_builds_benign_filter(name) -> None:
    assert h.EscapedFilter().build(name) == f"(uid={name})", name


# === our own / batch 6 (original; copy-verified vs ldap3.escape_filter_chars) ===
# Knox (absurd/sw) + math: every RFC-4515 filter metacharacter is escaped to \HH -- including a
# bare "*", which unescaped would match ALL entries (an auth-bypass wildcard).
def test_oracle_escapes_each_ldap_metacharacter() -> None:
    star = h.EscapedFilter().build("*").lower()              # bare wildcard neutralised
    assert star == "(uid=\\2a)"                              # ldap3 emits lowercase \HH
    out = h.EscapedFilter().build("*)(uid=*").lower()        # the classic LDAP filter injection
    assert ")(" not in out                                   # cannot break out of the filter
    assert "\\2a" in out and "\\28" in out and "\\29" in out  # metachars escaped to \HH
