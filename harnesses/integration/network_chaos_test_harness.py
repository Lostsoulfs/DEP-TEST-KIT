#!/usr/bin/env python3
"""Network-chaos (missing socket timeout) integration harness — Toxiproxy + testcontainers.

WHY:   A Redis client without a socket timeout is fine on a healthy LAN and catastrophic
       on a flaky one. When the server accepts the connection but then stalls (a hung
       node, a saturated proxy), a client with no read timeout blocks indefinitely and
       the stall propagates up as an unbounded hang — no in-memory mock can surface this.
       A client WITH a read timeout turns the same stall into a fast, catchable
       TimeoutError it can retry or fail over on. The defect is a one-line omission:
       `socket_timeout` left unset.

HOW:   Both clients talk to Redis THROUGH a Toxiproxy proxy. The proof injects a
       `timeout` toxic (stop data, then close the connection after N ms) to emulate a
       stalled upstream. The RESILIENT client (socket_timeout set) raises
       `redis.TimeoutError` — its own timeout fires first. The FRAGILE client (no
       socket_timeout) blocks until the proxy drops the connection and surfaces a
       `redis.ConnectionError` instead — a slower, more confusing failure. The two
       outcomes are deterministic (distinct exception types), not a flaky timing race.

WHERE: integration/ — needs real ephemeral Redis + Toxiproxy via Docker on a shared
       network. Uses `redis` + `toxiproxy-python` (integration extra). The proxy/client
       fixtures live in `tests/integration/conftest.py`.

Self-test:
  python harnesses/integration/network_chaos_test_harness.py --self-test
  (deferred: the real proof runs under `pytest -m integration`, which needs Docker)
"""

from __future__ import annotations

import argparse
import shutil
import sys


class ResilientClient:
    """Sets a socket timeout, so a stalled upstream fails fast and catchably."""

    socket_timeout: float | None = 0.5  # seconds

    def __init__(self, factory) -> None:
        # factory(socket_timeout) -> redis.Redis, supplied by the fixtures so this module
        # imports no redis symbols at load time (deferred, like the other integration ones).
        self._client = factory(self.socket_timeout)

    def set(self, key: str, value: str) -> None:
        self._client.set(key, value)

    def get(self, key: str):
        return self._client.get(key)


class FragileClient(ResilientClient):
    """Identical client, but it forgot the socket timeout — a stall becomes a hang."""

    socket_timeout = None


def run_self_test() -> int:
    print(
        "self-test: DEFERRED -- integration harness. Run `pytest -m integration` "
        f"(needs Docker). docker on PATH: {shutil.which('docker') is not None}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Network-chaos integration harness")
    parser.add_argument("--self-test", action="store_true")
    parser.parse_args(argv)
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
