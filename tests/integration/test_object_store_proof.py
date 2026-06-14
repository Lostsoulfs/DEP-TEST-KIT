"""Proof: only a real S3 round-trip reveals the encoding corruption.

The buggy store writes Latin-1 bytes; read back under the UTF-8 contract they are
invalid and raise UnicodeDecodeError. The correct store round-trips the text. A mock
that hands back the original `str` would never expose the bad bytes.
"""

import pytest

from harnesses.integration import object_store_test_harness as h

pytestmark = pytest.mark.integration


def test_proof_buggy_store_writes_corrupt_bytes(s3_client, s3_bucket) -> None:
    store = h.BuggyBlobStore(s3_client, s3_bucket)
    store.save("note", h.TEXT)
    with pytest.raises(UnicodeDecodeError):
        store.load("note")  # Latin-1 bytes are not valid UTF-8


def test_proof_correct_store_round_trips(s3_client, s3_bucket) -> None:
    store = h.BlobStore(s3_client, s3_bucket)
    store.save("note", h.TEXT)
    assert store.load("note") == h.TEXT
