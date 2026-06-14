"""Proof: a real Elasticsearch exposes the missing refresh. The oracle (refresh)
is read-after-write consistent; the buggy store (no refresh) is not."""

import pytest

from harnesses.integration import elasticsearch_index_test_harness as h

pytestmark = pytest.mark.integration


def test_proof_buggy_inconsistent(es_client) -> None:
    store = h.BuggySearchStore(es_client)
    assert h.read_after_write_consistent(store) is False


def test_proof_oracle_consistent(es_client) -> None:
    store = h.SearchStore(es_client)
    assert h.read_after_write_consistent(store) is True
