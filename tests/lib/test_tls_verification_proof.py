"""Proof: the verifying client refuses the invalid certificate the verify=False client accepts.
SSLError on the bad cert vs a 200 once verification is disabled."""

from harnesses.lib import tls_verification_test_harness as h


def test_proof_buggy_is_flagged() -> None:
    assert h.accepts_invalid_cert(h.InsecureClient) is True


def test_proof_oracle_not_flagged() -> None:
    assert h.accepts_invalid_cert(h.StrictClient) is False


def test_proof_oracle_happy_path() -> None:
    assert h.fetches_valid_https_ok(h.StrictClient) is True


# --- scenario coverage: the verify=False client accepts each bad transport ---
def test_proof_buggy_accepts_invalid_cert() -> None:
    assert h.InsecureClient().fetch("https://bank.example/", h._InvalidCertAdapter()) == 200


def test_proof_buggy_accepts_cleartext() -> None:
    assert h.InsecureClient().fetch("http://bank.example/", h._ValidCertAdapter()) == 200
