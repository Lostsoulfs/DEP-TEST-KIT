import httpx

from harnesses.lib import async_http_contract_test_harness as h


def test_oracle_survives_transient_503() -> None:
    assert h.survives_transient(h.fetch_with_retry, httpx.Response(503)) is True


def test_oracle_survives_transient_timeout() -> None:
    assert h.survives_transient(h.fetch_with_retry, httpx.ReadTimeout("slow")) is True


def test_self_test_passes() -> None:
    assert h.run_self_test() == 0
