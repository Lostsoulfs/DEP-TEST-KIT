import pytest

from harnesses.integration import elasticsearch_index_test_harness as h

pytestmark = pytest.mark.integration


def test_oracle_finds_indexed_doc(es_client) -> None:
    store = h.SearchStore(es_client)
    store.add("doc-1", "hello world")
    assert "doc-1" in store.search("hello")
