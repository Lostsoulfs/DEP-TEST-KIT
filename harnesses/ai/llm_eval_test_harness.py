#!/usr/bin/env python3
"""LLM-output evaluation harness — hallucination detection (deepeval).

WHY:   An LLM answer cannot be checked with `assert output == expected`: the wording
       varies every run. The real failure class is the *hallucination* — a confident
       claim that contradicts the provided context (the RAG source). A plain string
       test passes a faithful answer and a fabricated one alike; an evaluation metric
       scores faithfulness and fails the fabrication.

HOW:   A deterministic deepeval metric (`ContextFaithfulnessMetric`, a `BaseMetric`
       subclass) scores an `LLMTestCase`: the fraction of the answer's claims that are
       grounded in the context. The ORACLE answer is grounded (score 1.0, pass); the
       BUGGY answer states the tower is in Berlin, ungrounded (score 0.0, caught). The
       deterministic metric stands in for an LLM judge so the lane needs no API key and
       is reproducible — the failure class (hallucination) and deepeval's
       metric/test-case harness are exercised for real.

WHERE: ai/ — dependency-backed (deepeval), in-process, deterministic. No live LLM, no
       secret. Adds `deepeval` to the `ai` extra. Telemetry is opted out at import so
       the lane makes no network call.

Self-test:
  python harnesses/ai/llm_eval_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import os
import sys

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

# Opt out of deepeval telemetry/anonymous reporting (runtime hygiene). The import itself
# is network-safe, so this is set after the imports — no module-level statement precedes
# them, keeping the file free of E402 and any suppression.
os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")
os.environ.setdefault("ERROR_REPORTING", "NO")
os.environ.setdefault("DEEPEVAL_DISABLE_PROGRESS_BAR", "YES")

CONTEXT = ["The Eiffel Tower is in Paris.", "It was completed in 1889."]
GROUNDED_ANSWER = "The Eiffel Tower is in Paris."
HALLUCINATED_ANSWER = "The Eiffel Tower is in Berlin."


class ContextFaithfulnessMetric(BaseMetric):
    """Deterministic faithfulness: the share of the answer's sentence-claims that
    appear (case-insensitively) in the context. No LLM judge."""

    def __init__(self, threshold: float = 1.0) -> None:
        self.threshold = threshold
        self.score = 0.0
        self.success = False
        self.reason = ""

    def measure(self, test_case: LLMTestCase) -> float:
        context = " ".join(test_case.context or []).lower()
        claims = [
            c.strip() for c in test_case.actual_output.replace("!", ".").split(".") if c.strip()
        ]
        if not claims:
            self.score = 1.0
        else:
            grounded = sum(1 for c in claims if c.lower() in context)
            self.score = grounded / len(claims)
        self.success = self.score >= self.threshold
        self.reason = f"{self.score:.2f} of {len(claims)} claim(s) grounded in context"
        return self.score

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return self.success

    @property
    def __name__(self) -> str:
        return "Context Faithfulness (deterministic)"


def answer_is_faithful(answer: str) -> bool:
    """Return True if `answer` passes the faithfulness metric against CONTEXT."""
    metric = ContextFaithfulnessMetric(threshold=1.0)
    case = LLMTestCase(input="Where is the Eiffel Tower?", actual_output=answer, context=CONTEXT)
    metric.measure(case)
    return metric.is_successful()


def run_self_test() -> int:
    failures = 0
    if not answer_is_faithful(GROUNDED_ANSWER):
        failures += 1
        print("FAIL: grounded answer was flagged as unfaithful", file=sys.stderr)
    if answer_is_faithful(HALLUCINATED_ANSWER):
        failures += 1
        print("FAIL: hallucinated answer was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (grounded answer passes; hallucinated 'Berlin' answer caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LLM hallucination-eval harness (deepeval)")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
