#!/usr/bin/env python3
"""Human step-up confirmation harness (cryptography / Ed25519).

OWASP Top 10 for Agentic Applications 2026 -- ASI09 Human-Agent Trust Exploitation.

WHY: Agents exploit "authority bias" to talk a human into rubber-stamping a risky action --
or simply assert that the human already approved. The 2026 mitigation is explicit: an
irreversible action must require INDEPENDENT, out-of-band step-up authentication, NOT an
in-band "the user said yes" the agent itself can fabricate. A test where the human really
approves passes whether or not the executor can tell a real approval from a self-asserted
one -- the gap only shows when the AGENT claims consent with no out-of-band proof.

HOW: `StepUpExecutor` is the ORACLE -- an irreversible action requires an Ed25519 signature
over `(action|nonce)` from the human's key, which the agent does NOT hold; missing/invalid
step-up is refused. `InBandConsentExecutor` is the planted defect -- it executes on the
agent's own say-so. `executes_without_stepup` has the agent attempt the action with no
human signature: the oracle refuses, the in-band executor runs it.

WHERE: ai/ -- in-process, deterministic. Uses `cryptography` (the human holds the private
key; the executor verifies with the public key -- the agent can't forge a step-up).

Self-test:
    python harnesses/ai/agent_human_confirmation_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable, Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["executes_without_stepup"]

DOSSIER = {
    "name": "agent_human_confirmation",
    "path": "harnesses/ai/agent_human_confirmation_test_harness.py",
    "flavor": "ai",
    "dependency": "cryptography (Ed25519)",
    "standard": "OWASP Top 10 for Agentic Applications 2026 - ASI09 Human-Agent Trust Exploitation",
    "failure_class": (
        "Irreversible action runs on in-band agent-asserted consent (no out-of-band step-up)"
    ),
    "oracle": "StepUpExecutor.execute - require the human's Ed25519 signature over (action|nonce)",
    "buggy": "InBandConsentExecutor.execute - run on the agent's own say-so",
    "planted_mutant": (
        "agent triggers an irreversible action with no human step-up; in-band executor runs it"
    ),
    "proof_file": "tests/ai/test_agent_human_confirmation_proof.py",
    "vacuity_targets": ["executes_without_stepup"],
    "commands": ["python harnesses/ai/agent_human_confirmation_test_harness.py --self-test"],
    "known_limits": (
        "models the step-up binding; real systems also need replay protection on the token"
    ),
    "related": ["agent_join_replay (ASI10)", "oauth_pkce", "rate_limit"],
}


class StepUpExecutor:
    """ORACLE: require an out-of-band human Ed25519 step-up before an irreversible action."""

    def __init__(self, human_public_key: Ed25519PublicKey) -> None:
        self.human_public_key = human_public_key

    def execute(self, action: str, nonce: str, stepup_signature: Optional[bytes]) -> str:
        if stepup_signature is None:
            raise PermissionError("irreversible action requires out-of-band human step-up")
        self.human_public_key.verify(stepup_signature, f"{action}|{nonce}".encode())
        return f"executed:{action}"


class InBandConsentExecutor:
    """BUGGY: execute on the agent's own in-band 'confirmed', ignoring the step-up."""

    def __init__(self, human_public_key: Optional[Ed25519PublicKey] = None) -> None:
        self.human_public_key = human_public_key

    def execute(self, action: str, nonce: str, stepup_signature: Optional[bytes]) -> str:
        return f"executed:{action}"  # BUG: no out-of-band step-up is required


def executes_with_valid_stepup(make_executor: Callable[[Ed25519PublicKey], object]) -> bool:
    human = Ed25519PrivateKey.generate()
    signature = human.sign(b"wire_transfer|n-1")
    try:
        return make_executor(human.public_key()).execute("wire_transfer", "n-1", signature) == "executed:wire_transfer"
    except Exception:
        return False


def executes_without_stepup(make_executor: Callable[[Ed25519PublicKey], object]) -> bool:
    """The agent attempts an irreversible action with NO human step-up. True == it ran anyway
    (the bug); False == it was refused."""
    human_public_key = Ed25519PrivateKey.generate().public_key()
    try:
        make_executor(human_public_key).execute("wire_transfer", "n-1", None)
        return True   # ran an irreversible action on agent-asserted consent -> trust exploited
    except Exception:
        return False  # refused without out-of-band step-up


def run_self_test() -> int:
    failures = 0
    if not executes_with_valid_stepup(StepUpExecutor):
        failures += 1
        print("FAIL: oracle refused a genuinely human-approved action", file=sys.stderr)
    if executes_without_stepup(StepUpExecutor):
        failures += 1
        print("FAIL: oracle ran an irreversible action without human step-up", file=sys.stderr)
    if not executes_without_stepup(InBandConsentExecutor):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print(
            "FAIL: in-band consent executor was NOT caught running without step-up",
            file=sys.stderr,
        )
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (step-up executor refuses self-asserted consent; in-band executor caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Human step-up confirmation harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
