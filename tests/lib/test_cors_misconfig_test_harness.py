"""Oracle + CLI-contract test for cors_misconfig (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_cors_misconfig_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import cors_misconfig_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.allows_trusted_origin(h.AllowlistCors) is True


import pytest  # noqa: E402

_UNTRUSTED_ORIGINS = [
    "null", "https://evil.com", "https://app.example.evil.com", "https://evilapp.example",
    "https://app.example.attacker.com", "https://sub.app.example",
]


@pytest.mark.parametrize("origin", _UNTRUSTED_ORIGINS)
def test_oracle_denies_untrusted_origin(origin) -> None:
    assert h.AllowlistCors().headers(origin).get(h._ACAO) is None, origin


_TRUSTED_ORIGINS = ["https://app.example", "https://app.example/path", "http://app.example"]


@pytest.mark.parametrize("origin", _TRUSTED_ORIGINS)
def test_oracle_allows_trusted_origin(origin) -> None:
    assert h.AllowlistCors().headers(origin).get("Access-Control-Allow-Origin") == origin


_GARBAGE_ORIGINS = ["", "null", "://", "not a url", "http://", "javascript:x"]


@pytest.mark.parametrize("origin", _GARBAGE_ORIGINS)
def test_oracle_no_acao_for_garbage_origin(origin) -> None:
    assert h.AllowlistCors().headers(origin).get("Access-Control-Allow-Origin") is None, origin


# === our own / batch 4 (original; panel + math bench + web-checked) ===
# Toll (surreal/psych): the eye reads "app.example" inside the string; the host SET reads the
# whole host -- suffix/substring lookalikes are not the allowlisted origin.
def test_oracle_suffix_substring_lookalikes_get_no_acao() -> None:
    for origin in ("https://app.example.evil.com", "https://evil-app.example",
                   "https://notapp.example", "https://app.example.attacker.com",
                   "https://xapp.example"):
        assert h.AllowlistCors().headers(origin) == {}, origin


# Adeyemi (whimsical/psych) + math -- KNOWN LIMIT (web: an Origin is scheme+host+port). This
# allowlist matches the HOST only, so it reflects an insecure-scheme or odd-port origin of an
# allowlisted host. Honest weakness; the fix is to match the full origin, not just the hostname.
def test_oracle_known_limit_host_only_match_ignores_scheme_port() -> None:
    assert h.AllowlistCors().headers("http://app.example").get(h._ACAO) == "http://app.example"
    port_origin = "https://app.example:8443"
    assert h.AllowlistCors().headers(port_origin).get(h._ACAO) == port_origin
