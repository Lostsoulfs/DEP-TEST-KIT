#!/usr/bin/env python3
"""Retry-policy correctness test harness (tenacity).

WHY: Retry logic is usually tested against a stub that succeeds on the first or
second try — which proves nothing about WHICH errors it retries. A policy that
retries on `Exception` will keep hammering a PERMANENT failure (a 400, a
validation error) that can never succeed: wasted calls, amplified load, and
slower failure (CWE-754 improper handling of exceptional conditions). The bug
only shows when the operation raises a non-retryable error.

HOW: `attempts_for_permanent(make_policy)` runs an operation that always raises
`PermanentError` under a tenacity policy and counts how many times it was
called. The ORACLE policy retries only `TransientError` (stop after 3), so a
permanent error is attempted exactly once. The BUGGY policy retries on
`Exception`, so the permanent error is attempted 3 times. `retries_permanent`
makes the difference a boolean the proof asserts.

WHERE: lib/ — dependency-backed (`tenacity`) but fully in-process, no service.
Adds `tenacity` to the `lib` extra in pyproject.toml.

Self-test:
    python harnesses/lib/retry_resilience_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

import tenacity


class TransientError(Exception):
    """A retryable, temporary failure (e.g. a 503 / timeout)."""


class PermanentError(Exception):
    """A non-retryable failure (e.g. a 400 / validation error)."""


MAX_ATTEMPTS = 3


def oracle_policy() -> tenacity.Retrying:
    """Retries ONLY transient errors, capped at MAX_ATTEMPTS."""
    return tenacity.Retrying(
        stop=tenacity.stop_after_attempt(MAX_ATTEMPTS),
        retry=tenacity.retry_if_exception_type(TransientError),
        reraise=True,
    )


def buggy_policy() -> tenacity.Retrying:
    """Plausible-but-wrong: retries EVERYTHING, including permanent errors."""
    return tenacity.Retrying(
        stop=tenacity.stop_after_attempt(MAX_ATTEMPTS),
        retry=tenacity.retry_if_exception_type(Exception),
        reraise=True,
    )


def attempts_for_permanent(make_policy: Callable[[], tenacity.Retrying]) -> int:
    """Count how many times an always-permanently-failing op is invoked."""
    calls = {"n": 0}

    def op() -> None:
        calls["n"] += 1
        raise PermanentError("never going to succeed")

    try:
        make_policy()(op)
    except Exception:
        pass
    return calls["n"]


def retries_permanent(make_policy: Callable[[], tenacity.Retrying]) -> bool:
    """True == the policy wastes retries on a permanent error (the bug)."""
    return attempts_for_permanent(make_policy) > 1


def run_self_test() -> int:
    failures = 0
    if retries_permanent(oracle_policy):
        failures += 1
        print("FAIL: oracle policy retried a permanent error", file=sys.stderr)
    if not retries_permanent(buggy_policy):
        failures += 1  # the planted bug must be caught — else vacuous green
        print("FAIL: buggy retry-everything policy was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (oracle retries only transient errors; retry-everything bug caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Retry-policy correctness harness")
    parser.add_argument("--self-test", action="store_true")
    parser.parse_args(argv)
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
