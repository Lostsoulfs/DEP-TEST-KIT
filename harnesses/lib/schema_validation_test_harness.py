#!/usr/bin/env python3
"""Schema-variant coverage test harness (pydantic + polyfactory).

WHY:   A handler over a closed set of variants (an Enum, or a tagged Union) can be
       silently incomplete: it handles the two variants the author wrote examples
       for and quietly mishandles a third. Example-based tests miss it because the
       author who forgot the variant also forgets to test it. The bug ships and
       only fires on the payload nobody imagined — the classic "poison payload".

HOW:   `Figure` is a pydantic model whose `shape` is a 3-value Enum. polyfactory's
       `coverage()` builds one instance per Enum value — exhausting the variant
       space without anyone enumerating it by hand. The oracle `area` handles every
       shape; `buggy_area` omits TRIANGLE (a plausible copy-paste gap) and returns a
       non-positive area for it. The harness drives the handler across the full
       coverage set and reports whether any variant is mishandled.

WHERE: lib/ — dependency-backed (pydantic, polyfactory) but fully in-process, no
       services. Adds `pydantic` + `polyfactory` to the `lib` extra.

Self-test:
  python harnesses/lib/schema_validation_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import math
import sys
from enum import Enum
from typing import Callable

from polyfactory.factories.pydantic_factory import ModelFactory
from pydantic import BaseModel, Field


class Shape(str, Enum):
    CIRCLE = "circle"
    SQUARE = "square"
    TRIANGLE = "triangle"


class Figure(BaseModel):
    shape: Shape
    # Fixed positive size keeps the demo deterministic and focused on Enum-variant
    # coverage (the headline polyfactory feature) rather than numeric edge cases.
    size: float = Field(default=2.0, gt=0)


# --- ORACLE: every variant handled ----------------------------------------------
def area(fig: Figure) -> float:
    if fig.shape is Shape.CIRCLE:
        return math.pi * fig.size**2
    if fig.shape is Shape.SQUARE:
        return fig.size**2
    if fig.shape is Shape.TRIANGLE:
        return (math.sqrt(3) / 4) * fig.size**2
    raise ValueError(f"unhandled shape: {fig.shape}")  # pragma: no cover


# --- BUGGY: TRIANGLE branch omitted ---------------------------------------------
def buggy_area(fig: Figure) -> float:
    if fig.shape is Shape.CIRCLE:
        return math.pi * fig.size**2
    if fig.shape is Shape.SQUARE:
        return fig.size**2
    # TRIANGLE silently falls through to a degenerate 0.0 — a real area is positive.
    return 0.0


class FigureFactory(ModelFactory[Figure]):
    __model__ = Figure
    # Pin size so coverage varies only the Enum, isolating the variant-completeness
    # check from numeric randomness.
    size = 2.0


def mishandles_a_variant(handler: Callable[[Figure], float]) -> bool:
    """Drive `handler` across polyfactory's per-Enum coverage set. Return True if any
    variant raises or yields a non-positive area (i.e. the handler is incomplete)."""
    for fig in FigureFactory.coverage():
        try:
            result = handler(fig)
        except Exception:
            return True
        if not (result > 0):
            return True
    return False


def run_self_test() -> int:
    failures = 0
    if mishandles_a_variant(area):
        failures += 1
        print("FAIL: oracle area mishandles a covered variant", file=sys.stderr)
    if not mishandles_a_variant(buggy_area):
        failures += 1
        print("FAIL: buggy area (missing TRIANGLE) was NOT caught", file=sys.stderr)
    # Concrete, human-visible instance of the gap.
    if buggy_area(Figure(shape=Shape.TRIANGLE)) > 0:
        failures += 1
        print("FAIL: buggy TRIANGLE area unexpectedly positive", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (oracle covers all variants; missing TRIANGLE branch caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Schema-variant coverage harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
