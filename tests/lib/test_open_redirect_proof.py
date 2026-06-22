"""Proof: the allowlist redirect stays on-origin where the naive redirect follows off-site.
An external target falls back to '/' vs being returned unchanged."""

from harnesses.lib import open_redirect_test_harness as h


def test_proof_buggy_is_flagged() -> None:
    assert h.redirects_offsite(h.OpenRedirect) is True


def test_proof_oracle_not_flagged() -> None:
    assert h.redirects_offsite(h.AllowlistRedirect) is False


def test_proof_oracle_happy_path() -> None:
    assert h.allows_same_site(h.AllowlistRedirect) is True


import pytest  # noqa: E402

_OFFSITE_BYPASSES = [
    "//evil.com", "https://evil.com", "https://app.example@evil.com",
    "https://app.example.evil.com", "https://app.example.attacker.com",
    "http://evil.com", "https://evil.com/app.example",
]


@pytest.mark.parametrize("target", _OFFSITE_BYPASSES)
def test_proof_naive_redirect_follows_offsite(target) -> None:
    host = h._host(h.OpenRedirect().resolve(target))
    assert host is not None and host not in h._ALLOWED, target
