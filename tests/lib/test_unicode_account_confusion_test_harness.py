"""Oracle + CLI-contract test for unicode_account_confusion (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_unicode_account_confusion_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import unicode_account_confusion_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.registers_distinct_users(h.CanonicalizingRegistry) is True


import pytest  # noqa: E402

_CONFUSABLES = ["ａｄｍｉｎ", "ⓐⓓⓜⓘⓝ", "\U0001d41a\U0001d41d\U0001d426\U0001d422\U0001d427"]


@pytest.mark.parametrize("lookalike", _CONFUSABLES)
def test_oracle_folds_confusable_lookalike(lookalike) -> None:
    registry = h.CanonicalizingRegistry()
    registry.register("admin@app.example")
    try:
        registry.register(lookalike + "@app.example")
        caught = False
    except ValueError:
        caught = True
    assert caught is True, lookalike


_DISTINCT_PAIRS = [("alice", "bob"), ("admin", "administrator"), ("john", "jane")]


@pytest.mark.parametrize("first,second", _DISTINCT_PAIRS)
def test_oracle_allows_distinct_accounts(first, second) -> None:
    registry = h.CanonicalizingRegistry()
    registry.register(first + "@app.example")
    registry.register(second + "@app.example")


# === our own / batch 5 (original; representation-gap) ===
# Toll (surreal/psych): NFKC + casefold collapse a whole ORBIT of look-alikes onto one identity
# -- fullwidth and mixed-case ADMIN all canonicalize to admin@x.com and collide. (Fullwidth
# A-D-M-I-N = U+FF21 FF24 FF2D FF29 FF2E, written as escapes to keep the source ASCII.)
def test_oracle_folds_nfkc_confusable_orbit() -> None:
    reg = h.CanonicalizingRegistry()
    reg.register("admin@x.com")
    for lookalike in ("ＡＤＭＩＮ@x.com", "Admin@x.com", "ADMIN@x.com"):
        try:
            reg.register(lookalike)
            collided = False
        except Exception:
            collided = True
        assert collided is True, lookalike
