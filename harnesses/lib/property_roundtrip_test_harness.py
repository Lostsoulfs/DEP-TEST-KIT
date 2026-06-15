#!/usr/bin/env python3
"""Property-based round-trip test harness (Hypothesis).

WHY:   Example-based tests only check the inputs a human imagined. An encode→decode
       round-trip that "works" on the three strings in the test file can still be
       wrong for an empty run, a count of exactly 1, or a repeated character at a
       boundary. Hypothesis generates thousands of inputs and, on failure, SHRINKS
       to the minimal counterexample — surfacing the boundary bug a fixed example
       set never would.

HOW:   `rle_encode`/`rle_decode` implement run-length coding. The oracle invariant
       is `rle_decode(rle_encode(s)) == s` for ALL text. `buggy_rle_decode` drops
       runs whose count is 1 — a defect that passes naive examples like "aaa" but
       fails on "ab". The harness proves Hypothesis catches it and shrinks it to a
       1-2 character counterexample.

WHERE: lib/ — dependency-backed (hypothesis) but fully in-process, no services.
       Adds `hypothesis` to the `lib` extra in pyproject.toml.

Self-test:
  python harnesses/lib/property_roundtrip_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

from hypothesis import given, settings
from hypothesis import strategies as st

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["rle_decode"]


# --- ORACLE ---------------------------------------------------------------------
def rle_encode(text: str) -> list[tuple[str, int]]:
    runs: list[tuple[str, int]] = []
    for ch in text:
        if runs and runs[-1][0] == ch:
            char, count = runs[-1]
            runs[-1] = (char, count + 1)
        else:
            runs.append((ch, 1))
    return runs


def rle_decode(runs: list[tuple[str, int]]) -> str:
    return "".join(char * count for char, count in runs)


# --- BUGGY: drops single-character runs (count == 1) ----------------------------
def buggy_rle_decode(runs: list[tuple[str, int]]) -> str:
    return "".join(char * count for char, count in runs if count != 1)


def _roundtrip_property(decode: Callable[[list[tuple[str, int]]], str]):
    @settings(max_examples=300)
    @given(st.text())
    def prop(s: str) -> None:
        assert decode(rle_encode(s)) == s

    return prop


def find_roundtrip_counterexample(decode: Callable[[list[tuple[str, int]]], str]) -> bool:
    """Run the round-trip property against `decode`. Return True if Hypothesis
    falsifies it (i.e. the decoder is buggy), False if the property holds."""
    try:
        _roundtrip_property(decode)()
    except AssertionError:
        return True
    return False


def run_self_test() -> int:
    failures = 0
    if find_roundtrip_counterexample(rle_decode):
        failures += 1  # the correct decoder should hold
        print("FAIL: oracle round-trip falsified", file=sys.stderr)
    if not find_roundtrip_counterexample(buggy_rle_decode):
        failures += 1  # the planted bug must be caught — else vacuous green
        print("FAIL: buggy decoder was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (oracle holds; buggy decoder caught and shrunk by Hypothesis)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Property round-trip harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
