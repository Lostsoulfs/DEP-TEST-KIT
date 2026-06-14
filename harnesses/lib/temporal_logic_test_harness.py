#!/usr/bin/env python3
"""Token-expiry boundary harness (time-machine).

WHY:   Expiry checks are a classic off-by-one: is a token valid *at* its expiry
       instant, or only strictly before it? `<=` vs `<` is a one-character bug that
       leaves a credential live for one extra tick. You cannot test it with the wall
       clock — you can almost never observe `now == expiry` exactly — so the bug
       hides forever. time-machine pins the clock to the precise expiry instant,
       making the boundary observable and the bug deterministic.

HOW:   `is_valid_oracle` treats a token as valid only while `now < expiry`, so at the
       exact expiry instant it is already expired. `is_valid_buggy` uses `now <=
       expiry`, reporting the token still valid at that instant. The harness travels
       the clock to `EXPIRY` and asserts the check reports the token expired.

WHERE: lib/ — dependency-backed (time-machine) but fully in-process, no services.
       Adds `time-machine` to the `lib` extra. (time-machine is CPython 3.10+.)

Self-test:
  python harnesses/lib/temporal_logic_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from typing import Callable

import time_machine

EXPIRY = dt.datetime(2030, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc)
Check = Callable[[dt.datetime], bool]


def _now() -> dt.datetime:
    return dt.datetime.now(tz=dt.timezone.utc)


# --- ORACLE: valid strictly before expiry ---------------------------------------
def is_valid_oracle(expiry: dt.datetime) -> bool:
    return _now() < expiry


# --- BUGGY: off-by-one — valid through the expiry instant ------------------------
def is_valid_buggy(expiry: dt.datetime) -> bool:
    return _now() <= expiry


def expires_at_boundary(is_valid: Check) -> bool:
    """Freeze the clock at the exact expiry instant. Return True if `is_valid`
    correctly reports the token as expired (False) at that instant."""
    with time_machine.travel(EXPIRY, tick=False):
        return is_valid(EXPIRY) is False


def _valid_before_expiry(is_valid: Check) -> bool:
    """Sanity: a token must read as valid one second before expiry (both impls)."""
    with time_machine.travel(EXPIRY - dt.timedelta(seconds=1), tick=False):
        return is_valid(EXPIRY) is True


def run_self_test() -> int:
    failures = 0
    # Both impls must agree away from the boundary — the bug is *only* at the edge.
    if not (_valid_before_expiry(is_valid_oracle) and _valid_before_expiry(is_valid_buggy)):
        failures += 1
        print("FAIL: a token read as invalid one second before expiry", file=sys.stderr)
    if not expires_at_boundary(is_valid_oracle):
        failures += 1
        print("FAIL: oracle did not expire the token at the boundary", file=sys.stderr)
    if expires_at_boundary(is_valid_buggy):
        failures += 1
        print("FAIL: buggy off-by-one expiry was NOT caught at the boundary", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (oracle expires at the instant; off-by-one caught at boundary)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Token-expiry boundary harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
