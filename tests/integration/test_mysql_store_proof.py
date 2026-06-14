"""Proof: only a real MySQL reveals the utf8mb3 charset trap.

The buggy store declares utf8mb3, which cannot hold a 4-byte character — a real MySQL
rejects it (error 1366) under strict mode. The correct store (utf8mb4) round-trips it.
A mock store would accept the string in both cases.
"""

import pymysql
import pytest

from harnesses.integration import mysql_store_test_harness as h

pytestmark = pytest.mark.integration

EMOJI = "🌈"


def test_proof_utf8mb3_rejects_4byte_char(mysql_conn) -> None:
    store = h.BuggyNoteStore(mysql_conn)
    store.ensure_schema()
    with pytest.raises(pymysql.err.MySQLError):
        store.save(EMOJI)


def test_proof_utf8mb4_accepts_what_buggy_rejects(mysql_conn) -> None:
    store = h.NoteStore(mysql_conn)
    store.ensure_schema()
    store.save(EMOJI)
    assert store.first() == EMOJI
