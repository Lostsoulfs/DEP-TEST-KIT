#!/usr/bin/env python3
"""Elasticsearch read-after-write integration test harness (testcontainers).

WHY: Elasticsearch is near-real-time: a freshly indexed document is NOT
searchable until a refresh. Code tested against a mock (which "indexes" into a
dict) passes its read-after-write assertion, then intermittently returns empty
results in production. Only a real ES exposes the missing refresh
(a consistency/correctness failure a mock cannot model).

HOW: `SearchStore.add` indexes with `refresh="wait_for"`, so an immediate search
finds the document. `BuggySearchStore.add` omits the refresh — the same
immediate search misses it. `read_after_write_consistent` returns whether the
just-written doc is searchable; the proof shows oracle True / buggy False.

WHERE: integration/ — needs a real ephemeral Elasticsearch (Docker). The
`elasticsearch` client is injected by `tests/integration/conftest.py`
(`es_client`); adds `elasticsearch` to the integration extra.

Self-test:
    python harnesses/integration/elasticsearch_index_test_harness.py --self-test
    (deferred: the real proof runs under `pytest -m integration`, which needs Docker)
"""

from __future__ import annotations

import argparse
import shutil
import sys


class SearchStore:
    """ORACLE: indexes with a refresh so read-after-write is consistent."""

    def __init__(self, client, index: str = "docs") -> None:
        self.client = client          # elasticsearch.Elasticsearch, injected
        self.index = index

    def add(self, doc_id: str, text: str) -> None:
        self.client.index(index=self.index, id=doc_id, document={"text": text}, refresh="wait_for")

    def search(self, term: str) -> list[str]:
        res = self.client.search(index=self.index, query={"match": {"text": term}})
        return [hit["_id"] for hit in res["hits"]["hits"]]


class BuggySearchStore(SearchStore):
    """BUGGY: indexes WITHOUT a refresh; the document isn't searchable yet."""

    def add(self, doc_id: str, text: str) -> None:
        self.client.index(index=self.index, id=doc_id, document={"text": text})  # BUG: no refresh


def read_after_write_consistent(store: SearchStore, doc_id: str = "d1",
                                term: str = "hello") -> bool:
    """True == the just-indexed document is immediately searchable."""
    store.add(doc_id, term)
    return doc_id in store.search(term)


def run_self_test() -> int:
    print(
        "self-test: DEFERRED -- integration harness. "
        "Run `pytest -m integration` (needs Docker). "
        f"docker on PATH: {shutil.which('docker') is not None}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Elasticsearch read-after-write integration harness")
    parser.add_argument("--self-test", action="store_true")
    parser.parse_args(argv)
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
