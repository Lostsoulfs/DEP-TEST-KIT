"""Oracle + CLI-contract test for tls_verification (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_tls_verification_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import tls_verification_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.fetches_valid_https_ok(h.StrictClient) is True


# --- scenario coverage: more A02 transport situations the strict client must refuse ---
def _tls_status(make_client, url, server):
    try:
        return make_client().fetch(url, server)
    except (h.SSLError, h.InsecureTransport):
        return None


def test_oracle_rejects_invalid_cert_server() -> None:
    assert _tls_status(h.StrictClient, "https://bank.example/", h._InvalidCertAdapter()) is None


def test_oracle_refuses_cleartext_http() -> None:
    assert _tls_status(h.StrictClient, "http://bank.example/", h._ValidCertAdapter()) is None


def test_oracle_allows_valid_https() -> None:
    assert _tls_status(h.StrictClient, "https://api.example/", h._ValidCertAdapter()) == 200


# --- second pass: benign robustness + non-https scheme refused ---
def test_oracle_allows_second_valid_https_host() -> None:
    assert _tls_status(h.StrictClient, "https://api2.example/v1", h._ValidCertAdapter()) == 200


def test_oracle_refuses_non_https_scheme() -> None:
    assert _tls_status(h.StrictClient, "ftp://files.example/x", h._ValidCertAdapter()) is None


# --- third pass: malformed URLs never complete a request ---
def test_oracle_never_succeeds_on_malformed_urls() -> None:
    for url in ["", "://x", "https//missing-colon", "gopher://x/"]:
        assert _tls_status(h.StrictClient, url, h._ValidCertAdapter()) is None, url


import pytest  # noqa: E402


@pytest.mark.parametrize("url", [
    "http://x/", "ftp://x/", "gopher://x/", "file:///etc/passwd",
    "ws://x/", "dict://x/", "//x/", "x",
])
def test_oracle_refuses_non_https_scheme_corpus(url) -> None:
    assert _tls_status(h.StrictClient, url, h._ValidCertAdapter()) is None, url


# === our own / batch 4 (original; metamorphic) ===
# Constantin (surreal/sw): the scheme check is case-insensitive because urlparse normalises it,
# so "HTTPS"/"HtTpS" are accepted (no false-reject) while uppercase "HTTP" is still refused.
def test_oracle_scheme_check_is_case_insensitive() -> None:
    assert h.StrictClient().fetch("HTTPS://app.example/", h._ValidCertAdapter()) == 200
    assert h.StrictClient().fetch("HtTpS://app.example/", h._ValidCertAdapter()) == 200
    try:
        h.StrictClient().fetch("HTTP://app.example/", h._ValidCertAdapter())
        refused = False
    except Exception:
        refused = True
    assert refused is True
