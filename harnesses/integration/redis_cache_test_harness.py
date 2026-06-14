#!/usr/bin/env python3
"""Redis TTL cache integration test harness (testcontainers).

WHY:   A cache that "expires" entries is only correct if the expiry is actually set on
       the server. A store that writes with a plain SET (no EX) passes every in-memory
       mock test — the mock has no concept of TTL — and then leaks stale data forever
       in production. Only a real Redis reports the key's true time-to-live.

HOW:   `TTLCache.put` writes with `SET key val EX ttl`; `BuggyTTLCache` ships the SAME
       code path but drops the expiry (plain SET) — the "forgot the TTL" defect. The
       proof reads `TTL key` from real Redis: the correct cache reports a positive TTL,
       the buggy one reports -1 (no expiry). No sleeping required.

WHERE: integration/ — needs a real ephemeral Redis via Docker. Uses `redis` (added to
       the `integration` extra). Isolation (research T2): one session-scoped container,
       a logical DB index per pytest-xdist worker, flushed around each test. The client
       is injected by `tests/integration/conftest.py`.

Self-test:
  python harnesses/integration/redis_cache_test_harness.py --self-test
  (deferred: the real proof runs under `pytest -m integration`, which needs Docker)
"""

from __future__ import annotations

import argparse
import shutil
import sys


class TTLCache:
    set_ttl = True

    def __init__(self, client) -> None:
        # client is a redis.Redis (decode_responses=True), injected by the fixtures.
        self.client = client

    def put(self, key: str, value: str, ttl: int) -> None:
        if self.set_ttl:
            self.client.set(key, value, ex=ttl)
        else:
            self.client.set(key, value)

    def get(self, key: str):
        return self.client.get(key)

    def ttl(self, key: str) -> int:
        # Redis returns the remaining TTL in seconds, or -1 if the key has no expiry.
        return self.client.ttl(key)


class BuggyTTLCache(TTLCache):
    """Identical cache, but it forgot to set the expiry — keys never die."""

    set_ttl = False


def run_self_test() -> int:
    print(
        "self-test: DEFERRED -- integration harness. Run `pytest -m integration` "
        f"(needs Docker). docker on PATH: {shutil.which('docker') is not None}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Redis TTL cache integration harness")
    parser.add_argument("--self-test", action="store_true")
    parser.parse_args(argv)
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
