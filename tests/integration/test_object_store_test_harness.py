import pytest

from harnesses.integration import object_store_test_harness as h

pytestmark = pytest.mark.integration


def test_utf8_text_round_trips(s3_client, s3_bucket) -> None:
    store = h.BlobStore(s3_client, s3_bucket)
    store.save("note", h.TEXT)
    assert store.load("note") == h.TEXT


def test_ascii_round_trips(s3_client, s3_bucket) -> None:
    store = h.BlobStore(s3_client, s3_bucket)
    store.save("note", "hello")
    assert store.load("note") == "hello"
