#!/usr/bin/env python3
"""Agent expression-evaluation sandbox harness (simpleeval).

OWASP Top 10 for Agentic Applications 2026 -- ASI05 Unexpected Code Execution.

WHY: Agents routinely evaluate expressions they assemble from tool output or user text
("compute 2 + 3 * 4"). Reaching for `eval()` turns that into remote code execution: the
classic AutoGPT-style escape `().__class__.__bases__[0].__subclasses__()...` walks from a
literal to arbitrary objects. A test that checks "does `2+3*4` return 14?" passes for BOTH
`eval()` and a real sandbox -- the danger only shows on a hostile expression. A real
sandboxing dependency (simpleeval) refuses attribute access; `eval()` happily evaluates it.

HOW: `SafeEvaluator` is the ORACLE -- `simpleeval.simple_eval` (no attribute access, no
builtins, no calls by default). `UnsafeEvaluator` is the planted defect -- `eval()`.
`executes_payload` feeds the attribute-traversal probe and returns True if the evaluator
evaluated it without refusing: the oracle raises (sandboxed), the buggy evaluator returns a
value (escape reachable).

WHERE: ai/ -- in-process, deterministic. Adds `simpleeval` to the `ai` extra.

Self-test:
    python harnesses/ai/agent_safe_eval_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys

from simpleeval import simple_eval

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["executes_payload"]

DOSSIER = {
    "name": "agent_safe_eval",
    "path": "harnesses/ai/agent_safe_eval_test_harness.py",
    "flavor": "ai",
    "dependency": "simpleeval",
    "standard": "OWASP Top 10 for Agentic Applications 2026 — ASI05 Unexpected Code Execution",
    "failure_class": "Agent-controlled expression reaches eval() -> sandbox escape / RCE",
    "oracle": "SafeEvaluator.eval — simpleeval.simple_eval (no attribute/builtin access)",
    "buggy": "UnsafeEvaluator.eval — Python eval()",
    "planted_mutant": "evaluate '().__class__.__bases__'; buggy evaluates it, oracle refuses",
    "proof_file": "tests/ai/test_agent_safe_eval_proof.py",
    "vacuity_targets": ["executes_payload"],
    "commands": ["python harnesses/ai/agent_safe_eval_test_harness.py --self-test"],
    "known_limits": (
        "probes attribute-traversal escapes; a full eval policy review is still required"
    ),
    "related": ["secure_codegen_eval (CWE-95 rule)", "agent_tool_manifest (ASI04)"],
}

# An attribute-traversal probe: harmless to evaluate (returns a tuple), but a real
# sandbox must REFUSE it because it is the first hop of a classic eval escape.
_ESCAPE_PROBE = "().__class__.__bases__"


class SafeEvaluator:
    """ORACLE: a real expression sandbox that forbids attribute access."""

    def eval(self, expr: str):
        return simple_eval(expr)


class UnsafeEvaluator:
    """BUGGY: raw eval() -- evaluates the escape probe."""

    def eval(self, expr: str):
        return eval(expr)  # noqa: S307 -- the intentional planted defect


def evaluates_safe_math(make_evaluator) -> bool:
    """A benign arithmetic expression must evaluate correctly for either evaluator."""
    try:
        return make_evaluator().eval("2 + 3 * 4") == 14
    except Exception:
        return False


def executes_payload(make_evaluator) -> bool:
    """True == the evaluator evaluated the attribute-traversal escape probe (unsafe);
    False == it refused (sandboxed)."""
    try:
        make_evaluator().eval(_ESCAPE_PROBE)
        return True
    except Exception:
        return False


def run_self_test() -> int:
    failures = 0
    if not evaluates_safe_math(SafeEvaluator):
        failures += 1
        print("FAIL: oracle could not evaluate benign arithmetic", file=sys.stderr)
    if executes_payload(SafeEvaluator):
        failures += 1
        print("FAIL: oracle evaluated the sandbox-escape probe", file=sys.stderr)
    if not executes_payload(UnsafeEvaluator):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: eval()-based evaluator was NOT caught executing the probe", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (sandbox refuses the escape probe; eval() evaluator caught executing it)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Agent expression-evaluation sandbox harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
