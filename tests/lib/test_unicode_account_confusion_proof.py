"""Proof: canonicalization folds the look-alike the raw registry accepts as distinct.
A fullwidth 'admin' collides under NFKC+IDNA vs registering as a new account."""

from harnesses.lib import unicode_account_confusion_test_harness as h


def test_proof_buggy_is_flagged() -> None:
    assert h.confusable_impersonation(h.RawRegistry) is True


def test_proof_oracle_not_flagged() -> None:
    assert h.confusable_impersonation(h.CanonicalizingRegistry) is False


def test_proof_oracle_happy_path() -> None:
    assert h.registers_distinct_users(h.CanonicalizingRegistry) is True


import pytest  # noqa: E402

_CONFUSABLES = ["ａｄｍｉｎ", "ⓐⓓⓜⓘⓝ", "\U0001d41a\U0001d41d\U0001d426\U0001d422\U0001d427"]


@pytest.mark.parametrize("lookalike", _CONFUSABLES)
def test_proof_raw_registry_allows_confusable(lookalike) -> None:
    registry = h.RawRegistry()
    registry.register("admin@app.example")
    assert registry.register(lookalike + "@app.example") == lookalike + "@app.example", lookalike
