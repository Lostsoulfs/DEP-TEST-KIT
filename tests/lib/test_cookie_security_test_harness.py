"""Oracle + CLI-contract test for cookie_security (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_cookie_security_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import cookie_security_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.sets_the_cookie(h.SecureCookieSetter) is True


import pytest  # noqa: E402

_REQUIRED_FLAGS = ["Secure", "HttpOnly", "SameSite"]
_FULL_COOKIE = {"name": "sid", "value": "abc", "Secure": True, "HttpOnly": True,
                "SameSite": "Strict"}


def _setter_emitting(cookie):
    class _S:
        def set(self, value):
            return cookie
    return lambda: _S()


@pytest.mark.parametrize("dropped", _REQUIRED_FLAGS)
def test_oracle_flags_each_missing_flag(dropped) -> None:
    partial = {k: v for k, v in _FULL_COOKIE.items() if k != dropped}
    assert h.cookie_missing_flags(_setter_emitting(partial)) is True, dropped


@pytest.mark.parametrize("samesite", ["Strict", "Lax", "None"])
def test_oracle_passes_fully_flagged_cookie(samesite) -> None:
    cookie = {"name": "sid", "value": "abc", "Secure": True, "HttpOnly": True, "SameSite": samesite}
    assert h.cookie_missing_flags(_setter_emitting(cookie)) is False


# === our own / batch 4 (original; KNOWN LIMIT) ===
# Brandt (absurd/psych) -- presence != value. The schema requires the flag KEYS to exist, so a
# cookie with Secure=False and SameSite="None" still passes though it is not actually secure.
# Fix: assert the values (Secure is True, SameSite in {Strict, Lax}).
def test_oracle_known_limit_presence_not_value() -> None:
    from jsonschema import validate
    weak = {"name": "sid", "value": "abc", "Secure": False, "HttpOnly": False, "SameSite": "None"}
    try:
        validate(weak, h._REQUIRED)
        passed_despite_weak = True
    except Exception:
        passed_despite_weak = False
    assert passed_despite_weak is True
