import pytest
from pymongo.errors import DuplicateKeyError

from harnesses.integration import mongo_store_test_harness as h

pytestmark = pytest.mark.integration


def test_distinct_emails_accepted(mongo_db) -> None:
    store = h.UserStore(mongo_db)
    store.ensure_schema()
    store.add("a@example.com")
    store.add("b@example.com")
    assert store.count() == 2


def test_unique_index_blocks_duplicate(mongo_db) -> None:
    store = h.UserStore(mongo_db)
    store.ensure_schema()
    store.add("a@example.com")
    with pytest.raises(DuplicateKeyError):
        store.add("a@example.com")
