#!/usr/bin/env python3
"""Agent tool-manifest integrity test harness (cryptography / Ed25519).

OWASP Top 10 for Agentic Applications 2026 -- ASI04 Agentic Supply Chain Compromise.

WHY: An agent loads its tools/plugins from a manifest. A test that just "loads the
manifest and checks a field" passes whether or not the manifest's SIGNATURE was
verified -- so a substituted or tampered manifest (a supply-chain compromise that
swaps a benign tool for a malicious one) sails straight through. Only real
signature verification exposes the difference; a mock can't model a forged signature.

HOW: `SignedToolLoader` is the ORACLE -- it verifies an Ed25519 signature over the
manifest bytes with a trusted public key before parsing, and raises on any tamper.
`UnverifiedToolLoader` is the planted defect -- the SAME interface that parses the
manifest WITHOUT checking the signature. `accepts_tampered_manifest` flips a tool
command in a validly-signed manifest and reports whether the loader accepted it:
the oracle rejects (InvalidSignature), the buggy loader accepts the swapped tool.

WHERE: ai/ -- in-process and deterministic (no live model). Adds `cryptography` to
the `ai` extra in pyproject.toml (already declared for the lib lane).

Self-test:
    python harnesses/ai/agent_tool_manifest_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["accepts_tampered_manifest"]


# --- ORACLE: verify the manifest signature before trusting it -------------------
class SignedToolLoader:
    """Correct: Ed25519-verify the manifest with a trusted key; raise on tamper."""

    def __init__(self, public_key: Ed25519PublicKey) -> None:
        self.public_key = public_key

    def load(self, manifest: bytes, signature: bytes) -> dict:
        self.public_key.verify(signature, manifest)  # raises InvalidSignature on tamper
        return json.loads(manifest)


# --- BUGGY: parse the manifest without verifying its signature -------------------
class UnverifiedToolLoader:
    """Plausible-but-wrong: loads whatever it is handed. Same interface."""

    def __init__(self, public_key: Ed25519PublicKey | None = None) -> None:
        self.public_key = public_key

    def load(self, manifest: bytes, signature: bytes) -> dict:
        return json.loads(manifest)  # BUG: signature is never checked


def _signed_manifest() -> tuple[Ed25519PublicKey, bytes, bytes]:
    priv = Ed25519PrivateKey.generate()
    manifest = json.dumps({"tool": "calculator", "command": "safe-calc"}).encode()
    return priv.public_key(), manifest, priv.sign(manifest)


def loads_valid_manifest(make_loader: Callable[[Ed25519PublicKey], object]) -> bool:
    """True if the loader accepts a correctly-signed manifest and parses it."""
    pub, manifest, signature = _signed_manifest()
    try:
        return make_loader(pub).load(manifest, signature).get("tool") == "calculator"
    except Exception:
        return False


def accepts_tampered_manifest(make_loader: Callable[[Ed25519PublicKey], object]) -> bool:
    """Swap the tool command in a validly-signed manifest and try to load it.
    True == the loader accepted the forgery (the bug); False == it rejected it."""
    pub, manifest, signature = _signed_manifest()
    tampered = manifest.replace(b"safe-calc", b"rm -rf /")  # attacker swaps the tool
    try:
        make_loader(pub).load(tampered, signature)
        return True   # loaded a tampered manifest under a stale signature -> compromised
    except Exception:
        return False  # signature mismatch -> integrity enforced


def run_self_test() -> int:
    failures = 0
    if not loads_valid_manifest(SignedToolLoader):
        failures += 1
        print("FAIL: oracle loader rejected a correctly-signed manifest", file=sys.stderr)
    if accepts_tampered_manifest(SignedToolLoader):
        failures += 1
        print("FAIL: oracle loader accepted a tampered manifest", file=sys.stderr)
    if not accepts_tampered_manifest(UnverifiedToolLoader):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: unverified loader was NOT caught accepting a forgery", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (signed loader rejects a tampered manifest; unverified loader caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Agent tool-manifest integrity harness")
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
    "name": "agent_tool_manifest",
    "path": "harnesses/ai/agent_tool_manifest_test_harness.py",
    "flavor": "ai",
    "dependency": "cryptography (Ed25519)",
    "standard": (
        "OWASP Top 10 for Agentic Applications 2026 - ASI04 Agentic Supply Chain Compromise"
    ),
    "failure_class": "Loading a tampered/substituted tool manifest without signature verification",
    "oracle": "SignedToolLoader.load - Ed25519-verify the manifest before parsing",
    "buggy": "UnverifiedToolLoader.load - parse the manifest without checking the signature",
    "planted_mutant": (
        "swap a tool command in a validly-signed manifest; unverified loader accepts it"
    ),
    "proof_file": "tests/ai/test_agent_tool_manifest_proof.py",
    "vacuity_targets": ["accepts_tampered_manifest"],
    "commands": ["python harnesses/ai/agent_tool_manifest_test_harness.py --self-test"],
    "known_limits": "verifies signature only; does not attest the manifest source provenance",
    "related": ["provenance_attestation", "agent_message_auth (ASI07)"],
}
