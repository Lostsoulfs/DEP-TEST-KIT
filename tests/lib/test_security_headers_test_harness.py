"""Oracle + CLI-contract test for security_headers (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_security_headers_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import security_headers_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.serves_content(h.HardenedApp) is True


import pytest  # noqa: E402

_REQUIRED_HEADERS = [
    "Content-Security-Policy", "Strict-Transport-Security",
    "X-Frame-Options", "X-Content-Type-Options",
]
_FULL_HEADERS = {
    "Content-Type": "text/html",
    "Content-Security-Policy": "default-src 'self'",
    "Strict-Transport-Security": "max-age=63072000",
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
}


def _app_serving(headers):
    class _A:
        def headers(self):
            return headers
    return lambda: _A()


@pytest.mark.parametrize("dropped", _REQUIRED_HEADERS)
def test_oracle_flags_each_missing_required_header(dropped) -> None:
    partial = {k: v for k, v in _FULL_HEADERS.items() if k != dropped}
    assert h.missing_security_headers(_app_serving(partial)) is True, dropped


def test_oracle_passes_full_hardened_response() -> None:
    full = dict(_FULL_HEADERS, **{"Referrer-Policy": "no-referrer"})
    assert h.missing_security_headers(_app_serving(full)) is False


# === our own / batch 4 (original; web-checked KNOWN LIMIT) ===
# Brandt (absurd/psych) -- presence != strength (web: HSTS max-age=0 disables it; CSP "*" is
# ineffective). The required-keys schema checks that the headers EXIST, not that their values
# are safe, so a fully-neutered-but-present set still passes. Fix: validate values, not just keys.
def test_oracle_known_limit_presence_not_strength() -> None:
    from jsonschema import validate
    neutered = {"Content-Type": "text/html", "Content-Security-Policy": "default-src *",
                "Strict-Transport-Security": "max-age=0", "X-Frame-Options": "DENY",
                "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"}
    try:
        validate(neutered, h._REQUIRED)
        passed_despite_neutered = True
    except Exception:
        passed_despite_neutered = False
    assert passed_despite_neutered is True
