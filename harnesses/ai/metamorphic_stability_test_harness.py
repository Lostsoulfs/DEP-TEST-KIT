#!/usr/bin/env python3
"""Metamorphic stability harness — output invariance under neutral perturbation (Hypothesis).

WHY:   A grounded responder should give the SAME answer to semantically-equivalent
       phrasings of a question; an ungrounded one is volatile — its output swings under
       surface perturbations (case, whitespace, punctuation) that do not change meaning.
       An example test checks one phrasing and never sees the instability. This is the
       MetaQA-style metamorphic relation for hallucination/instability detection: rather
       than assert a fixed output, assert the RELATION `f(perturb(q)) == f(q)` across many
       generated, meaning-preserving perturbations.

HOW:   `respond_stable` (ORACLE) normalizes the question (case/punctuation/whitespace
       insensitive) before answering, so every neutral perturbation maps to the same
       answer. `respond_volatile` (BUGGY) keys off a surface feature (length parity), so a
       neutral perturbation that changes the length flips its answer. Hypothesis composes
       meaning-preserving ops and `unstable_under_perturbation` returns the first
       perturbation that changes the answer (falsifying stability), or None if invariant.
       The oracle is stable (None); the buggy is caught (a perturbation is found). No model.

WHERE: ai/ — dependency-backed (hypothesis), fully in-process, deterministic. No live LLM
       and no API key. Uses the `hypothesis` already declared in the `ai` extra.

Self-test:
  python harnesses/ai/metamorphic_stability_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

from hypothesis import given, settings
from hypothesis import strategies as st

BASE_QUESTION = "What is the capital of France?"

# Meaning-preserving surface perturbations: case, whitespace, and trailing punctuation
# only — none changes what is being asked.
_OPS: dict[str, Callable[[str], str]] = {
    "upper": str.upper,
    "lower": str.lower,
    "title": str.title,
    "pad": lambda q: f"  {q}  ",
    "trailing_space": lambda q: q + " ",
    "strip_qmark": lambda q: q.rstrip("?"),
}


def _normalize(q: str) -> frozenset[str]:
    """Case/punctuation/whitespace-insensitive token set — the meaning-bearing content."""
    return frozenset("".join(ch if ch.isalnum() else " " for ch in q.lower()).split())


def respond_stable(question: str) -> str:
    """ORACLE: answers from the normalized question, so neutral perturbations are invariant."""
    toks = _normalize(question)
    return "Paris" if {"capital", "france"} <= toks else "unknown"


def respond_volatile(question: str) -> str:
    """BUGGY: keys off a surface feature (length parity), so a neutral perturbation that
    changes the length flips the answer."""
    return "Paris" if len(question) % 2 == 0 else "Lyon"


def _make_stability_check(responder: Callable[[str], str], base: str):
    expected = responder(base)

    @settings(max_examples=200)
    @given(st.lists(st.sampled_from(list(_OPS)), min_size=1, max_size=4))
    def check(ops: list[str]) -> None:
        perturbed = base
        for op in ops:
            perturbed = _OPS[op](perturbed)
        if responder(perturbed) != expected:
            raise AssertionError(f"{ops!r} -> {responder(perturbed)!r} (expected {expected!r})")

    return check


def unstable_under_perturbation(
    responder: Callable[[str], str], base: str = BASE_QUESTION
) -> str | None:
    """Return a perturbation (op sequence) that changes the responder's answer, or None if
    the answer is invariant under every meaning-preserving perturbation Hypothesis tries."""
    try:
        _make_stability_check(responder, base)()
    except AssertionError as e:
        return str(e)
    return None


def run_self_test() -> int:
    failures = 0
    oracle_bad = unstable_under_perturbation(respond_stable)
    if oracle_bad is not None:
        failures += 1
        print(f"FAIL: oracle was unstable under a neutral perturbation: {oracle_bad}", file=sys.stderr)
    buggy_bad = unstable_under_perturbation(respond_volatile)
    if buggy_bad is None:
        failures += 1  # the planted bug must be caught — else vacuous green
        print("FAIL: buggy (volatile) responder appeared stable (not caught)", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print(f"self-test: OK (oracle invariant; buggy caught on -> {buggy_bad})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Metamorphic stability harness (Hypothesis)")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
