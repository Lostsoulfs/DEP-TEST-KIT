"""Proof: only a real MongoDB reveals the missing unique index.

The buggy store never creates the unique index, so a real cluster accepts a duplicate
email — count becomes 2. The correct store raises DuplicateKeyError. A mock would
enforce whatever the test author imagined, not the real index.
"""

import pytest
from pymongo.errors import DuplicateKeyError

from harnesses.integration import mongo_store_test_harness as h

pytestmark = pytest.mark.integration


def test_proof_buggy_store_allows_duplicate(mongo_db) -> None:
    store = h.BuggyUserStore(mongo_db)
    store.ensure_schema()
    store.add("dup@example.com")
    store.add("dup@example.com")
    assert store.count() == 2  # the planted bug, made visible by a real DB


def test_proof_correct_store_blocks_what_buggy_allows(mongo_db) -> None:
    store = h.UserStore(mongo_db)
    store.ensure_schema()
    store.add("dup@example.com")
    with pytest.raises(DuplicateKeyError):
        store.add("dup@example.com")
