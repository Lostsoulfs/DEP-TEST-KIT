"""Oracle + CLI-contract test for failopen_authz (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_failopen_authz_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import failopen_authz_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.allows_when_permitted(h.FailClosedAuthz) is True


# --- scenario coverage: A10 backend error modes that must fail closed ---
class _RaisingClient:
    def __init__(self, exc):
        self._exc = exc

    def get(self, url, **kwargs):
        raise self._exc


def test_oracle_denies_on_every_backend_error() -> None:
    from requests.exceptions import ConnectionError as ConnErr, HTTPError
    errors = {"timeout": h.Timeout("t"), "connection": ConnErr("c"), "http_5xx": HTTPError("500")}
    for name, exc in errors.items():
        assert h.FailClosedAuthz(_RaisingClient(exc)).allow("mallory", "delete_all") is False, name


# --- second pass: explicit allow/deny honored (no over-deny, no over-allow) ---
def test_oracle_honors_explicit_allow_and_deny() -> None:
    assert h.FailClosedAuthz(h._HealthyClient(allow=True)).allow("alice", "read") is True
    assert h.FailClosedAuthz(h._HealthyClient(allow=False)).allow("alice", "read") is False


# --- third pass: a response with no decision is treated as deny ---
def test_oracle_does_not_grant_on_missing_decision() -> None:
    class _Garbage:
        def get(self, url, **kwargs):
            class _R:
                def json(self):
                    return {}
            return _R()

    assert h.FailClosedAuthz(_Garbage()).allow("mallory", "delete_all") is False


import pytest  # noqa: E402


@pytest.mark.parametrize("exc_name", [
    "Timeout", "ConnectionError", "HTTPError", "TooManyRedirects",
    "SSLError", "ConnectTimeout", "ReadTimeout", "ChunkedEncodingError",
])
def test_oracle_denies_on_request_exception(exc_name) -> None:
    import requests.exceptions as rexc

    class _Raise:
        def get(self, url, **kwargs):
            raise getattr(rexc, exc_name)("boom")

    assert h.FailClosedAuthz(_Raise()).allow("mallory", "delete_all") is False, exc_name


# === our own / batch 4 (original; math bench + web-checked KNOWN LIMIT) ===
# Brandt (absurd/psych) -- stringly-typed decision (web: the Discourse `== "true"` class). The
# deny-by-default oracle still does bool(resp.json()["allow"]), so a policy that returns the
# STRING "false" or "0" GRANTS (non-empty strings are truthy). int 0 correctly denies.
# Fix: require a real JSON boolean, not a truthy coercion.
def test_oracle_known_limit_stringly_typed_decision_grants() -> None:
    class _StrClient:
        def __init__(self, v):
            self._v = v

        def get(self, url, **kwargs):
            return h._Resp({"allow": self._v})

    assert h.FailClosedAuthz(_StrClient("false")).allow("u", "a") is True
    assert h.FailClosedAuthz(_StrClient("0")).allow("u", "a") is True
    assert h.FailClosedAuthz(_StrClient(0)).allow("u", "a") is False
