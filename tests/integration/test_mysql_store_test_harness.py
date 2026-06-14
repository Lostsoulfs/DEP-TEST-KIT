import pytest

from harnesses.integration import mysql_store_test_harness as h

pytestmark = pytest.mark.integration

EMOJI = "🌈"  # a 4-byte UTF-8 character


def test_utf8mb4_round_trips_4byte_char(mysql_conn) -> None:
    store = h.NoteStore(mysql_conn)
    store.ensure_schema()
    store.save(EMOJI)
    assert store.first() == EMOJI


def test_ascii_round_trips(mysql_conn) -> None:
    store = h.NoteStore(mysql_conn)
    store.ensure_schema()
    store.save("hello")
    assert store.first() == "hello"
