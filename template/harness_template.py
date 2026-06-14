#!/usr/bin/env python3
"""<ONE-LINE TITLE> test harness.

Copy this file to `harnesses/<lib|integration>/<name>_test_harness.py` and fill in
the three required sections below. Every harness in this repo must explain itself:

WHY:   The failure class this harness catches that the stdlib (and example-based
       tests) cannot. State the bug it exists to prevent, concretely.
HOW:   The mechanism — the dependency/service used, the oracle (the correct
       reference) and the intentional BUGGY implementation it proves it catches.
WHERE: Which flavor and why. `lib/` = dependency-backed but in-process (no
       services). `integration/` = needs a real ephemeral service (Docker).
       Name the dependency it adds to pyproject's matching extra.

Shape contract (so `green` always means something — no vacuous passes):
  - self-contained module; the only imports are stdlib + this harness's own
    declared dependency.
  - a deterministic ORACLE (the correct behavior) AND an intentional BUGGY impl.
  - a paired test  `tests/<flavor>/test_<name>_test_harness.py`
  - a proof test   `tests/<flavor>/test_<name>_proof.py` that asserts the BUGGY
    impl is caught and the good one passes — this is what stops a test from
    passing while inert.
  - a `run_self_test()` returning 0/1 and a `--self-test` CLI where the harness
    is in-process. Integration harnesses whose self-test needs Docker say so and
    defer to `pytest -m integration`.

Self-test:
  python harnesses/<flavor>/<name>_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys


# --- ORACLE: the correct reference behavior -------------------------------------
def reference(value: int) -> int:
    """The behavior under test, implemented correctly."""
    return abs(value)


# --- BUGGY: an intentional defect the harness must catch -------------------------
def buggy(value: int) -> int:
    """A plausible-but-wrong variant (drops the negative case)."""
    return value


def run_self_test() -> int:
    failures = 0
    for v in (-3, 0, 5):
        if reference(v) != abs(v):
            failures += 1
    # The harness must catch the planted bug, else it is vacuous.
    if buggy(-3) == abs(-3):
        failures += 1  # buggy impl was NOT caught — harness has no teeth
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
