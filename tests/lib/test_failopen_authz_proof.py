"""Proof: fail-closed denies on a backend error where fail-open grants access.
The timed-out policy call yields deny vs allow (CWE-636)."""

from harnesses.lib import failopen_authz_test_harness as h


def test_proof_buggy_is_flagged() -> None:
    assert h.fails_open_on_error(h.FailOpenAuthz) is True


def test_proof_oracle_not_flagged() -> None:
    assert h.fails_open_on_error(h.FailClosedAuthz) is False


def test_proof_oracle_happy_path() -> None:
    assert h.allows_when_permitted(h.FailClosedAuthz) is True


# --- scenario coverage: the fail-open authz grants on every backend error ---
class _RaisingClient:
    def __init__(self, exc):
        self._exc = exc

    def get(self, url, **kwargs):
        raise self._exc


def test_proof_buggy_grants_on_every_error() -> None:
    from requests.exceptions import ConnectionError as ConnErr, HTTPError
    for exc in (h.Timeout("t"), ConnErr("c"), HTTPError("500")):
        assert h.FailOpenAuthz(_RaisingClient(exc)).allow("mallory", "delete_all") is True
