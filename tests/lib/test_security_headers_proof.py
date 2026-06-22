"""Proof: the header contract flags the lax app's missing headers the hardened app passes.
CSP/HSTS/X-Frame-Options absent in the lax response vs present in the hardened one."""

from harnesses.lib import security_headers_test_harness as h


def test_proof_buggy_is_flagged() -> None:
    assert h.missing_security_headers(h.LaxApp) is True


def test_proof_oracle_not_flagged() -> None:
    assert h.missing_security_headers(h.HardenedApp) is False


def test_proof_oracle_happy_path() -> None:
    assert h.serves_content(h.HardenedApp) is True
