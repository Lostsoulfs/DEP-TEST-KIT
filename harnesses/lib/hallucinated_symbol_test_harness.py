#!/usr/bin/env python3
"""Hallucinated-attribute detection harness (live pydantic surface introspection).

WHY:   LLM-generated code invents methods/attributes that do not exist on REAL packages —
       the Llama-family `AttributeError`/`TypeError`-from-a-hallucinated-method pattern. A
       naive check ("does the package import?") passes, and static type-checkers (mypy /
       pyright / ty) go blind on untyped, C-extension, or dynamically-built surfaces —
       exactly where hallucinations concentrate. The only ground truth is the LIVE,
       version-pinned surface of the actually-installed dependency.

HOW:   Parse a snippet's `pydantic.<attr>` accesses with `ast`, and resolve each against the
       installed pydantic's live surface — `hasattr` (which triggers PEP 562 module
       `__getattr__` and finds C-extension members) plus `__all__` — pinned to
       `importlib.metadata.version("pydantic")`. The ORACLE `hallucinated_attributes` flags an
       attribute that is not on the surface (`pydantic.BaseModelz`); the BUGGY
       `buggy_hallucinated_attributes` only checks that the MODULE imports and never checks the
       attribute, so a hallucinated method slips straight through.

WHERE: lib/ — dependency-backed (pydantic, already in the `lib` extra), fully in-process, no
       service. The harness introspects the real installed pydantic; nothing is mocked.

Self-test:
  python harnesses/lib/hallucinated_symbol_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import ast
import sys
from importlib import metadata

import pydantic  # the dependency whose live surface is the oracle

_MODULE = "pydantic"
PINNED_VERSION = metadata.version(_MODULE)

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["attribute_exists"]

REAL_SRC = (
    "import pydantic\n"
    "class M(pydantic.BaseModel):\n"
    "    pass\n"
    "validator = pydantic.field_validator\n"
)
HALLUCINATED_SRC = (
    "import pydantic\n"
    "x = pydantic.BaseModelz\n"            # invented class
    "y = pydantic.field_validatorr\n"      # invented decorator (typo'd hallucination)
)
_HALLUCINATED = {"BaseModelz", "field_validatorr"}


def attribute_exists(attr: str) -> bool:
    """ORACLE primitive: does `attr` exist on the live, installed pydantic surface? Honors
    PEP 562 module `__getattr__`, C-extension members (via hasattr), and `__all__` re-exports."""
    if hasattr(pydantic, attr):
        return True
    return attr in getattr(pydantic, "__all__", ())


def _accessed_attrs(source: str) -> list[str]:
    """Every `pydantic.<attr>` accessed in `source`."""
    tree = ast.parse(source)
    return [
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == _MODULE
    ]


def hallucinated_attributes(source: str) -> list[str]:
    """ORACLE: the `pydantic.<attr>` accesses in `source` that are NOT on the live surface."""
    return sorted({attr for attr in _accessed_attrs(source) if not attribute_exists(attr)})


def buggy_hallucinated_attributes(source: str) -> list[str]:
    """BUGGY: verifies only that the module imports; never checks the attribute exists, so a
    hallucinated method on a real, importable package is invisible."""
    try:
        __import__(_MODULE)
    except ImportError:
        return [_MODULE]
    return []


def run_self_test() -> int:
    failures = 0
    if hallucinated_attributes(REAL_SRC):
        failures += 1
        print("FAIL: oracle flagged a real pydantic attribute (false positive)", file=sys.stderr)

    oracle_found = set(hallucinated_attributes(HALLUCINATED_SRC))
    if not _HALLUCINATED <= oracle_found:
        failures += 1
        print("FAIL: oracle missed a hallucinated attribute", file=sys.stderr)

    buggy_found = set(buggy_hallucinated_attributes(HALLUCINATED_SRC))
    if _HALLUCINATED & buggy_found:
        failures += 1
        print("FAIL: buggy checker flagged the hallucination — no teeth gap", file=sys.stderr)

    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print(f"self-test: OK (oracle catches hallucinated attrs the naive check misses; "
          f"pydantic {PINNED_VERSION})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Hallucinated-attribute detection harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
