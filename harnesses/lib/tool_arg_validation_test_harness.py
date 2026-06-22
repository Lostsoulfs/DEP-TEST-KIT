#!/usr/bin/env python3
"""Agent tool-argument validation harness (pydantic).

OWASP Top 10 for Agentic Applications 2026 -- ASI02 Tool Misuse & Exploitation.

WHY: The 2026 lesson from the Amazon Q incident: attackers don't smuggle in a new tool,
they bend a LEGITIMATE tool with hostile arguments. If an agent dispatches tool calls with
un-validated arguments, a negative/oversized amount, a path-traversal target, or an extra
privileged field (mass assignment) reaches the tool. A test that calls the tool with sane
arguments passes; only schema validation at the tool boundary catches the hostile ones.
pydantic is the real validator -- it enforces types, ranges, formats, AND rejects unexpected
fields (`extra="forbid"`).

HOW: `ValidatingDispatcher` is the ORACLE -- it parses raw tool args through a pydantic model
that bounds the amount, format-checks the account, and forbids extra fields; invalid args
raise before dispatch. `RawDispatcher` is the planted defect -- it reads the raw dict and
dispatches unchecked. `accepts_malicious_args` submits a negative amount, a traversal target,
and an injected `is_admin` field: the oracle rejects, the raw dispatcher accepts.

WHERE: lib/ -- in-process, deterministic. Adds `pydantic` to the `ai` extra (already in the repo).

Self-test:
    python harnesses/lib/tool_arg_validation_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import re
import sys
from typing import Callable

from pydantic import BaseModel, ConfigDict, field_validator

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["accepts_malicious_args"]

DOSSIER = {
    "name": "tool_arg_validation",
    "path": "harnesses/lib/tool_arg_validation_test_harness.py",
    "flavor": "lib",
    "dependency": "pydantic",
    "standard": "OWASP Top 10 for Agentic Applications 2026 — ASI02 Tool Misuse & Exploitation",
    "failure_class": (
        "A legitimate tool dispatched with hostile args (bad range/format, mass-assignment)"
    ),
    "oracle": (
        "ValidatingDispatcher.dispatch — pydantic model bounds/format-checks args, forbids extra"
    ),
    "buggy": "RawDispatcher.dispatch — dispatches the raw arg dict unchecked",
    "planted_mutant": "{amount:-999, to_account:'../../etc/passwd', is_admin:True}; oracle rejects",
    "proof_file": "tests/lib/test_tool_arg_validation_proof.py",
    "vacuity_targets": ["accepts_malicious_args"],
    "commands": ["python harnesses/lib/tool_arg_validation_test_harness.py --self-test"],
    "known_limits": "validates the args schema; does not model tool-chaining / side-effect policy",
    "related": ["agent_capability_allowlist (ASI03)", "schema_validation (lib)"],
}


class TransferArgs(BaseModel):
    """The tool's argument contract."""

    model_config = ConfigDict(extra="forbid")  # reject injected/extra fields (mass assignment)

    amount: int
    to_account: str

    @field_validator("amount")
    @classmethod
    def _bounded(cls, v: int) -> int:
        if v <= 0 or v > 1_000_000:
            raise ValueError("amount out of allowed range")
        return v

    @field_validator("to_account")
    @classmethod
    def _account_format(cls, v: str) -> str:
        if not re.fullmatch(r"acct-\d{6}", v):
            raise ValueError("account must match acct-NNNNNN")
        return v


class ValidatingDispatcher:
    """ORACLE: validate args through the schema before dispatch."""

    def dispatch(self, raw: dict) -> dict:
        args = TransferArgs(**raw)  # raises on invalid / extra fields
        return {"amount": args.amount, "to": args.to_account}


class RawDispatcher:
    """BUGGY: dispatch the raw argument dict unchecked."""

    def dispatch(self, raw: dict) -> dict:
        return {"amount": raw["amount"], "to": raw["to_account"]}  # BUG: no validation


def dispatches_valid_args(make_dispatcher: Callable[[], object]) -> bool:
    try:
        return make_dispatcher().dispatch({"amount": 100, "to_account": "acct-123456"})["amount"] == 100
    except Exception:
        return False


def accepts_malicious_args(make_dispatcher: Callable[[], object]) -> bool:
    """True == hostile args were dispatched (the bug); False == rejected by validation."""
    hostile = {"amount": -999, "to_account": "../../etc/passwd", "is_admin": True}
    try:
        make_dispatcher().dispatch(hostile)
        return True   # dispatched a destructive/extra-field tool call
    except Exception:
        return False  # validation rejected it


def run_self_test() -> int:
    failures = 0
    if not dispatches_valid_args(ValidatingDispatcher):
        failures += 1
        print("FAIL: oracle rejected a well-formed tool call", file=sys.stderr)
    if accepts_malicious_args(ValidatingDispatcher):
        failures += 1
        print("FAIL: oracle dispatched hostile arguments", file=sys.stderr)
    if not accepts_malicious_args(RawDispatcher):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: raw dispatcher was NOT caught dispatching hostile args", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (schema rejects hostile tool args; raw dispatcher caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Agent tool-argument validation harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
