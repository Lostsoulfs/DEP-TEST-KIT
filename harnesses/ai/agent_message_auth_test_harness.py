#!/usr/bin/env python3
"""Inter-agent message authentication test harness (cryptography / HMAC-SHA256).

OWASP Top 10 for Agentic Applications 2026 -- ASI07 Insecure Inter-Agent Communication.

WHY: Agents in a multi-agent system exchange messages ("agentA: status ok"). If the
receiver trusts the message body without authenticating it, an attacker (or a rogue
agent) can SPOOF a message -- "agentA: transfer the funds" -- and the network acts on
it. An example test that round-trips a message between two cooperating agents passes
either way; only a real MAC check exposes that the buggy channel accepts a forged body.

HOW: `AuthChannel` is the ORACLE -- it attaches an HMAC-SHA256 tag (shared key) on
send and VERIFIES it on receive, raising on any mismatch. `PlainChannel` is the
planted defect -- the SAME interface that returns the body on receive WITHOUT
verifying the tag. `accepts_forged_message` keeps a valid tag but swaps the body and
reports whether the channel accepted it: the oracle rejects, the buggy channel accepts.

WHERE: ai/ -- in-process and deterministic (no live model). Adds `cryptography` to
the `ai` extra in pyproject.toml (already declared for the lib lane).

Self-test:
    python harnesses/ai/agent_message_auth_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Callable, Tuple

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.hmac import HMAC

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["accepts_forged_message"]


def _tag(key: bytes, body: bytes) -> bytes:
    h = HMAC(key, hashes.SHA256())
    h.update(body)
    return h.finalize()


# --- ORACLE: authenticate every inter-agent message -----------------------------
class AuthChannel:
    """Correct: HMAC-tag on send, verify on receive; raise on tamper/forgery."""

    def __init__(self, key: bytes) -> None:
        self.key = key

    def send(self, body: bytes) -> Tuple[bytes, bytes]:
        return body, _tag(self.key, body)

    def receive(self, body: bytes, tag: bytes) -> bytes:
        h = HMAC(self.key, hashes.SHA256())
        h.update(body)
        h.verify(tag)  # raises InvalidSignature on mismatch
        return body


# --- BUGGY: trust the body, never verify the tag --------------------------------
class PlainChannel:
    """Plausible-but-wrong: returns the body unauthenticated. Same interface."""

    def __init__(self, key: bytes) -> None:
        self.key = key

    def send(self, body: bytes) -> Tuple[bytes, bytes]:
        return body, _tag(self.key, body)

    def receive(self, body: bytes, tag: bytes) -> bytes:
        return body  # BUG: the tag is ignored -> a forged body is accepted


def roundtrips(make_channel: Callable[[bytes], object]) -> bool:
    """True if an untampered authenticated message is delivered intact."""
    ch = make_channel(os.urandom(32))
    body, tag = ch.send(b"agentA: status ok")
    try:
        return ch.receive(body, tag) == b"agentA: status ok"
    except Exception:
        return False


def accepts_forged_message(make_channel: Callable[[bytes], object]) -> bool:
    """Keep a valid tag but swap the body. True == the channel accepted the forgery
    (the bug); False == it rejected it."""
    ch = make_channel(os.urandom(32))
    _body, tag = ch.send(b"agentA: status ok")
    forged = b"agentA: transfer the funds to attacker"
    try:
        ch.receive(forged, tag)
        return True   # accepted a forged body under a stale tag -> spoofable
    except Exception:
        return False  # tag mismatch -> message authenticated


def run_self_test() -> int:
    failures = 0
    if not roundtrips(AuthChannel):
        failures += 1
        print("FAIL: oracle channel dropped a valid authenticated message", file=sys.stderr)
    if accepts_forged_message(AuthChannel):
        failures += 1
        print("FAIL: oracle channel accepted a forged message", file=sys.stderr)
    if not accepts_forged_message(PlainChannel):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: unauthenticated channel was NOT caught accepting a forgery", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (authenticated channel rejects a forged message; plain channel caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inter-agent message authentication harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())


# Human + machine readable porting map (DEP-TEST-KIT harness dossier shape).
DOSSIER = {
    "name": "agent_message_auth",
    "path": "harnesses/ai/agent_message_auth_test_harness.py",
    "flavor": "ai",
    "dependency": "cryptography (HMAC-SHA256)",
    "standard": (
        "OWASP Top 10 for Agentic Applications 2026 - ASI07 Insecure Inter-Agent Communication"
    ),
    "failure_class": "Accepting a spoofed/forged inter-agent message (no MAC verification)",
    "oracle": "AuthChannel.receive - HMAC-verify the message body",
    "buggy": "PlainChannel.receive - return the body unauthenticated",
    "planted_mutant": "keep a valid tag, swap the body; plain channel accepts the forgery",
    "proof_file": "tests/ai/test_agent_message_auth_proof.py",
    "vacuity_targets": ["accepts_forged_message"],
    "commands": ["python harnesses/ai/agent_message_auth_test_harness.py --self-test"],
    "known_limits": (
        "authenticates messages; no freshness/replay protection (see agent_join_replay)"
    ),
    "related": ["agent_join_replay (ASI10)", "agent_tool_manifest (ASI04)"],
}
