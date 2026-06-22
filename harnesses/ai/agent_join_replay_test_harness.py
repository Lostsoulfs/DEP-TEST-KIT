#!/usr/bin/env python3
"""Agent join-token replay test harness (cryptography / Ed25519 + nonce + expiry).

OWASP Top 10 for Agentic Applications 2026 -- ASI10 Rogue Agents.

WHY: A rogue (or compromised) agent doesn't need to forge a signature -- it can REPLAY
a previously-valid, correctly-signed join/authorization token to re-enter the agent
network or re-trigger an irreversible action. A test that checks "is the signature
valid?" passes on the replay too, because the signature IS valid. 2026 guidance for
agentic systems is explicit: authorization artifacts for irreversible operations must be
short-lived AND single-use (nonce + expiry). Only a stateful replay check exposes the
difference; a stateless signature check (and a mock) cannot.

HOW: `ReplayGuardedAdmission` is the ORACLE -- it Ed25519-verifies the token, enforces
the expiry against an injected clock, and consumes a single-use nonce (rejecting any
nonce it has already seen). `NoReplayAdmission` is the planted defect -- it verifies the
SAME signature (so this isn't a "forgot to check the sig" bug) but ignores the nonce and
expiry. `admits_replayed_token` admits a valid token once, then submits the IDENTICAL
token again: the oracle rejects the second, the buggy admission accepts it.

WHERE: ai/ -- in-process, deterministic (injected clock, no live model). Adds
`cryptography` to the `ai` extra (already declared for the lib lane).

Self-test:
    python harnesses/ai/agent_join_replay_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Callable, Tuple

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["admits_replayed_token"]

# Human + machine readable porting map (DEP-TEST-KIT harness dossier shape).
DOSSIER = {
    "name": "agent_join_replay",
    "path": "harnesses/ai/agent_join_replay_test_harness.py",
    "flavor": "ai",
    "dependency": "cryptography (Ed25519)",
    "standard": "OWASP Top 10 for Agentic Applications 2026 — ASI10 Rogue Agents",
    "failure_class": "Replay of a previously-valid signed agent join/authorization token",
    "oracle": "ReplayGuardedAdmission.admit — verify sig + expiry + single-use nonce",
    "buggy": "NoReplayAdmission.admit — verifies the signature but ignores nonce/expiry",
    "planted_mutant": "submit an identical, validly-signed token twice; buggy admits the replay",
    "proof_file": "tests/ai/test_agent_join_replay_proof.py",
    "vacuity_targets": ["admits_replayed_token"],
    "commands": ["python harnesses/ai/agent_join_replay_test_harness.py --self-test"],
    "known_limits": "in-memory nonce store; production needs a shared/persistent replay cache",
    "related": ["agent_message_auth (ASI07)", "agent_tool_manifest (ASI04)", "keycloak_oidc"],
}

_NOW = 1_000_000  # injected 'current time' for deterministic expiry tests


def _make_token(exp: int = _NOW + 60, nonce: str = "n-1") -> Tuple[Ed25519PublicKey, bytes, bytes]:
    priv = Ed25519PrivateKey.generate()
    payload = json.dumps({"agent": "worker-7", "nonce": nonce, "exp": exp},
                         sort_keys=True).encode()
    return priv.public_key(), payload, priv.sign(payload)


class ReplayGuardedAdmission:
    """ORACLE: verify signature, enforce expiry, consume a single-use nonce."""

    def __init__(self, public_key: Ed25519PublicKey, now: int = _NOW) -> None:
        self.public_key = public_key
        self.now = now
        self._seen: set[str] = set()

    def admit(self, payload: bytes, signature: bytes) -> bool:
        self.public_key.verify(signature, payload)  # raises InvalidSignature on tamper
        claims = json.loads(payload)
        if self.now > claims["exp"]:
            raise ValueError("expired join token")
        if claims["nonce"] in self._seen:
            raise ValueError("replayed nonce")
        self._seen.add(claims["nonce"])
        return True


class NoReplayAdmission:
    """BUGGY: verifies the signature but never tracks the nonce or checks expiry."""

    def __init__(self, public_key: Ed25519PublicKey, now: int = _NOW) -> None:
        self.public_key = public_key
        self.now = now

    def admit(self, payload: bytes, signature: bytes) -> bool:
        # sig IS checked -- the bug is replay, not forgery
        self.public_key.verify(signature, payload)
        return True  # BUG: no nonce consumption, no expiry enforcement


def admits_valid_once(make_admission: Callable[[Ed25519PublicKey], object]) -> bool:
    pub, payload, sig = _make_token()
    try:
        return bool(make_admission(pub).admit(payload, sig))
    except Exception:
        return False


def admits_replayed_token(make_admission: Callable[[Ed25519PublicKey], object]) -> bool:
    """Admit a valid token, then submit the SAME token again. True == the replay was
    accepted (the bug); False == the second admission was rejected."""
    pub, payload, sig = _make_token()
    guard = make_admission(pub)
    try:
        guard.admit(payload, sig)        # first use: legitimate
    except Exception:
        return False
    try:
        guard.admit(payload, sig)        # replay of the identical signed token
        return True                      # accepted a replay -> rogue re-entry possible
    except Exception:
        return False                     # replay rejected


def run_self_test() -> int:
    failures = 0
    if not admits_valid_once(ReplayGuardedAdmission):
        failures += 1
        print("FAIL: oracle rejected a fresh, valid join token", file=sys.stderr)
    if admits_replayed_token(ReplayGuardedAdmission):
        failures += 1
        print("FAIL: oracle accepted a replayed token", file=sys.stderr)
    if not admits_replayed_token(NoReplayAdmission):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: no-replay admission was NOT caught accepting a replay", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (replay-guarded admission rejects a replay; no-replay variant caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Agent join-token replay harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
