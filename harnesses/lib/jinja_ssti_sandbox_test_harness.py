#!/usr/bin/env python3
"""Jinja2 SSTI sandbox harness (jinja2).

OWASP Top 10:2025 A05 Injection (Server-Side Template Injection), a live 2026 RCE class:
SGLang (Apr 2026) and Jupyter Enterprise Gateway (CVE-2026-44181) shipped a plain
`jinja2.Environment()` where attacker-influenced template text reaches the renderer, and the
classic `{{ ().__class__.__bases__ ... }}` escape chain executes Python.

WHY: A regex that looks for `{{ }}` only guesses; and a test that renders `Hello {{ name }}`
passes for BOTH a sandboxed and an unsandboxed environment. The danger only shows when the
template performs ATTRIBUTE TRAVERSAL -- the real template engine either refuses it
(SandboxedEnvironment) or evaluates it (plain Environment). Only running the real renderer
proves which.

HOW: `SandboxedRenderer` is the ORACLE -- `jinja2.sandbox.SandboxedEnvironment`, which raises
`SecurityError` on access to unsafe attributes. `UnsafeRenderer` is the planted defect -- a
plain `jinja2.Environment` (the SGLang/Jupyter bug). `executes_escape` renders the
attribute-traversal probe: the oracle raises, the unsafe renderer evaluates it.

WHERE: lib/ -- in-process, deterministic. Adds `jinja2` to the matching extra.

Self-test:
    python harnesses/lib/jinja_ssti_sandbox_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys

from jinja2 import Environment
from jinja2.sandbox import SandboxedEnvironment

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["executes_escape"]

DOSSIER = {
    "name": "jinja_ssti_sandbox",
    "path": "harnesses/lib/jinja_ssti_sandbox_test_harness.py",
    "flavor": "lib",
    "dependency": "jinja2",
    "standard": "OWASP Top 10:2025 A05 Injection (SSTI) — SGLang 2026, CVE-2026-44181",
    "failure_class": (
        "Attacker-influenced template rendered by an unsandboxed Jinja2 Environment -> RCE"
    ),
    "oracle": (
        "SandboxedRenderer — jinja2.sandbox.SandboxedEnvironment (raises SecurityError on escape)"
    ),
    "buggy": "UnsafeRenderer — plain jinja2.Environment()",
    "planted_mutant": (
        "render '{{ ().__class__.__bases__ }}'; unsafe renderer evaluates it, sandbox refuses"
    ),
    "proof_file": "tests/lib/test_jinja_ssti_sandbox_proof.py",
    "vacuity_targets": ["executes_escape"],
    "commands": ["python harnesses/lib/jinja_ssti_sandbox_test_harness.py --self-test"],
    "known_limits": (
        "probes the attribute-traversal escape; full SSTI review still needs input-source analysis"
    ),
    "related": ["advanced_injection (stdlib SSTI regex)", "agent_safe_eval (ASI05)"],
}

# Attribute traversal: the first hop of the classic Jinja2 sandbox-escape chain.
_ESCAPE_PROBE = "{{ ().__class__.__bases__ }}"


class SandboxedRenderer:
    """ORACLE: SandboxedEnvironment refuses unsafe attribute access."""

    def __init__(self) -> None:
        self.env = SandboxedEnvironment()

    def render(self, template: str, **ctx) -> str:
        return self.env.from_string(template).render(**ctx)


class UnsafeRenderer:
    """BUGGY: a plain Environment evaluates the escape chain."""

    def __init__(self) -> None:
        self.env = Environment()  # the SGLang / Jupyter 2026 misconfiguration

    def render(self, template: str, **ctx) -> str:
        return self.env.from_string(template).render(**ctx)


def renders_benign(make_renderer) -> bool:
    try:
        return make_renderer().render("Hello {{ name }}", name="Alice") == "Hello Alice"
    except Exception:
        return False


def executes_escape(make_renderer) -> bool:
    """True == the renderer evaluated the attribute-traversal escape (SSTI reachable);
    False == it refused (sandboxed)."""
    try:
        make_renderer().render(_ESCAPE_PROBE)
        return True
    except Exception:
        return False


def run_self_test() -> int:
    failures = 0
    if not renders_benign(SandboxedRenderer):
        failures += 1
        print("FAIL: oracle could not render a benign template", file=sys.stderr)
    if executes_escape(SandboxedRenderer):
        failures += 1
        print("FAIL: oracle evaluated the SSTI escape probe", file=sys.stderr)
    if not executes_escape(UnsafeRenderer):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: plain Environment was NOT caught evaluating the escape probe", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (sandbox refuses the SSTI escape; plain Environment caught evaluating it)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Jinja2 SSTI sandbox harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
