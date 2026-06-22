"""Oracle + CLI-contract test for jinja_autoescape_xss (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_jinja_autoescape_xss_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import jinja_autoescape_xss_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.renders_plain_text(h.AutoescapeRenderer) is True


import pytest  # noqa: E402

# XSS corpus (PayloadsAllTheThings; OWASP XSS Filter-Evasion; PortSwigger 2026 cheat sheet)
_XSS_PAYLOADS = [
    "<script>alert(1)</script>", "<img src=x onerror=alert(1)>", "<svg onload=alert(1)>",
    '"><script>alert(1)</script>', "<body onload=alert(1)>", "<iframe src=javascript:alert(1)>",
    '<a href="javascript:alert(1)">x</a>', "<details open ontoggle=alert(1)>",
    "<input autofocus onfocus=alert(1)>", "<marquee onstart=alert(1)>", "<ScRiPt>alert(1)</ScRiPt>",
]


@pytest.mark.parametrize("payload", _XSS_PAYLOADS)
def test_oracle_escapes_xss_payload(payload) -> None:
    assert payload not in h.AutoescapeRenderer().render(payload), payload


_SAFE_TEXTS = ["Hello World", "Café résumé", "price 5 and 6", "user_name-123"]


@pytest.mark.parametrize("text", _SAFE_TEXTS)
def test_oracle_preserves_safe_text(text) -> None:
    assert h.AutoescapeRenderer().render(text) == f"<div>{text}</div>", text


# === our own / batch 5 (original; math bench) ===
# Constantin (surreal/sw) + math: autoescape encodes every HTML metacharacter -- the five that
# matter (< > & " ') each become an entity, so injected markup cannot re-open as a tag.
def test_oracle_escapes_each_html_metacharacter() -> None:
    out = h.AutoescapeRenderer().render("a<b>&\"'c")
    assert "&lt;" in out and "&gt;" in out and "&amp;" in out
    assert "<b>" not in out
    assert "<script>" not in h.AutoescapeRenderer().render("<script>alert(1)</script>")
