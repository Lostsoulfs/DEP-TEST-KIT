import pytest

from harnesses.integration import redis_cache_test_harness as h

pytestmark = pytest.mark.integration


def test_value_is_stored_and_readable(redis_client) -> None:
    cache = h.TTLCache(redis_client)
    cache.put("k", "v", ttl=100)
    assert cache.get("k") == "v"


def test_ttl_is_set(redis_client) -> None:
    cache = h.TTLCache(redis_client)
    cache.put("k", "v", ttl=100)
    assert cache.ttl("k") > 0
