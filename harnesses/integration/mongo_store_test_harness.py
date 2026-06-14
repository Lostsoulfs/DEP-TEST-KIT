#!/usr/bin/env python3
"""MongoDB unique-index integration test harness (testcontainers).

WHY:   MongoDB will happily store duplicate documents unless a UNIQUE index exists —
       there is no schema to lean on. A store that "dedupes by email" but never creates
       the unique index passes every mock test and silently writes duplicates against a
       real cluster. Only a real MongoDB enforces (or fails to enforce) the index.

HOW:   `UserStore.ensure_schema` creates a unique index on `email`; `BuggyUserStore`
       ships the SAME code but skips the index — the "forgot the unique index" defect.
       The proof inserts the same email twice: the correct store raises
       `DuplicateKeyError`, the buggy store ends with two documents.

WHERE: integration/ — needs a real ephemeral MongoDB via Docker. Uses `pymongo` (added
       to the `integration` extra). Isolation (research T2): one session-scoped
       container, a logical database per pytest-xdist worker, collection dropped around
       each test. The database handle is injected by `tests/integration/conftest.py`.

Self-test:
  python harnesses/integration/mongo_store_test_harness.py --self-test
  (deferred: the real proof runs under `pytest -m integration`, which needs Docker)
"""

from __future__ import annotations

import argparse
import shutil
import sys


class UserStore:
    unique = True

    def __init__(self, db) -> None:
        # db is a pymongo Database, injected by the fixtures.
        self.col = db["users"]

    def ensure_schema(self) -> None:
        if self.unique:
            self.col.create_index("email", unique=True)

    def add(self, email: str) -> None:
        self.col.insert_one({"email": email})

    def count(self) -> int:
        return self.col.count_documents({})


class BuggyUserStore(UserStore):
    """Identical store, but it never creates the unique index — the planted bug."""

    unique = False


def run_self_test() -> int:
    print(
        "self-test: DEFERRED -- integration harness. Run `pytest -m integration` "
        f"(needs Docker). docker on PATH: {shutil.which('docker') is not None}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MongoDB unique-index integration harness")
    parser.add_argument("--self-test", action="store_true")
    parser.parse_args(argv)
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
