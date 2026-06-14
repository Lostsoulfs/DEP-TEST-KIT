"""Paired test: on a healthy link (no toxic) both clients round-trip identically — the
bug only manifests under chaos. Establishes the oracle's normal behaviour so the proof's
failure is attributable to the injected fault, not a broken setup.
"""

import pytest

from harnesses.integration import network_chaos_test_harness as h

pytestmark = pytest.mark.integration


def test_resilient_client_round_trips_when_healthy(redis_via_proxy, chaos_proxy) -> None:
    client = h.ResilientClient(redis_via_proxy)
    client.set("k", "v")
    assert client.get("k") == "v"


def test_fragile_client_round_trips_when_healthy(redis_via_proxy, chaos_proxy) -> None:
    client = h.FragileClient(redis_via_proxy)
    client.set("k2", "v2")
    assert client.get("k2") == "v2"
