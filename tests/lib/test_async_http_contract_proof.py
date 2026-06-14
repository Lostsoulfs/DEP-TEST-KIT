"""Proof: the no-retry client is caught on every transient fault; the oracle holds."""

import httpx

from harnesses.lib import async_http_contract_test_harness as h


def test_proof_no_retry_client_is_caught_on_503() -> None:
    assert h.survives_transient(h.fetch_no_retry, httpx.Response(503)) is False


def test_proof_no_retry_client_is_caught_on_timeout() -> None:
    assert h.survives_transient(h.fetch_no_retry, httpx.ReadTimeout("slow")) is False


def test_proof_oracle_recovers_from_both_faults() -> None:
    for fault in h.FAULTS.values():
        assert h.survives_transient(h.fetch_with_retry, fault) is True
