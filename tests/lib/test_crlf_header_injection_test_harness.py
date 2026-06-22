"""Oracle + CLI-contract test for crlf_header_injection (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_crlf_header_injection_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import crlf_header_injection_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.writes_valid_header(h.SafeHeaderWriter) is True


import pytest  # noqa: E402

_NEWLINE_PAYLOADS = [
    "value\r\nSet-Cookie: x=1", "value\nSet-Cookie: x=1", "value\rSet-Cookie: x=1",
    "value\r\n\r\n<html>", "value\r\nLocation: //evil",
]


@pytest.mark.parametrize("payload", _NEWLINE_PAYLOADS)
def test_oracle_rejects_crlf_variant(payload) -> None:
    try:
        h.SafeHeaderWriter().write("X-H", payload)
        accepted = True
    except Exception:
        accepted = False
    assert accepted is False, repr(payload)


_VALID_VALUES = [
    "text/html", "Bearer abc123", "max-age=31536000", "application/json; charset=utf-8",
]


@pytest.mark.parametrize("value", _VALID_VALUES)
def test_oracle_writes_valid_header(value) -> None:
    written = h.SafeHeaderWriter().write("X-Custom", value)
    assert written.get("X-Custom") == value, value


# === our own / batch 4 (original; panel + math bench) ===
# Knox (absurd/sw): the header NAME is an attack surface too -- a CRLF in the name is rejected,
# not just in the value.
def test_oracle_rejects_crlf_in_header_name() -> None:
    try:
        h.SafeHeaderWriter().write("X-Evil\r\nSet-Cookie: x=y", "v")
        rejected = False
    except Exception:
        rejected = True
    assert rejected is True


# math bench (coverage): every ASCII line terminator that could split a response is rejected.
def test_oracle_rejects_every_ascii_terminator_in_value() -> None:
    for term in ("\r", "\n", "\r\n"):
        try:
            h.SafeHeaderWriter().write("X-Token", "a" + term + "b")
            rejected = False
        except Exception:
            rejected = True
        assert rejected is True, repr(term)
