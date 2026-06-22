#!/usr/bin/env python3
"""LLM structured-output contract harness (jsonschema).

OWASP Top 10 for Agentic Applications 2026 -- ASI02 Tool Misuse (output side). 2026 guidance:
multi-step agents compound schema failures (a 12-span run at 5% per-step failure has a ~46%
chance of at least one bad span), and model "strict" flags don't guarantee compliance
(Claude's strict param is advisory) -- so tool-call output MUST be validated before it drives
an action.

WHY: An LLM emits a tool call as JSON (`{tool, amount, to, ...}`). If the executor trusts that
JSON, a hallucinated extra field, an out-of-range value, or a wrong type drives a real tool.
A test with a well-formed call passes whether or not the executor validates; only a malformed
output exposes the gap. This is the OUTPUT-side complement to `tool_arg_validation` (which
validates the same boundary from the schema's perspective via pydantic) -- here the contract
is an explicit JSON Schema applied to model output, the 2026 "cheapest fix for flaky agents".

HOW: `ValidatingExecutor` is the ORACLE -- it validates model output against a JSON Schema
(`additionalProperties: false`, bounded amount, account pattern) before acting; invalid output
raises. `TrustingExecutor` is the planted defect -- it acts on the raw output.
`executes_malformed_output` feeds a negative amount, a bad account, and an injected `role`
field: the oracle rejects, the trusting executor acts.

WHERE: lib/ -- in-process, deterministic. Adds `jsonschema` to the matching extra.

Self-test:
    python harnesses/lib/structured_output_contract_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

from jsonschema import validate

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["executes_malformed_output"]

DOSSIER = {
    "name": "structured_output_contract",
    "path": "harnesses/lib/structured_output_contract_test_harness.py",
    "flavor": "lib",
    "dependency": "jsonschema",
    "standard": "OWASP Agentic 2026 ASI02 (output side) — LLM structured-output validation",
    "failure_class": (
        "Acting on un-validated LLM tool-call output (bad range/type, hallucinated field)"
    ),
    "oracle": "ValidatingExecutor.execute — jsonschema.validate(output, TOOL_SCHEMA) before acting",
    "buggy": "TrustingExecutor.execute — act on the raw model output",
    "planted_mutant": (
        "{amount:-5, to:'../etc', role:'admin'}; oracle rejects, trusting executor acts"
    ),
    "proof_file": "tests/lib/test_structured_output_contract_proof.py",
    "vacuity_targets": ["executes_malformed_output"],
    "commands": ["python harnesses/lib/structured_output_contract_test_harness.py --self-test"],
    "known_limits": (
        "validates structure/format; semantic correctness of the call still needs policy"
    ),
    "related": ["tool_arg_validation (ASI02 input side)", "insecure_output_handling (LLM02)"],
}

TOOL_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["tool", "amount", "to"],
    "properties": {
        "tool": {"const": "transfer"},
        "amount": {"type": "integer", "minimum": 1, "maximum": 1_000_000},
        "to": {"type": "string", "pattern": r"^acct-\d{6}$"},
    },
}


class ValidatingExecutor:
    """ORACLE: validate model output against the tool schema before acting."""

    def execute(self, model_output: dict) -> dict:
        validate(instance=model_output, schema=TOOL_SCHEMA)  # raises ValidationError
        return {"ok": True, **model_output}


class TrustingExecutor:
    """BUGGY: act on the raw model output."""

    def execute(self, model_output: dict) -> dict:
        return {"ok": True, **model_output}  # BUG: no schema validation


def executes_valid_output(make_executor: Callable[[], object]) -> bool:
    try:
        return make_executor().execute({"tool": "transfer", "amount": 100, "to": "acct-123456"})["ok"] is True
    except Exception:
        return False


def executes_malformed_output(make_executor: Callable[[], object]) -> bool:
    """True == malformed model output was acted on (the bug); False == rejected by the schema."""
    malformed = {"tool": "transfer", "amount": -5, "to": "../etc/passwd", "role": "admin"}
    try:
        make_executor().execute(malformed)
        return True   # acted on out-of-range / bad-format / extra-field output
    except Exception:
        return False  # schema rejected it


def run_self_test() -> int:
    failures = 0
    if not executes_valid_output(ValidatingExecutor):
        failures += 1
        print("FAIL: oracle rejected a well-formed tool call", file=sys.stderr)
    if executes_malformed_output(ValidatingExecutor):
        failures += 1
        print("FAIL: oracle acted on malformed model output", file=sys.stderr)
    if not executes_malformed_output(TrustingExecutor):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: trusting executor was NOT caught acting on malformed output", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (schema rejects malformed model output; trusting executor caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LLM structured-output contract harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
