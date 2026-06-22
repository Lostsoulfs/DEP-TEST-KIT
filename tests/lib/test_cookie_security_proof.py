"""Proof: the flag contract flags the insecure cookie the secure setter passes.
Secure/HttpOnly/SameSite absent vs present on the session cookie."""

from harnesses.lib import cookie_security_test_harness as h


def test_proof_buggy_is_flagged() -> None:
    assert h.cookie_missing_flags(h.InsecureCookieSetter) is True


def test_proof_oracle_not_flagged() -> None:
    assert h.cookie_missing_flags(h.SecureCookieSetter) is False


def test_proof_oracle_happy_path() -> None:
    assert h.sets_the_cookie(h.SecureCookieSetter) is True
