"""Oracle + CLI-contract test for html_sanitization (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_html_sanitization_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import html_sanitization_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.renders_safe_markup(h.SanitizingRenderer) is True


import pytest  # noqa: E402

_XSS_PAYLOADS = [
    "<script>alert(1)</script>", "<img src=x onerror=alert(1)>", "<svg onload=alert(1)>",
    '"><script>alert(1)</script>', "<body onload=alert(1)>", "<iframe src=javascript:alert(1)>",
    '<a href="javascript:alert(1)">x</a>', "<details open ontoggle=alert(1)>",
    "<input autofocus onfocus=alert(1)>", "<marquee onstart=alert(1)>", "<ScRiPt>alert(1)</ScRiPt>",
]


@pytest.mark.parametrize("payload", _XSS_PAYLOADS)
def test_oracle_strips_xss_payload(payload) -> None:
    assert payload not in h.SanitizingRenderer().render(payload), payload


_SAFE_SNIPPETS = [
    ("<b>hello</b>", "hello"), ("<i>world</i>", "world"),
    ("<a href='/x'>link</a>", "link"), ("<p>para</p>", "para"),
    ("<strong>bold</strong>", "bold"),
]


@pytest.mark.parametrize("snippet,text", _SAFE_SNIPPETS)
def test_oracle_preserves_inner_text(snippet, text) -> None:
    assert text in h.SanitizingRenderer().render(snippet), snippet


# === our own / batch 6 (original; reasoned vs nh3.clean defaults) ===
# Knox (absurd/sw) + math: nh3's default allowlist neutralizes more than <script> --
# <img onerror>, <svg onload>, <iframe> all lose their live tag form (escaped or stripped),
# while benign inline markup keeps its text.
def test_oracle_neutralizes_multiple_xss_vectors() -> None:
    vectors = ["<img src=x onerror=alert(1)>", "<svg onload=alert(1)>",
               "<iframe src=javascript:alert(1)>", "<script>alert(1)</script>"]
    for v in vectors:
        out = h.SanitizingRenderer().render(v)
        assert "<img" not in out and "<svg" not in out
        assert "<iframe" not in out and "<script>" not in out
    assert "hi" in h.SanitizingRenderer().render("<b>hi</b>")
