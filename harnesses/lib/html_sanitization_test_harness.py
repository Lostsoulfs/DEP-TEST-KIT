#!/usr/bin/env python3
"""HTML-sanitization harness (nh3): strip active markup from user-supplied HTML.

OWASP Top 10:2025 A03 Cross-Site Scripting - stored XSS (CWE-79).

WHY: Distinct from template auto-escaping (which escapes a plain value): here the app accepts
RICH user HTML (comments, profiles) and must allow safe tags while stripping `<script>`, event
handlers, and `javascript:` URLs. Storing the raw HTML and serving it later is stored XSS.

HOW: `SanitizingRenderer` is the ORACLE -- `nh3.clean` with a benign tag allow-list, which
strips disallowed tags so `<script>` never survives. `RawHtmlRenderer` is the planted defect --
it stores the HTML verbatim. `reflects_active_script` sanitizes markup containing a script tag
and reports whether a live `<script>` survived.

WHERE: lib/ -- dependency-backed (`nh3`, the maintained Rust/ammonia sanitizer; bleach is EOL),
in-process.

Self-test:
    python harnesses/lib/html_sanitization_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

import nh3

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["reflects_active_script"]

DOSSIER = {
    "name": "html_sanitization",
    "path": "harnesses/lib/html_sanitization_test_harness.py",
    "flavor": "lib",
    "dependency": "nh3",
    "standard": "OWASP Top 10:2025 A03 Cross-Site Scripting - stored XSS (CWE-79)",
    "failure_class": "Storing user HTML with a live <script> tag intact (stored XSS)",
    "oracle": "SanitizingRenderer.render - nh3.clean strips disallowed tags (benign allow-list)",
    "buggy": "RawHtmlRenderer.render - store the HTML verbatim",
    "planted_mutant": "user HTML '<b>hi</b><script>steal()</script>' keeps the script tag",
    "proof_file": "tests/lib/test_html_sanitization_proof.py",
    "vacuity_targets": ["reflects_active_script"],
    "commands": ["python harnesses/lib/html_sanitization_test_harness.py --self-test"],
    "known_limits": "tag/attribute sanitization; not CSP or DOM-XSS sink analysis",
    "related": ["jinja_autoescape_xss", "advanced_injection"],
}

_PAYLOAD = "<b>hi</b><script>steal()</script>"

# Benign formatting tags only -- excludes script/img/svg/iframe/etc. so active markup is stripped.
_ALLOWED_TAGS = {"a", "b", "i", "em", "strong", "code", "blockquote", "abbr", "p", "ul", "ol", "li"}


class SanitizingRenderer:
    """ORACLE: nh3.clean strips disallowed tags (keeps a benign allow-list)."""

    def render(self, user_html: str) -> str:
        return nh3.clean(user_html, tags=_ALLOWED_TAGS)


class RawHtmlRenderer:
    """BUGGY: store the user HTML verbatim."""

    def render(self, user_html: str) -> str:
        return user_html  # BUG: stored XSS


def renders_safe_markup(make_renderer: Callable[[], object]) -> bool:
    return "hi" in make_renderer().render("<b>hi</b>")


def reflects_active_script(make_renderer: Callable[[], object]) -> bool:
    """True == a live <script> tag survived sanitization (stored XSS)."""
    return "<script>" in make_renderer().render(_PAYLOAD)


def run_self_test() -> int:
    failures = 0
    if not renders_safe_markup(SanitizingRenderer):
        failures += 1
        print("FAIL: oracle dropped benign markup entirely", file=sys.stderr)
    if reflects_active_script(SanitizingRenderer):
        failures += 1
        print("FAIL: oracle let a live script tag through", file=sys.stderr)
    if not reflects_active_script(RawHtmlRenderer):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: raw HTML renderer stored XSS was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (nh3 strips the script tag; raw renderer stores it -- caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HTML-sanitization harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
