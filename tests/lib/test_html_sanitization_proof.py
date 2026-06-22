"""Proof: nh3 strips the script tag the raw renderer stores.
<script> is removed/escaped vs surviving live in the stored HTML."""

from harnesses.lib import html_sanitization_test_harness as h


def test_proof_buggy_is_flagged() -> None:
    assert h.reflects_active_script(h.RawHtmlRenderer) is True


def test_proof_oracle_not_flagged() -> None:
    assert h.reflects_active_script(h.SanitizingRenderer) is False


def test_proof_oracle_happy_path() -> None:
    assert h.renders_safe_markup(h.SanitizingRenderer) is True


import pytest  # noqa: E402

_XSS_PAYLOADS = [
    "<script>alert(1)</script>", "<img src=x onerror=alert(1)>", "<svg onload=alert(1)>",
    '"><script>alert(1)</script>', "<body onload=alert(1)>", "<iframe src=javascript:alert(1)>",
    '<a href="javascript:alert(1)">x</a>', "<details open ontoggle=alert(1)>",
    "<input autofocus onfocus=alert(1)>", "<marquee onstart=alert(1)>", "<ScRiPt>alert(1)</ScRiPt>",
]


@pytest.mark.parametrize("payload", _XSS_PAYLOADS)
def test_proof_raw_renderer_keeps_xss(payload) -> None:
    assert h.RawHtmlRenderer().render(payload) == payload, payload
