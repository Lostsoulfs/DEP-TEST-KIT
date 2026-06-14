#!/usr/bin/env python3
"""OpenAPI contract-drift fuzz harness (schemathesis).

WHY:   A handwritten API test checks the responses the author thought to write. It
       cannot tell you the server has *drifted* from its own OpenAPI contract —
       returning a field with the wrong type, an undeclared shape, or a 500 on an
       input nobody tried. That drift is exactly what breaks generated clients and
       downstream consumers. schemathesis reads the schema and generates requests
       from it, validating every response against the declared contract — so the
       schema becomes an executable spec instead of stale documentation.

HOW:   `SCHEMA` declares `GET /widget` returns `{ count: integer (required) }`. Two
       Flask (WSGI) apps serve it. The ORACLE returns `{"count": 1}` — conformant.
       The BUGGY app returns `{"count": "oops"}` — a string where the contract
       promises an integer, the canonical drift bug. schemathesis derives cases from
       the schema and calls `call_and_validate`; a contract violation raises a
       `FailureGroup`. Runs fully in-process via WSGI (no network, no server).

WHERE: lib/ — dependency-backed (schemathesis, flask) and in-process. Adds
       `schemathesis` + `flask` to the `lib` extra. (httpx/hypothesis already present.)

Self-test:
  python harnesses/lib/openapi_fuzz_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Any

import schemathesis
from flask import Flask, jsonify
from hypothesis import HealthCheck, given, settings
from schemathesis.core.failures import FailureGroup

SCHEMA: dict[str, Any] = {
    "openapi": "3.0.0",
    "info": {"title": "widget-service", "version": "1.0"},
    "paths": {
        "/widget": {
            "get": {
                "responses": {
                    "200": {
                        "description": "a widget",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["count"],
                                    "properties": {"count": {"type": "integer"}},
                                }
                            }
                        },
                    }
                }
            }
        }
    },
}

ORACLE_COUNT: Any = 1  # conforms: integer
BUGGY_COUNT: Any = "oops"  # drift: string where the contract promises an integer


def _make_app(count_value: Any) -> Flask:
    app = Flask(__name__)

    @app.get("/openapi.json")
    def spec() -> Any:  # noqa: ANN401
        return jsonify(SCHEMA)

    @app.get("/widget")
    def widget() -> Any:  # noqa: ANN401
        return jsonify({"count": count_value})

    return app


def conforms_to_contract(count_value: Any) -> bool:
    """Fuzz `GET /widget` of an app returning `count_value` against the schema.
    Return True if every generated response validates, False on contract drift."""
    app = _make_app(count_value)
    schema = schemathesis.openapi.from_wsgi("/openapi.json", app)
    operation = schema["/widget"]["GET"]

    @settings(max_examples=10, deadline=None, suppress_health_check=list(HealthCheck))
    @given(case=operation.as_strategy())
    def run(case: Any) -> None:  # noqa: ANN401
        case.call_and_validate()

    try:
        run()
    except FailureGroup:
        return False
    return True


def run_self_test() -> int:
    failures = 0
    if not conforms_to_contract(ORACLE_COUNT):
        failures += 1
        print("FAIL: conformant app flagged as drifting", file=sys.stderr)
    if conforms_to_contract(BUGGY_COUNT):
        failures += 1
        print("FAIL: contract drift (string count) was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (conformant app validates; string-typed count drift caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OpenAPI contract-drift fuzz harness")
    parser.add_argument("--self-test", action="store_true")
    parser.parse_args(argv)
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
