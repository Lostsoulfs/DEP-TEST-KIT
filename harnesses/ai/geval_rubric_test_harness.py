#!/usr/bin/env python3
"""Rubric-conformance harness — deterministic G-Eval stand-in (deepeval).

WHY:   Beyond factual correctness, an LLM/agent output often must satisfy an explicit
       RUBRIC — structure, required fields, value ranges, allowed enums (format / tone /
       policy). deepeval's G-Eval scores output against natural-language
       `evaluation_steps`, but with an LLM judge: non-deterministic and needs an API key,
       so it cannot gate CI reproducibly. The failure class is a plausible output that
       violates ONE rubric step (a missing key, an out-of-range score, a disallowed
       verdict). A plain `assert ==` cannot express a rubric, and an inert check passes a
       conforming and a malformed output alike.

HOW:   A deterministic deepeval metric (`RubricMetric`, a `BaseMetric` subclass) runs each
       hard-coded rubric step as a Python predicate over the output and scores the fraction
       passed. The `EVALUATION_STEPS` read like the steps you would hand G-Eval, but each
       is backed by a deterministic check. The ORACLE output satisfies every step (score
       1.0, pass); the BUGGY output violates exactly one — its `confidence` is outside
       [0, 1] (score < 1.0, caught). The deterministic grader stands in for the LLM judge.

WHERE: ai/ — dependency-backed (deepeval), in-process, deterministic. No live LLM, no
       secret. Uses the `deepeval` already in the `ai` extra. Telemetry opted out at import.

Self-test:
  python harnesses/ai/geval_rubric_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Callable

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")
os.environ.setdefault("ERROR_REPORTING", "NO")
os.environ.setdefault("DEEPEVAL_DISABLE_PROGRESS_BAR", "YES")

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["output_satisfies_rubric"]

# A "judge agent" must emit JSON: {"verdict": "pass"|"fail", "confidence": <0..1>}.
ORACLE_OUTPUT = '{"verdict": "pass", "confidence": 0.92}'
BUGGY_OUTPUT = '{"verdict": "pass", "confidence": 1.7}'   # confidence out of range

# Hard-coded, reproducible rubric: each step is the text you would hand G-Eval, paired
# with a deterministic predicate over (raw_output, parsed_obj).
EVALUATION_STEPS: list[tuple[str, Callable[[str, object], bool]]] = [
    ("Output is valid JSON.",
     lambda raw, obj: obj is not None),
    ("Output has both keys 'verdict' and 'confidence'.",
     lambda raw, obj: isinstance(obj, dict) and {"verdict", "confidence"} <= obj.keys()),
    ("'verdict' is one of {'pass', 'fail'}.",
     lambda raw, obj: isinstance(obj, dict) and obj.get("verdict") in {"pass", "fail"}),
    ("'confidence' is a number in [0, 1].",
     lambda raw, obj: isinstance(obj, dict)
     and isinstance(obj.get("confidence"), (int, float))
     and not isinstance(obj.get("confidence"), bool)
     and 0.0 <= float(obj["confidence"]) <= 1.0),
]


def _parse(raw: str) -> object:
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return None


class RubricMetric(BaseMetric):
    """Deterministic rubric grader: the fraction of hard-coded EVALUATION_STEPS the output
    satisfies. Stands in for G-Eval's LLM judge so the lane is reproducible."""

    def __init__(self, threshold: float = 1.0) -> None:
        self.threshold = threshold
        self.score = 0.0
        self.success = False
        self.reason = ""

    def measure(self, test_case: LLMTestCase) -> float:
        raw = test_case.actual_output or ""
        obj = _parse(raw)
        passed = [text for text, check in EVALUATION_STEPS if check(raw, obj)]
        self.score = len(passed) / len(EVALUATION_STEPS)
        self.success = self.score >= self.threshold
        failed = [text for text, check in EVALUATION_STEPS if not check(raw, obj)]
        self.reason = (
            f"{len(passed)}/{len(EVALUATION_STEPS)} rubric steps passed"
            + (f"; failed: {failed[0]}" if failed else "")
        )
        return self.score

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return self.success

    @property
    def __name__(self) -> str:
        return "Rubric Conformance (deterministic G-Eval)"


def output_satisfies_rubric(output: str) -> bool:
    """Return True if `output` passes every rubric step."""
    metric = RubricMetric(threshold=1.0)
    metric.measure(LLMTestCase(input="grade the agent output", actual_output=output))
    return metric.is_successful()


def run_self_test() -> int:
    failures = 0
    if not output_satisfies_rubric(ORACLE_OUTPUT):
        failures += 1
        print("FAIL: rubric-conformant oracle output was flagged", file=sys.stderr)
    if output_satisfies_rubric(BUGGY_OUTPUT):
        failures += 1  # the planted bug must be caught — else vacuous green
        print("FAIL: buggy output (confidence out of range) was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (rubric-conformant output passes; out-of-range confidence caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rubric-conformance harness (deterministic G-Eval)")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
