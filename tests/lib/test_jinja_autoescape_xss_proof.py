"""Proof: auto-escaping neutralizes the script tag the unescaped env reflects.
The <script> payload becomes inert &lt;script&gt; vs surviving live in the output."""

from harnesses.lib import jinja_autoescape_xss_test_harness as h


def test_proof_buggy_is_flagged() -> None:
    assert h.reflects_unescaped_script(h.UnescapedRenderer) is True


def test_proof_oracle_not_flagged() -> None:
    assert h.reflects_unescaped_script(h.AutoescapeRenderer) is False


def test_proof_oracle_happy_path() -> None:
    assert h.renders_plain_text(h.AutoescapeRenderer) is True


import pytest  # noqa: E402

_XSS_PAYLOADS = [
    "<script>alert(1)</script>", "<img src=x onerror=alert(1)>", "<svg onload=alert(1)>",
    '"><script>alert(1)</script>', "<body onload=alert(1)>", "<iframe src=javascript:alert(1)>",
    '<a href="javascript:alert(1)">x</a>', "<details open ontoggle=alert(1)>",
    "<input autofocus onfocus=alert(1)>", "<marquee onstart=alert(1)>", "<ScRiPt>alert(1)</ScRiPt>",
]


@pytest.mark.parametrize("payload", _XSS_PAYLOADS)
def test_proof_unescaped_reflects_xss(payload) -> None:
    assert payload in h.UnescapedRenderer().render(payload), payload
