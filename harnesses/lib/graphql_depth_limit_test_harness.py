#!/usr/bin/env python3
"""GraphQL depth-limit harness (graphql-core): reject abusively deep queries.

OWASP API Security 2023 API4 Unrestricted Resource Consumption (GraphQL query depth / DoS).

WHY: GraphQL lets a client nest a query arbitrarily deep (`a { b { c { ... } } }`) or exploit
cyclic relationships, forcing the server into exponential resolution work -- a denial-of-service
with a single small request. The server must parse the query and reject one whose selection
nesting exceeds a depth budget.

HOW: `DepthLimitedSchema` is the ORACLE -- it parses the query (graphql-core) and refuses one
whose maximum selection-set depth exceeds the budget. `UnboundedSchema` is the planted defect
-- it executes any query. `executes_deeply_nested` submits a deeply-nested query and reports
whether it was executed.

WHERE: lib/ -- dependency-backed (`graphql-core` query parsing), in-process.

Self-test:
    python harnesses/lib/graphql_depth_limit_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

from graphql import parse

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["executes_deeply_nested"]

DOSSIER = {
    "name": "graphql_depth_limit",
    "path": "harnesses/lib/graphql_depth_limit_test_harness.py",
    "flavor": "lib",
    "dependency": "graphql-core",
    "standard": "OWASP API Security 2023 API4 Unrestricted Resource Consumption - GraphQL depth",
    "failure_class": "Executing an arbitrarily deep GraphQL query (resolution DoS)",
    "oracle": "DepthLimitedSchema.execute - parse and refuse depth beyond the budget",
    "buggy": "UnboundedSchema.execute - execute any query",
    "planted_mutant": "a query nested far deeper than the budget is executed",
    "proof_file": "tests/lib/test_graphql_depth_limit_proof.py",
    "vacuity_targets": ["executes_deeply_nested"],
    "commands": ["python harnesses/lib/graphql_depth_limit_test_harness.py --self-test"],
    "known_limits": "selection-set depth budget; not field-count/alias complexity scoring",
    "related": ["structured_output_contract", "agent_circuit_breaker"],
}

_MAX_DEPTH = 5
_SHALLOW = "{ user { name email } }"
_DEEP = "{ a { b { c { d { e { f { g } } } } } } }"


def _query_depth(query: str) -> int:
    document = parse(query)

    def depth(selection_set) -> int:
        if selection_set is None:
            return 0
        return max((1 + depth(getattr(sel, "selection_set", None))
                    for sel in selection_set.selections), default=0)

    return max((depth(getattr(d, "selection_set", None)) for d in document.definitions), default=0)


class DepthLimitedSchema:
    """ORACLE: refuse a query whose nesting exceeds the depth budget."""

    def execute(self, query: str) -> str:
        if _query_depth(query) > _MAX_DEPTH:
            raise ValueError("query exceeds maximum depth")
        return "ok"


class UnboundedSchema:
    """BUGGY: execute any query regardless of depth."""

    def execute(self, query: str) -> str:
        return "ok"  # BUG: no depth budget


def executes_shallow_query(make_schema: Callable[[], object]) -> bool:
    return make_schema().execute(_SHALLOW) == "ok"


def executes_deeply_nested(make_schema: Callable[[], object]) -> bool:
    """True == a query deeper than the budget was executed (resource-exhaustion DoS)."""
    try:
        return make_schema().execute(_DEEP) == "ok"
    except Exception:
        return False


def run_self_test() -> int:
    failures = 0
    if not executes_shallow_query(DepthLimitedSchema):
        failures += 1
        print("FAIL: oracle rejected a shallow, in-budget query", file=sys.stderr)
    if executes_deeply_nested(DepthLimitedSchema):
        failures += 1
        print("FAIL: oracle executed a query past the depth budget", file=sys.stderr)
    if not executes_deeply_nested(UnboundedSchema):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: unbounded schema deep-query execution was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (depth-limited schema refuses the deep query; unbounded one executes it)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="GraphQL depth-limit harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
