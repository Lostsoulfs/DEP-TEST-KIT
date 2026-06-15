"""The vacuous-green meta-gate has teeth of its own: it must classify a real fixture as TEETH
and a deliberately-vacuous fixture as VACUOUS, and the mapped harnesses must all pass."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load_gate():
    spec = importlib.util.spec_from_file_location("vacuity_gate", ROOT / "tools" / "vacuity_gate.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gate_self_test_passes() -> None:
    # Proves the gate detects a vacuous harness (and clears a real one).
    assert _load_gate()._run_self_test() == 0


def test_gate_classifies_fixtures() -> None:
    gate = _load_gate()
    fx = ROOT / "tools" / "_vacuity_fixtures"
    assert gate._classify(str(fx / "real_harness.py"), ["oracle"]) == "TEETH"
    assert gate._classify(str(fx / "vacuous_harness.py"), ["oracle"]) == "VACUOUS"


def test_mapped_harnesses_have_teeth() -> None:
    # No mapped harness may be vacuous; the gate returns 0 over the current set.
    assert _load_gate().run_gate() == 0
