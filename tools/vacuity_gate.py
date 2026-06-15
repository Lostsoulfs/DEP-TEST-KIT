#!/usr/bin/env python3
"""Vacuous-green meta-gate — neuter each harness's oracle and prove its self-test goes red.

A harness is "vacuous green" if its own self-test/proof can pass while the thing it tests is
broken. This gate makes that machine-checkable: for every lib/ai harness that declares a
``VACUITY_TARGETS`` list, it replaces those oracle symbols with an inert stand-in (a callable
returning a unique sentinel), re-runs the harness's ``run_self_test()`` in a subprocess, and
asserts the self-test now FAILS. If it still passes, the harness has no teeth.

This delivers the per-harness mutation runner ADR-0006 deferred, WITHOUT mutmut (which can't run
on native Windows and chokes on package-prefixed modules): a direct monkeypatch in a subprocess
sidesteps both. Integration harnesses are excluded — their self-tests defer to Docker, exactly
as ``make selftest`` excludes them.

Status semantics (per mapped harness):
  TEETH    control self-test is green AND the neutered self-test is red  -> good
  VACUOUS  control green but neutered self-test STILL green               -> blocking failure
  ERROR    control self-test is already red (broken harness)              -> blocking failure
  UNMAPPED no VACUITY_TARGETS declared                                    -> advisory only (rollout)

Usage:
  python tools/vacuity_gate.py            # gate all lib+ai harnesses
  python tools/vacuity_gate.py --self-test  # prove the gate itself on two fixtures
"""

from __future__ import annotations

import argparse
import contextlib
import importlib
import importlib.util
import io
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FLAVORS = ("lib", "ai")  # integration self-tests defer to Docker; excluded like `make selftest`

_SENTINEL = object()


class _Inert:
    """A drop-in oracle that does nothing useful — returns a sentinel for any call."""

    def __call__(self, *args, **kwargs):
        return _SENTINEL


def _neuter(module, dotted: str) -> None:
    """Replace ``dotted`` (``func`` or ``Class.method``) on ``module`` with an inert callable."""
    parts = dotted.split(".")
    if len(parts) == 1:
        setattr(module, parts[0], _Inert())
    elif len(parts) == 2:
        setattr(getattr(module, parts[0]), parts[1], lambda self, *a, **k: _SENTINEL)
    else:
        raise ValueError(f"unsupported VACUITY_TARGET {dotted!r} (expected 'func' or 'Class.method')")


def _load(module_ref: str):
    """Import a dotted module, or load a fixture by .py path."""
    if module_ref.endswith(".py"):
        spec = importlib.util.spec_from_file_location("_vacuity_fixture", module_ref)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    return importlib.import_module(module_ref)


def _worker(module_ref: str, targets: list[str]) -> int:
    """Neuter ``targets`` on the module, then return its ``run_self_test()`` exit code. An
    uncaught exception from a neutered oracle propagates and exits non-zero — also a red."""
    module = _load(module_ref)
    for target in targets:
        _neuter(module, target)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        result = module.run_self_test()
    # A self-test returns 0 (green) / 1 (red). Coerce a bare ``None`` (a function that
    # falls off the end) to 0 rather than crashing the worker — int(None) would TypeError
    # and a green control harness would be misread as ERROR during the VACUITY_TARGETS rollout.
    return 0 if result is None else int(result)


def _run_worker(module_ref: str, targets: list[str]) -> int:
    """Run the worker in a fresh subprocess (isolation) and return its exit code."""
    args = [sys.executable, str(Path(__file__)), "--worker", "--module", module_ref]
    if targets:
        args += ["--targets", ",".join(targets)]
    return subprocess.run(args, capture_output=True, text=True).returncode


def _classify(module_ref: str, targets: list[str]) -> str:
    # SOUNDNESS NOTE: control must be green, then any non-zero neutered run is TEETH —
    # including a red that comes from a type-crash when the inert sentinel is touched (not
    # only from the harness's assertion firing). The control-vs-neutered delta keeps this
    # honest (the ONLY change is the oracle neuter), but the gate proves the oracle is
    # load-bearing/reachable, not that the self-test would catch every wrong-but-non-crashing
    # oracle. Limitation documented in docs/decisions/0006-mutation-testing.md.
    control = _run_worker(module_ref, [])          # no neuter — harness should be green
    if control != 0:
        return "ERROR"                              # self-test already red without us
    neutered = _run_worker(module_ref, targets)
    return "TEETH" if neutered != 0 else "VACUOUS"


def _discover() -> list[tuple[str, list[str] | None]]:
    found = []
    for flavor in FLAVORS:
        for path in sorted((ROOT / "harnesses" / flavor).glob("*_test_harness.py")):
            module_ref = f"harnesses.{flavor}.{path.stem}"
            targets = getattr(importlib.import_module(module_ref), "VACUITY_TARGETS", None)
            found.append((module_ref, targets))
    return found


def run_gate() -> int:
    mapped_bad, errors, unmapped, teeth = [], [], [], []
    for module_ref, targets in _discover():
        if not targets:
            unmapped.append(module_ref)
            print(f"  UNMAPPED  {module_ref}  (no VACUITY_TARGETS — advisory)")
            continue
        status = _classify(module_ref, list(targets))
        print(f"  {status:<8}  {module_ref}  targets={list(targets)}")
        if status == "TEETH":
            teeth.append(module_ref)
        elif status == "VACUOUS":
            mapped_bad.append(module_ref)
        else:
            errors.append(module_ref)

    print(
        f"\nvacuity-gate: {len(teeth)} teeth, {len(mapped_bad)} vacuous, "
        f"{len(errors)} error, {len(unmapped)} unmapped (advisory)."
    )
    if mapped_bad or errors:
        print("FAIL: a mapped harness stayed green with its oracle neutered (vacuous), "
              "or its self-test was already red.", file=sys.stderr)
        return 1
    return 0


def _run_self_test() -> int:
    """Prove the gate itself on two fixtures: a real harness must read TEETH; a deliberately
    vacuous one must read VACUOUS (else the gate has no teeth)."""
    fx = ROOT / "tools" / "_vacuity_fixtures"
    real = str(fx / "real_harness.py")
    vacuous = str(fx / "vacuous_harness.py")
    failures = 0

    real_status = _classify(real, ["oracle"])
    if real_status != "TEETH":
        failures += 1
        print(f"FAIL: real fixture classified {real_status}, expected TEETH", file=sys.stderr)

    vacuous_status = _classify(vacuous, ["oracle"])
    if vacuous_status != "VACUOUS":
        failures += 1
        print(f"FAIL: vacuous fixture classified {vacuous_status}, expected VACUOUS "
              "(the gate did not detect a vacuous harness)", file=sys.stderr)

    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (real fixture reads TEETH; vacuous fixture is detected as VACUOUS)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Vacuous-green meta-gate")
    parser.add_argument("--self-test", action="store_true", help="prove the gate on its fixtures")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--module", help=argparse.SUPPRESS)
    parser.add_argument("--targets", default="", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.worker:
        targets = [t for t in args.targets.split(",") if t]
        return _worker(args.module, targets)
    if args.self_test:
        return _run_self_test()
    print("Vacuous-green meta-gate — neutering each mapped harness's oracle:\n")
    return run_gate()


if __name__ == "__main__":
    sys.exit(main())
