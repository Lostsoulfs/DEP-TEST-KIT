#!/usr/bin/env python3
"""SQL-injection harness (sqlalchemy): bind parameters, never string-format user input.

OWASP Top 10:2025 A05 Injection (SQL injection, CWE-89).

WHY: Distinct from the ORM-constraint harness (sql_orm, which is about data integrity): this
is query CONSTRUCTION. Building SQL by interpolating user input -- `f"... name = '{user}'"` --
lets `' OR '1'='1` rewrite the query. Bound parameters keep user data OUT of the SQL text
entirely, so injection is structurally impossible.

HOW: `ParameterizedQuery` is the ORACLE -- `text("... name = :name").bindparams(name=user)`,
so the rendered SQL holds a `:name` placeholder, never the value. `StringFormatQuery` is the
planted defect -- f-string interpolation. `query_is_injectable` builds a query from a classic
payload and reports whether the injection appears in the rendered SQL.

WHERE: lib/ -- dependency-backed (`sqlalchemy` bound parameters), in-process, no database.

Self-test:
    python harnesses/lib/sql_injection_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

from sqlalchemy import text

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["query_is_injectable"]

DOSSIER = {
    "name": "sql_injection",
    "path": "harnesses/lib/sql_injection_test_harness.py",
    "flavor": "lib",
    "dependency": "sqlalchemy",
    "standard": "OWASP Top 10:2025 A05 Injection - SQL injection (CWE-89)",
    "failure_class": "User input string-formatted into SQL text (' OR '1'='1 rewrites the query)",
    "oracle": "ParameterizedQuery.build - text(...).bindparams; value stays a placeholder",
    "buggy": "StringFormatQuery.build - f-string interpolation of user input",
    "planted_mutant": "username \"' OR '1'='1\" appears verbatim in the rendered SQL",
    "proof_file": "tests/lib/test_sql_injection_proof.py",
    "vacuity_targets": ["query_is_injectable"],
    "commands": ["python harnesses/lib/sql_injection_test_harness.py --self-test"],
    "known_limits": "parameterization of values; not identifier/ORDER-BY allow-listing",
    "related": ["sql_orm", "nosql_injection", "ldap_injection"],
}

_PAYLOAD = "' OR '1'='1"


class ParameterizedQuery:
    """ORACLE: bound parameters keep the value out of the SQL text."""

    def build(self, username: str):
        return text("SELECT * FROM users WHERE name = :name").bindparams(name=username)

    def rendered_sql(self, username: str) -> str:
        return str(self.build(username))


class StringFormatQuery:
    """BUGGY: interpolate the user input into the SQL string."""

    def build(self, username: str) -> str:
        return f"SELECT * FROM users WHERE name = '{username}'"

    def rendered_sql(self, username: str) -> str:
        return self.build(username)


def builds_lookup_query(make_query: Callable[[], object]) -> bool:
    return "SELECT" in make_query().rendered_sql("alice")


def query_is_injectable(make_query: Callable[[], object]) -> bool:
    """True == the injection payload appears in the rendered SQL (SQL injection)."""
    return _PAYLOAD in make_query().rendered_sql(_PAYLOAD)


def run_self_test() -> int:
    failures = 0
    if not builds_lookup_query(ParameterizedQuery):
        failures += 1
        print("FAIL: oracle did not build a lookup query", file=sys.stderr)
    if query_is_injectable(ParameterizedQuery):
        failures += 1
        print("FAIL: oracle inlined user input into the SQL text", file=sys.stderr)
    if not query_is_injectable(StringFormatQuery):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: string-format SQL injection was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (bound params keep the payload out of the SQL; f-string inlines it)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SQL-injection harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
