"""Proof: only a real Redis reveals the missing-expiry bug.

The buggy cache writes with a plain SET, so the key never expires — TTL reports -1.
The correct cache sets EX and TTL reports a positive value. An in-memory mock models
no TTL at all, so it would catch neither.
"""

import pytest

from harnesses.integration import redis_cache_test_harness as h

pytestmark = pytest.mark.integration


def test_proof_buggy_cache_has_no_expiry(redis_client) -> None:
    cache = h.BuggyTTLCache(redis_client)
    cache.put("k", "v", ttl=100)
    assert cache.ttl("k") == -1  # key exists but has no expiry — the planted bug


def test_proof_correct_cache_sets_expiry(redis_client) -> None:
    cache = h.TTLCache(redis_client)
    cache.put("k", "v", ttl=100)
    assert cache.ttl("k") > 0
