#!/usr/bin/env python3
"""gate_canary.py — do DEP-TEST-KIT's anti-bug gates still BITE?

Vacuous green is the failure class the gates themselves cannot see: a gate that
passes while inert — a secret regex quietly neutered so it matches nothing, or a
meta-gate that no longer notices a harness with no teeth. Every such gate was proven
to bite once, by hand, when it was built. This script makes that a STANDING check:
each gate is run against a KNOWN-BAD fixture and the canary FAILS unless the gate
fails too.

Principle (ported from the Codex slot repo that pioneered this): run the REAL gate
code on fresh known-bad input. A canary that re-implements or softens the gate
proves nothing, so this drives the live ``scan_line`` and the live
``vacuity_gate`` — never a private copy.

Covered:
  - secret scanner  the live discrete patterns and GENERIC_SECRET_ASSIGNMENT must
                    still flag known secrets — including the compound-keyword forms
                    (client_secret / access_token) the old ``\\b`` regex missed —
                    while leaving a clean line alone.
  - vacuity gate    the vacuous-green meta-gate's own ``--self-test`` must still
                    classify a real fixture as TEETH and a deliberately-vacuous one
                    as VACUOUS (exit 0). If it ever stops detecting the vacuous
                    fixture, the gate that guards every harness has itself gone soft.

Self-canarying elsewhere (deliberately not duplicated here): every lib/ai harness
proves its own teeth via ``run_self_test()`` (``make selftest``); the vacuity gate
runs over the real harnesses as its own required job; ``make mutation`` deepens it.
This script is the meta-check that the two rot-prone gates above still bite.

Exit: 0 = every gate bit on known-bad input; 1 = a gate has gone soft — fix the
GATE (or the fixture, if the gate legitimately changed), not this script.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Run from anywhere: put the repo root on sys.path so the REAL gate code imports.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools import scan_staged, vacuity_gate  # noqa: E402  (after sys.path bootstrap)

_results: list[tuple[str, bool, str]] = []


def record(name: str, passed: bool, note: str = "") -> bool:
    """Print and collect one canary result. ``passed`` True = the gate bit."""
    _results.append((name, passed, note))
    tail = f" - {note}" if note else ""
    print(f"{'PASS' if passed else 'FAIL'}  | {name}{tail}")
    return passed


# ---------------------------------------------------------------------------
# 1. secret scanner — known secrets must be flagged (the scanner is secret-only
#    here, so any hit is a block); the compound-keyword forms the old \b regex
#    missed must bite; a clean line must not. scan_line is called through the
#    module so a softened gate is observable.
# ---------------------------------------------------------------------------
def canary_scanner() -> None:
    # Built from parts so this source never trips the repo's own secret gate.
    block_fixtures = {
        "AWS access key": "AKIA" + "IOSFODNN7EXAMPLE",
        "GitHub token": "ghp_" + ("a" * 36),
        "client_secret assignment": "client_secret" + " = " + "'" + ("A" * 24) + "'",
        "access_token assignment": "access_token" + " = " + ("B" * 32),
    }
    for label, line in block_fixtures.items():
        hits = scan_staged.scan_line(line)
        record(f"scanner: BITES on {label}", bool(hits), f"hits={hits}")

    clean = "a normal line of prose about tokens and secrets in passing"
    record("scanner: clean line is not flagged", not scan_staged.scan_line(clean))


# ---------------------------------------------------------------------------
# 2. vacuity gate — the vacuous-green meta-gate's own --self-test must still
#    classify a real fixture TEETH and a vacuous one VACUOUS. Run the REAL gate
#    entrypoint (vacuity_gate.main), not a private copy.
# ---------------------------------------------------------------------------
def canary_vacuity() -> None:
    code = vacuity_gate.main(["--self-test"])
    record("vacuity-gate: --self-test still detects the vacuous fixture",
           code == 0, f"exit {code}")


def run() -> int:
    """Run every canary and return the process exit code (0 green / 1 a gate soft)."""
    _results.clear()
    print("GATE CANARY - proving every anti-bug gate still fails on known-bad input\n")
    canary_scanner()
    canary_vacuity()
    failed = [name for name, ok, _ in _results if not ok]
    print(f"\n--- SUMMARY: {len(_results) - len(failed)}/{len(_results)} canaries pass ---")
    if failed:
        print("A gate has gone soft (vacuous green) - fix the GATE, not this script:")
        for name in failed:
            print(f"- {name}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
