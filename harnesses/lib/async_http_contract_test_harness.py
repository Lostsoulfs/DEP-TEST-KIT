#!/usr/bin/env python3
"""Async HTTP transient-fault contract harness (respx + httpx).

WHY:   A client that "works" against a live, healthy endpoint can have no resilience
       at all: the first 503 or read timeout from a flaky upstream takes it down.
       You cannot prove the retry path with a mock that always returns 200, and you
       cannot reliably provoke a real timeout in CI. respx lets you inject the exact
       transient fault deterministically and assert the client recovers.

HOW:   Two async httpx clients fetch a URL. The oracle `fetch_with_retry` retries on
       a 503 response and on transport errors (timeouts/connection drops), returning
       the body once the upstream recovers. `fetch_no_retry` issues a single request
       and surfaces the first fault — the plausible bug. respx serves the fault on
       call 1 and a 200 on call 2; the harness reports whether the client survived.

WHERE: lib/ — dependency-backed (respx, httpx) but fully in-process. The async code
       is driven via `asyncio.run`, so no event-loop plugin is needed and the proof
       test stays synchronous. Adds `respx` + `httpx` to the `lib` extra.

Self-test:
  python harnesses/lib/async_http_contract_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Awaitable, Callable

import httpx
import respx

URL = "https://upstream.test/resource"
Fetch = Callable[[str], Awaitable[str]]


# --- ORACLE: retries transient 503s and transport errors ------------------------
async def fetch_with_retry(url: str, attempts: int = 3) -> str:
    async with httpx.AsyncClient(timeout=1.0) as client:
        last_exc: Exception | None = None
        for _ in range(attempts):
            try:
                resp = await client.get(url)
            except httpx.TransportError as exc:  # timeouts, connect/read errors
                last_exc = exc
                continue
            if resp.status_code == 503:  # transient: upstream temporarily down
                continue
            resp.raise_for_status()
            return resp.text
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("exhausted retries on 503")


# --- BUGGY: one shot, no transient handling -------------------------------------
async def fetch_no_retry(url: str, attempts: int = 3) -> str:
    async with httpx.AsyncClient(timeout=1.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text


def _one_fault_then_ok(fault: object) -> Callable[[httpx.Request], httpx.Response]:
    """respx side_effect: raise/return `fault` on the first call, then 200 'ok'."""
    state = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        i = state["n"]
        state["n"] += 1
        if i == 0:
            if isinstance(fault, Exception):
                raise fault
            return fault  # an httpx.Response
        return httpx.Response(200, text="ok")

    return handler


def survives_transient(fetch: Fetch, fault: object) -> bool:
    """Return True if `fetch` recovers from a single transient `fault` then a 200."""

    async def run() -> str:
        with respx.mock(assert_all_called=False) as router:
            router.get(URL).mock(side_effect=_one_fault_then_ok(fault))
            return await fetch(URL)

    try:
        return asyncio.run(run()) == "ok"
    except Exception:
        return False


# The two transient faults a real client must shrug off.
FAULTS: dict[str, object] = {
    "503": httpx.Response(503),
    "timeout": httpx.ReadTimeout("slow upstream"),
}


def run_self_test() -> int:
    failures = 0
    for name, fault in FAULTS.items():
        if not survives_transient(fetch_with_retry, fault):
            failures += 1
            print(f"FAIL: oracle did not recover from transient {name}", file=sys.stderr)
        if survives_transient(fetch_no_retry, fault):
            failures += 1
            print(f"FAIL: buggy no-retry client unexpectedly survived {name}", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (oracle retries 503+timeout; no-retry client caught on both)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Async HTTP transient-fault harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
