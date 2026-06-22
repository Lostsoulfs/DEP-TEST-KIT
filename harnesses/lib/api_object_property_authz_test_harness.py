#!/usr/bin/env python3
"""API response field allow-listing harness (pydantic).

OWASP API Security Top 10 2023 -- API3 Broken Object Property Level Authorization
(the merge of Excessive Data Exposure + Mass Assignment).

WHY: The cheapest, most common API leak: an endpoint serializes the whole database record
straight to JSON, so `password_hash`, `ssn`, and internal flags ride along to the client. A
test that checks "does the response contain id and name?" passes whether or not the
sensitive fields leak. Only an explicit response allow-list (return ONLY the public fields)
catches it.

HOW: `AllowListSerializer` is the ORACLE -- it projects the record through a pydantic model
that declares only the public fields, so extra fields are dropped. `FullObjectSerializer` is
the planted defect -- it returns the raw record. `leaks_sensitive_fields` serializes a record
carrying secrets and reports whether any leaked: the oracle drops them, the full serializer
exposes them.

WHERE: lib/ -- dependency-backed (`pydantic`) but in-process, no service. Adds `pydantic` to
the `lib` extra (already in the repo).

Self-test:
    python harnesses/lib/api_object_property_authz_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

from pydantic import BaseModel

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["leaks_sensitive_fields"]

DOSSIER = {
    "name": "api_object_property_authz",
    "path": "harnesses/lib/api_object_property_authz_test_harness.py",
    "flavor": "lib",
    "dependency": "pydantic",
    "standard": "OWASP API Security Top 10 2023 - API3 Broken Object Property Level Authorization",
    "failure_class": (
        "Serializing the whole record -> excessive data exposure (password_hash, ssn leak)"
    ),
    "oracle": "AllowListSerializer.serialize - project through a public-fields pydantic model",
    "buggy": "FullObjectSerializer.serialize - return the raw record",
    "planted_mutant": "serialize a record with password_hash/ssn; full serializer leaks them",
    "proof_file": "tests/lib/test_api_object_property_authz_proof.py",
    "vacuity_targets": ["leaks_sensitive_fields"],
    "commands": ["python harnesses/lib/api_object_property_authz_test_harness.py --self-test"],
    "known_limits": (
        "covers the output (exposure) side; the input (mass-assignment) side is "
        "tool_arg_validation"
    ),
    "related": ["tool_arg_validation (mass assignment)", "sensitive_disclosure"],
}

# What the database layer returns -- including fields the client must never see.
_DB_RECORD = {
    "id": 1,
    "name": "Alice",
    "password_hash": "$2b$12$abcdefghijklmnopqrstuv",
    "ssn": "123-45-6789",
    "is_admin": False,
}
_SENSITIVE = {"password_hash", "ssn", "is_admin"}


class PublicUser(BaseModel):
    id: int
    name: str


class AllowListSerializer:
    """ORACLE: project the record through the public-fields model (extra fields dropped)."""

    def serialize(self, record: dict) -> dict:
        return PublicUser(**record).model_dump()


class FullObjectSerializer:
    """BUGGY: return the raw record -- every column rides along."""

    def serialize(self, record: dict) -> dict:
        return dict(record)  # BUG: excessive data exposure


def returns_public_fields(make_serializer: Callable[[], object]) -> bool:
    out = make_serializer().serialize(_DB_RECORD)
    return out.get("id") == 1 and out.get("name") == "Alice"


def leaks_sensitive_fields(make_serializer: Callable[[], object]) -> bool:
    """True == a sensitive field appeared in the serialized output (the bug)."""
    out = make_serializer().serialize(_DB_RECORD)
    return any(field in out for field in _SENSITIVE)


def run_self_test() -> int:
    failures = 0
    if not returns_public_fields(AllowListSerializer):
        failures += 1
        print("FAIL: oracle dropped a public field", file=sys.stderr)
    if leaks_sensitive_fields(AllowListSerializer):
        failures += 1
        print("FAIL: oracle leaked a sensitive field", file=sys.stderr)
    if not leaks_sensitive_fields(FullObjectSerializer):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: full-object serializer leak was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print(
        "self-test: OK (allow-list serializer drops secrets; full-object serializer caught "
        "leaking)"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="API response field allow-listing harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
