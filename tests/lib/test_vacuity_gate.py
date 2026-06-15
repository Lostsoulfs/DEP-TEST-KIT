"""The vacuous-green meta-gate has teeth of its own: it must classify a real fixture as TEETH
and a deliberately-vacuous fixture as VACUOUS, and the mapped harnesses must all pass."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

# run_gate() discovers + imports every lib AND ai harness in-process; the ai harnesses pull
# in deepeval. CI provisions --all-extras, but skip cleanly if a contributor ran the lib lane
# with only the lib extra installed (the gate's own teeth are covered by the fixture tests above).
_HAS_AI_EXTRA = importlib.util.find_spec("deepeval") is not None


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


@pytest.mark.skipif(not _HAS_AI_EXTRA, reason="run_gate imports ai harnesses (deepeval not installed)")
def test_mapped_harnesses_have_teeth() -> None:
    # No mapped harness may be vacuous; the gate returns 0 over the current set.
    assert _load_gate().run_gate() == 0
