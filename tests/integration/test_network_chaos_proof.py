"""Proof: a missing socket timeout turns a stalled upstream into a slow, confusing
failure instead of a fast, catchable one. Only a real proxy that can stall the
connection (Toxiproxy) reveals it — an in-memory mock answers instantly.

The `timeout` toxic stops data and closes the connection after 2s. The resilient client
(socket_timeout=0.5) raises TimeoutError at 0.5s; the fragile client (no timeout) blocks
the full 2s and then gets a ConnectionError when the proxy drops it. Distinct, deterministic
exception types — not a timing assertion.
"""

import pytest

from harnesses.integration import network_chaos_test_harness as h

pytestmark = pytest.mark.integration


def _stall(proxy) -> None:
    proxy.add_toxic(name="stall", type="timeout", attributes={"timeout": 2000})


def test_proof_resilient_client_fails_fast(redis_via_proxy, chaos_proxy) -> None:
    import redis

    proxy, _ = chaos_proxy
    _stall(proxy)
    client = h.ResilientClient(redis_via_proxy)  # socket_timeout = 0.5s
    # Its own read timeout fires first -> a fast, catchable TimeoutError.
    with pytest.raises(redis.exceptions.TimeoutError):
        client.get("k")


def test_proof_fragile_client_suffers_connection_drop(redis_via_proxy, chaos_proxy) -> None:
    import redis

    proxy, _ = chaos_proxy
    _stall(proxy)
    client = h.FragileClient(redis_via_proxy)  # the planted bug: no socket timeout
    # No client-side timeout: it blocks for the whole stall, then the proxy closes the
    # connection -> a ConnectionError (slow, confusing), never a clean fast TimeoutError.
    with pytest.raises(redis.exceptions.ConnectionError):
        client.get("k")
