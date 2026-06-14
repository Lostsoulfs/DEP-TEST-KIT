#!/usr/bin/env python3
"""Agentic property-based testing harness (Hypothesis).

WHY:   The Anthropic "property-based testing with Claude" pattern has an agent read a
       function's name, docstring, and types, INFER the properties that must hold, then
       write Hypothesis tests for them. The bugs it finds are ones no example test was
       written for. This harness embodies that pattern deterministically: it pins the
       properties an agent would infer for `ensure_prefix` and proves Hypothesis
       falsifies an implementation that violates one of them.

HOW:   `ensure_prefix(s)` adds a prefix only if absent. From the NAME alone an agent
       infers two properties: (P1) idempotence — `f(f(x)) == f(x)`; (P2) postcondition
       — `f(x)` starts with the prefix. The oracle satisfies both. `buggy_ensure_prefix`
       always prepends, so it still satisfies P2 but VIOLATES P1
       (`f(f("a")) == "ID_ID_a" != "ID_a"`). Hypothesis finds a counterexample; a single
       example like `"a"` would too, but the point is the agent inferred P1 without a
       human writing that case.

WHERE: ai/ — dependency-backed (hypothesis), fully in-process, deterministic. No live
       LLM and no API key: the "agent" step (property inference) is encoded as the
       PROPERTIES dict, so the lane stays CI-safe. Adds `hypothesis` to the `ai` extra.

Self-test:
  python harnesses/ai/agentic_pbt_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

from hypothesis import given, settings
from hypothesis import strategies as st

PREFIX = "ID_"


# --- ORACLE: prefix only when absent (idempotent) -------------------------------
def ensure_prefix(s: str, prefix: str = PREFIX) -> str:
    return s if s.startswith(prefix) else prefix + s


# --- BUGGY: always prepends — satisfies the postcondition, breaks idempotence ----
def buggy_ensure_prefix(s: str, prefix: str = PREFIX) -> str:
    return prefix + s


# The properties an agent infers for `ensure_prefix` from its name/contract. Each is a
# predicate over (fn, input) that must hold for every input.
PROPERTIES: dict[str, Callable[[Callable[[str], str], str], bool]] = {
    "postcondition: output starts with prefix": lambda fn, s: fn(s).startswith(PREFIX),
    "idempotence: f(f(x)) == f(x)": lambda fn, s: fn(fn(s)) == fn(s),
}


def _make_check(fn: Callable[[str], str], prop: Callable[[Callable[[str], str], str], bool]):
    @settings(max_examples=200)
    @given(st.text())
    def check(s: str) -> None:
        if not prop(fn, s):
            raise AssertionError(s)

    return check


def falsified_property(fn: Callable[[str], str]) -> str | None:
    """Run every inferred property against `fn` with Hypothesis. Return the name of the
    first property Hypothesis falsifies, or None if all hold."""
    for name, prop in PROPERTIES.items():
        try:
            _make_check(fn, prop)()
        except AssertionError:
            return name
    return None


def run_self_test() -> int:
    failures = 0
    oracle_bad = falsified_property(ensure_prefix)
    if oracle_bad is not None:
        failures += 1
        print(f"FAIL: oracle falsified an inferred property: {oracle_bad}", file=sys.stderr)
    buggy_bad = falsified_property(buggy_ensure_prefix)
    if buggy_bad is None:
        failures += 1
        print("FAIL: buggy impl satisfied all inferred properties (not caught)", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print(f"self-test: OK (oracle holds; buggy caught on -> {buggy_bad})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Agentic property-based testing harness")
    parser.add_argument("--self-test", action="store_true")
    parser.parse_args(argv)
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
