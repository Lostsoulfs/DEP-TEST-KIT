#!/usr/bin/env python3
"""Jinja2 auto-escaping (XSS) harness: escape user data in rendered HTML output.

OWASP Top 10:2025 A03 (XSS, folded into Injection) -- CWE-79.

WHY: Distinct from SSTI (template-source control): here the template is trusted but renders
untrusted DATA into HTML. With `autoescape=False`, a value like `<script>alert(1)</script>`
is reflected verbatim and executes in the victim's browser. Auto-escaping converts it to inert
`&lt;script&gt;`.

HOW: `AutoescapeRenderer` is the ORACLE -- `Environment(autoescape=True)`. `UnescapedRenderer`
is the planted defect -- `autoescape=False`. `reflects_unescaped_script` renders a script
payload as data and reports whether a live `<script>` tag survived into the output.

WHERE: lib/ -- dependency-backed (`jinja2`), in-process.

Self-test:
    python harnesses/lib/jinja_autoescape_xss_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

from jinja2 import Environment

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["reflects_unescaped_script"]

DOSSIER = {
    "name": "jinja_autoescape_xss",
    "path": "harnesses/lib/jinja_autoescape_xss_test_harness.py",
    "flavor": "lib",
    "dependency": "jinja2",
    "standard": "OWASP Top 10:2025 A03 Cross-Site Scripting (CWE-79)",
    "failure_class": "Rendering untrusted data into HTML without escaping (reflected XSS)",
    "oracle": "AutoescapeRenderer - Environment(autoescape=True) escapes < > & \" in data",
    "buggy": "UnescapedRenderer - Environment(autoescape=False)",
    "planted_mutant": "render a <script> payload as data; the unescaped env reflects it live",
    "proof_file": "tests/lib/test_jinja_autoescape_xss_proof.py",
    "vacuity_targets": ["reflects_unescaped_script"],
    "commands": ["python harnesses/lib/jinja_autoescape_xss_test_harness.py --self-test"],
    "known_limits": "HTML-context auto-escaping; not JS/CSS/URL-context or DOM XSS",
    "related": ["jinja_ssti_sandbox", "advanced_injection"],
}

_PAYLOAD = "<script>alert(1)</script>"


class AutoescapeRenderer:
    """ORACLE: auto-escaping environment."""

    def __init__(self) -> None:
        self.env = Environment(autoescape=True)

    def render(self, user: str) -> str:
        return self.env.from_string("<div>{{ user }}</div>").render(user=user)


class UnescapedRenderer:
    """BUGGY: no auto-escaping."""

    def __init__(self) -> None:
        self.env = Environment(autoescape=False)

    def render(self, user: str) -> str:
        return self.env.from_string("<div>{{ user }}</div>").render(user=user)


def renders_plain_text(make_renderer: Callable[[], object]) -> bool:
    return "hello" in make_renderer().render("hello")


def reflects_unescaped_script(make_renderer: Callable[[], object]) -> bool:
    """True == a live <script> tag survived into the HTML output (XSS)."""
    return "<script>" in make_renderer().render(_PAYLOAD)


def run_self_test() -> int:
    failures = 0
    if not renders_plain_text(AutoescapeRenderer):
        failures += 1
        print("FAIL: oracle failed to render benign text", file=sys.stderr)
    if reflects_unescaped_script(AutoescapeRenderer):
        failures += 1
        print("FAIL: oracle reflected an unescaped script tag", file=sys.stderr)
    if not reflects_unescaped_script(UnescapedRenderer):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: unescaped renderer XSS was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (auto-escaping neutralizes the script tag; unescaped env reflects it)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Jinja2 auto-escaping XSS harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
