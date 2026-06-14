#!/usr/bin/env python3
"""RAG context-precision harness — retrieval relevance (deepeval).

WHY:   A RAG answer is only as trustworthy as what was retrieved. A generator can be
       perfectly faithful to context that is itself irrelevant — "faithful to the wrong
       source." Checking only the final answer string hides this: the answer may read
       fine while the retrieval that fed it pulled in off-topic chunks. The failure
       class is low CONTEXT PRECISION — the retriever returns distractors that do not
       pertain to the question. `llm_eval` tests generation faithfulness (answer vs
       context); this harness tests the OTHER half of RAG, the retrieval, which a
       generation-only check cannot model.

HOW:   A deterministic deepeval metric (`ContextPrecisionMetric`, a `BaseMetric`
       subclass) scores the fraction of retrieved chunks that are relevant to the
       question (they share a key topic term). The ORACLE retriever returns the on-topic
       chunk (precision 1.0, pass); the BUGGY retriever returns off-topic distractors
       (precision 0.0, caught). The deterministic metric stands in for an LLM judge, so
       the lane needs no API key and is reproducible — deepeval's BaseMetric/LLMTestCase
       machinery (incl. retrieval_context) is exercised for real.

WHERE: ai/ — dependency-backed (deepeval), in-process, deterministic. No live LLM, no
       secret. Uses the `deepeval` already declared in the `ai` extra. Telemetry is
       opted out at import so the lane makes no network call.

Self-test:
  python harnesses/ai/rag_faithfulness_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import os
import sys

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

# Opt out of deepeval telemetry/anonymous reporting (runtime hygiene); set after the
# imports, which are network-safe, keeping the file free of E402 and any suppression.
os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")
os.environ.setdefault("ERROR_REPORTING", "NO")
os.environ.setdefault("DEEPEVAL_DISABLE_PROGRESS_BAR", "YES")

QUESTION = "When was the Eiffel Tower completed?"
_CORPUS = {
    "relevant": "The Eiffel Tower was completed in 1889 for the World's Fair.",
    "distractor_1": "The Louvre is the most-visited museum.",
    "distractor_2": "Paris is the capital of France.",
}
# Topic terms the question is "about"; a chunk is relevant if it shares one.
_KEY_TERMS = {"eiffel", "tower", "completed", "1889"}


def oracle_retrieve(question: str) -> list[str]:
    """ORACLE: returns the chunk that actually pertains to the question."""
    return [_CORPUS["relevant"]]


def buggy_retrieve(question: str) -> list[str]:
    """BUGGY: returns plausible-looking but off-topic chunks (low precision)."""
    return [_CORPUS["distractor_1"], _CORPUS["distractor_2"]]


class ContextPrecisionMetric(BaseMetric):
    """Deterministic context precision: the share of retrieved chunks that share a key
    topic term with the question. No LLM judge."""

    def __init__(self, threshold: float = 1.0) -> None:
        self.threshold = threshold
        self.score = 0.0
        self.success = False
        self.reason = ""

    def measure(self, test_case: LLMTestCase) -> float:
        chunks = test_case.retrieval_context or []
        if not chunks:
            self.score = 0.0
        else:
            relevant = sum(1 for c in chunks if _KEY_TERMS & set(c.lower().split()))
            self.score = relevant / len(chunks)
        self.success = self.score >= self.threshold
        self.reason = f"{self.score:.2f} of {len(chunks)} chunk(s) relevant to the question"
        return self.score

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return self.success

    @property
    def __name__(self) -> str:
        return "Context Precision (deterministic)"


def retrieval_is_precise(retrieve) -> bool:
    """Return True if the retriever's chunks pass the context-precision metric."""
    metric = ContextPrecisionMetric(threshold=1.0)
    case = LLMTestCase(
        input=QUESTION,
        actual_output="(unused: this harness scores retrieval precision, not generation)",
        retrieval_context=retrieve(QUESTION),
    )
    metric.measure(case)
    return metric.is_successful()


def run_self_test() -> int:
    failures = 0
    if not retrieval_is_precise(oracle_retrieve):
        failures += 1
        print("FAIL: oracle retrieval (relevant chunk) scored as imprecise", file=sys.stderr)
    if retrieval_is_precise(buggy_retrieve):
        failures += 1  # the planted bug must be caught — else vacuous green
        print("FAIL: buggy retrieval (distractors) was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (relevant retrieval passes; distractor retrieval caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="RAG context-precision harness (deepeval)")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
