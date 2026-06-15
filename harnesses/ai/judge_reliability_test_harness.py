#!/usr/bin/env python3
"""LLM-judge reliability test harness — variance gate + verbatim-span citation (deepeval).

WHY:   "LLM-as-judge" gates (G-Eval and friends) have two failure modes that a structural
       check cannot see. (1) The judge is NON-DETERMINISTIC: ask it the same question five
       times and it flips its verdict, so a green is luck, not signal. (2) The judge is
       CONTENT-BLIND: it returns a well-formed verdict that cites nothing real (or a
       trivially-present token), so it "passes" an answer it never actually grounded — the
       circular, stable-by-construction trap the repo's earlier `geval_rubric` skirts. A
       judge that is shape-valid can still be unreliable on both axes.

HOW:   The deterministic `JudgeReliabilityMetric` (a deepeval `BaseMetric`) meta-evaluates a
       judge callable on two fused pillars, with NO second LLM: (P1) run the judge N times on
       the same case and FAIL unless the verdict is unanimous (zero dispersion); (P2) require
       the judge to cite an evidence span that is a verbatim (whitespace/case-normalized)
       substring of the source, at least `MIN_SPAN` chars long, so a trivially-present token
       cannot satisfy it. The ORACLE judge is stable and cites the real supporting sentence
       (passes both). Two planted-bug judges isolate the pillars: `unstable_judge` flips its
       verdict by run index (caught by P1, even though its span is real); `blind_judge` is
       perfectly stable but cites a span absent from the source (caught by P2).

WHERE: ai/ — dependency-backed (deepeval), in-process, deterministic. No live LLM, no API
       key: the judge under test is a local callable, and both pillars are machine-checkable.
       Uses the `deepeval` already in the `ai` extra. Telemetry opted out at import.

Self-test:
  python harnesses/ai/judge_reliability_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import Counter
from dataclasses import dataclass
from typing import Callable, List

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase

os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")
os.environ.setdefault("ERROR_REPORTING", "NO")
os.environ.setdefault("DEEPEVAL_DISABLE_PROGRESS_BAR", "YES")

RUNS = 15        # how many times each judge is polled for the variance pillar
MIN_SPAN = 12    # a cited span must be at least this many chars (defeats trivial tokens)

# The case under judgement: a claim that IS supported by the source.
SOURCE = (
    "The Eiffel Tower was completed in 1889 and stands on the Champ de Mars in Paris. "
    "It was designed by the engineer Gustave Eiffel."
)
ANSWER = "The Eiffel Tower was completed in 1889."
_KEY_PHRASE = "completed in 1889"

# Symbols the vacuous-green meta-gate (Phase A) neuters to confirm this harness has teeth.
VACUITY_TARGETS = ["oracle_judge"]


@dataclass(frozen=True)
class Verdict:
    """What a judge returns: a label plus the span it claims supports that label."""

    label: str       # "supported" | "unsupported"
    evidence: str     # a span the judge asserts is in the source


# A judge: (source, answer, run_index) -> Verdict. run_index lets a flaky judge waver.
Judge = Callable[[str, str, int], Verdict]


def _normalize(text: str) -> str:
    return " ".join(text.split()).casefold()


def cites_verbatim_span(verdict: Verdict, source: str) -> bool:
    """True iff the cited evidence is a non-trivial verbatim substring of the source."""
    span = verdict.evidence.strip()
    if len(span) < MIN_SPAN:
        return False
    return _normalize(span) in _normalize(source)


# --- ORACLE: stable across runs and cites the real supporting sentence -----------
def oracle_judge(source: str, answer: str, run_index: int) -> Verdict:
    for sentence in source.split(". "):
        if _KEY_PHRASE in sentence:
            return Verdict("supported", sentence.strip())
    return Verdict("unsupported", "")


# --- BUGGY 1: flips its verdict by run index — a flaky judge (caught by P1) -------
def unstable_judge(source: str, answer: str, run_index: int) -> Verdict:
    label = "supported" if run_index % 2 == 0 else "unsupported"
    # NB: the cited span is genuinely in the source, so ONLY the variance pillar catches it.
    return Verdict(label, "completed in 1889 and stands on the Champ de Mars")


# --- BUGGY 2: perfectly stable, but cites a span not in the source (caught by P2) -
def blind_judge(source: str, answer: str, run_index: int) -> Verdict:
    return Verdict("supported", "this answer is correct and fully supported")


class JudgeReliabilityMetric(BaseMetric):
    """Deterministic meta-judge: polls a judge `runs` times and scores 1.0 only if the
    verdict is unanimous AND every cited span is a verbatim substring of the source."""

    def __init__(self, judge: Judge, runs: int = RUNS, threshold: float = 1.0) -> None:
        self.judge = judge
        self.runs = runs
        self.threshold = threshold
        self.score = 0.0
        self.success = False
        self.reason = ""
        self.stable = False
        self.spans_verbatim = False
        self.modal_agreement = 0.0

    def measure(self, test_case: LLMTestCase) -> float:
        source = (test_case.context or [""])[0]
        answer = test_case.actual_output or ""
        verdicts: List[Verdict] = [self.judge(source, answer, i) for i in range(self.runs)]

        labels = [v.label for v in verdicts]
        self.modal_agreement = max(Counter(labels).values()) / len(labels)
        self.stable = self.modal_agreement >= 1.0  # unanimous, no dispersion
        self.spans_verbatim = all(cites_verbatim_span(v, source) for v in verdicts)

        self.score = 1.0 if (self.stable and self.spans_verbatim) else 0.0
        self.success = self.score >= self.threshold
        self.reason = (
            f"stable={self.stable} (modal agreement {self.modal_agreement:.2f}); "
            f"spans_verbatim={self.spans_verbatim}"
        )
        return self.score

    async def a_measure(self, test_case: LLMTestCase, *args, **kwargs) -> float:
        return self.measure(test_case)

    def is_successful(self) -> bool:
        return self.success

    @property
    def __name__(self) -> str:
        return "Judge Reliability (variance + verbatim-span citation)"


def reliability_report(judge: Judge) -> JudgeReliabilityMetric:
    """Run the metric over the fixed case and return it (exposes both pillars)."""
    metric = JudgeReliabilityMetric(judge)
    metric.measure(LLMTestCase(input="Is the answer supported by the source?",
                               actual_output=ANSWER, context=[SOURCE]))
    return metric


def judge_is_reliable(judge: Judge) -> bool:
    return reliability_report(judge).is_successful()


def run_self_test() -> int:
    failures = 0
    if not judge_is_reliable(oracle_judge):
        failures += 1
        print("FAIL: reliable oracle judge was flagged", file=sys.stderr)

    unstable = reliability_report(unstable_judge)
    if unstable.is_successful():
        failures += 1
        print("FAIL: flaky judge passed — variance pillar has no teeth", file=sys.stderr)
    elif unstable.stable:
        failures += 1
        print("FAIL: flaky judge was not caught on the variance pillar", file=sys.stderr)

    blind = reliability_report(blind_judge)
    if blind.is_successful():
        failures += 1
        print("FAIL: content-blind judge passed — span pillar has no teeth", file=sys.stderr)
    elif blind.spans_verbatim:
        failures += 1
        print("FAIL: content-blind judge was not caught on the span pillar", file=sys.stderr)

    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (oracle reliable; flaky caught on variance; content-blind caught on span)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LLM-judge reliability harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
