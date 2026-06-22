"""Proof: requests' header validation rejects the CRLF the raw concatenation injects.
The Set-Cookie payload is dropped vs riding along in the raw header line."""

from harnesses.lib import crlf_header_injection_test_harness as h


def test_proof_buggy_is_flagged() -> None:
    assert h.header_injection_succeeds(h.RawHeaderWriter) is True


def test_proof_oracle_not_flagged() -> None:
    assert h.header_injection_succeeds(h.SafeHeaderWriter) is False


def test_proof_oracle_happy_path() -> None:
    assert h.writes_valid_header(h.SafeHeaderWriter) is True


import pytest  # noqa: E402

_NEWLINE_PAYLOADS = [
    "value\r\nSet-Cookie: x=1", "value\nSet-Cookie: x=1", "value\rSet-Cookie: x=1",
    "value\r\n\r\n<html>", "value\r\nLocation: //evil",
]


@pytest.mark.parametrize("payload", _NEWLINE_PAYLOADS)
def test_proof_raw_writer_injects_crlf(payload) -> None:
    raw = h.RawHeaderWriter().write("X-H", payload)
    assert any("\n" in str(v) or "\r" in str(v) for v in raw.values()), repr(payload)
