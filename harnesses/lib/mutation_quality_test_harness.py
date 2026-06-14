#!/usr/bin/env python3
"""Mutation-quality (vacuous-green) test harness (mutmut).

WHY:   Line coverage lies. A test can *execute* a line and assert nothing about it —
       "vacuous green", the exact failure class this repo exists to guard against. A
       coverage report shows 100% while a whole branch is logically unguarded. Only
       mutation testing exposes it: inject a small fault (a "mutant") into the code
       and see whether the suite notices. A mutant that survives is a line your tests
       run but do not pin.

HOW:   `target.py` is a one-line function. mutmut mutates it (e.g. `>` -> `>=`,
       `0` -> `1`) and re-runs a test suite against each mutant. The ORACLE is a
       STRONG suite that checks the boundary and the negative case — it kills every
       mutant (0 survivors). The BUGGY artefact is a WEAK suite that only asserts one
       easy case: it executes the line but lets mutants survive. The harness runs
       mutmut on each suite (in an isolated temp dir, never the repo) and counts
       survivors from `mutmut results`.

WHERE: lib/ — dependency-backed (mutmut) and in-process, but mutmut is a *runner*:
       it is invoked as a CLI subprocess, not imported (hence the deptry DEP002
       ignore). No services/Docker. Adds `mutmut` to the `lib` extra.

Self-test:
  python harnesses/lib/mutation_quality_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# mutmut loads its config from the *current working directory at import time*, so it
# must only ever run inside the throwaway temp project below — never the repo root.
_MUTMUT = str(Path(sys.executable).parent / "mutmut")


def mutmut_available() -> bool:
    """mutmut 3.x refuses to run on native Windows (boxed/mutmut#397); Linux/CI/WSL is
    fine. Callers skip rather than fail when it can't run — mirrors the integration
    lane's Docker-absent skip, never a silent green."""
    if sys.platform.startswith("win"):
        return False
    return Path(_MUTMUT).exists() or shutil.which("mutmut") is not None

# The code under test: one line, a handful of mutants.
TARGET_SRC = """\
def is_positive(n):
    return n > 0
"""

# --- ORACLE: a STRONG suite — kills every mutant --------------------------------
STRONG_TEST_SRC = """\
from target import is_positive


def test_is_positive():
    assert is_positive(5) is True
    assert is_positive(1) is True
    assert is_positive(0) is False
    assert is_positive(-3) is False
"""

# --- BUGGY: a WEAK suite — runs the line, asserts almost nothing (vacuous) -------
WEAK_TEST_SRC = """\
from target import is_positive


def test_is_positive():
    # Executes the line for coverage but checks only one easy case, so mutants
    # like `n >= 0` and `n > 1` slip through unnoticed.
    assert is_positive(5) is True
"""


def count_survivors(test_src: str) -> int:
    """Run mutmut on `target.py` against `test_src` in an isolated temp project.
    Return the number of surviving mutants reported by `mutmut results`."""
    with tempfile.TemporaryDirectory() as d:
        proj = Path(d)
        (proj / "target.py").write_text(TARGET_SRC)
        (proj / "test_target.py").write_text(test_src)
        (proj / "setup.cfg").write_text("[mutmut]\nsource_paths=target.py\n")
        subprocess.run([_MUTMUT, "run"], cwd=proj, capture_output=True, text=True, timeout=180)
        results = subprocess.run(
            [_MUTMUT, "results"], cwd=proj, capture_output=True, text=True, timeout=60
        )
    return sum(1 for line in results.stdout.splitlines() if line.strip().endswith(": survived"))


def run_self_test() -> int:
    if not mutmut_available():
        print(
            "self-test: SKIPPED (mutmut does not run on native Windows — boxed/mutmut#397; "
            "runs on Linux/CI/WSL)."
        )
        return 0
    failures = 0
    strong = count_survivors(STRONG_TEST_SRC)
    weak = count_survivors(WEAK_TEST_SRC)
    if strong != 0:
        failures += 1
        print(f"FAIL: strong suite left {strong} mutant(s) alive (expected 0)", file=sys.stderr)
    if weak <= 0:
        # If the weak suite shows no survivors, mutmut isn't actually biting — the
        # harness would be vacuous itself. This guard gives it teeth.
        failures += 1
        print("FAIL: weak suite produced no survivors — mutmut found no teeth gap", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print(f"self-test: OK (strong suite kills all; weak suite leaves {weak} mutant(s) alive)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mutation-quality (vacuous-green) harness")
    parser.add_argument("--self-test", action="store_true")
    parser.parse_args(argv)
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
