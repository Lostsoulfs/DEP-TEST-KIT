#!/usr/bin/env python3
"""MySQL charset integration test harness (testcontainers).

WHY:   "utf8" in MySQL is a historical trap: the `utf8`/`utf8mb3` charset stores only
       up to 3-byte sequences, so any 4-byte character (emoji, many CJK extensions)
       is rejected or mangled. A store declared with `utf8mb3` passes every mock and
       every ASCII test, then errors or corrupts the first time a user types an emoji.
       Only a real MySQL enforces the charset width.

HOW:   `NoteStore` declares its column `CHARACTER SET utf8mb4` (true 4-byte UTF-8);
       `BuggyNoteStore` ships the SAME code with `utf8mb3` — the classic "use utf8"
       defect. The proof saves a 4-byte character: the correct store round-trips it,
       the buggy store raises a MySQL error (1366, Incorrect string value) under the
       server's strict mode.

WHERE: integration/ — needs a real ephemeral MySQL via Docker. Uses `pymysql` (added
       to the `integration` extra). MySQL DDL auto-commits, so isolation is DROP+CREATE
       per test rather than a rollback (research T2). The connection is injected by
       `tests/integration/conftest.py`.

Self-test:
  python harnesses/integration/mysql_store_test_harness.py --self-test
  (deferred: the real proof runs under `pytest -m integration`, which needs Docker)
"""

from __future__ import annotations

import argparse
import shutil
import sys

CORRECT_CHARSET = "utf8mb4"
# BUGGY: utf8mb3 cannot hold a 4-byte character — only a real MySQL exposes this.
BUGGY_CHARSET = "utf8mb3"


class NoteStore:
    charset = CORRECT_CHARSET

    def __init__(self, conn) -> None:
        # conn is a pymysql connection, injected by the fixtures.
        self.conn = conn

    def ensure_schema(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute("DROP TABLE IF EXISTS notes")
            cur.execute(
                f"CREATE TABLE notes (id INT AUTO_INCREMENT PRIMARY KEY, "
                f"body TEXT CHARACTER SET {self.charset}) CHARACTER SET {self.charset}"
            )
        self.conn.commit()

    def save(self, body: str) -> None:
        with self.conn.cursor() as cur:
            cur.execute("INSERT INTO notes (body) VALUES (%s)", (body,))
        self.conn.commit()

    def first(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT body FROM notes ORDER BY id LIMIT 1")
            row = cur.fetchone()
            return row[0] if row else None


class BuggyNoteStore(NoteStore):
    """Identical store, but declared utf8mb3 — the planted bug."""

    charset = BUGGY_CHARSET


def run_self_test() -> int:
    print(
        "self-test: DEFERRED -- integration harness. Run `pytest -m integration` "
        f"(needs Docker). docker on PATH: {shutil.which('docker') is not None}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MySQL charset integration harness")
    parser.add_argument("--self-test", action="store_true")
    parser.parse_args(argv)
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
