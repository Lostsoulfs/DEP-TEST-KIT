#!/usr/bin/env python3
"""Tamper-evident audit-log harness (cryptography): an HMAC hash-chain detects edits.

OWASP Top 10:2025 A09 Security Logging & Alerting Failures (renamed in 2025 to stress
ALERTING). A core requirement: "protect security logs from tampering or deletion" -- you
cannot alert on what an attacker can quietly rewrite.

WHY: An audit log that stores plain rows lets an attacker who gains write access edit or
delete the entry that incriminates them, and a `verify()` that just returns True never
notices. A test that only checks "was the event written?" passes anyway; only re-verifying
after a tamper exposes the gap.

HOW: `HashChainedLog` is the ORACLE -- each entry carries an HMAC over (previous_mac + data)
with a server secret (cryptography), so editing, deleting, or reordering any entry breaks the
chain and `verify()` returns False. `PlainLog` is the planted defect -- `verify()` always
returns True. `tampering_undetected` appends entries, rewrites the incriminating one in
place, and reports whether `verify()` still passes.

WHERE: lib/ -- dependency-backed (`cryptography` HMAC-SHA256) and fully in-process.

Self-test:
    python harnesses/lib/tamper_evident_log_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import secrets
import sys
from typing import Callable

from cryptography.hazmat.primitives import hashes, hmac

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["tampering_undetected"]

DOSSIER = {
    "name": "tamper_evident_log",
    "path": "harnesses/lib/tamper_evident_log_test_harness.py",
    "flavor": "lib",
    "dependency": "cryptography",
    "standard": "OWASP Top 10:2025 A09 Security Logging & Alerting Failures - log tampering",
    "failure_class": "Audit log a user can edit or delete without detection (no integrity)",
    "oracle": "HashChainedLog - per-entry HMAC over (prev_mac + data); verify detects edits",
    "buggy": "PlainLog.verify - always True (no integrity)",
    "planted_mutant": "rewrite an incriminating entry in place; the chain no longer verifies",
    "proof_file": "tests/lib/test_tamper_evident_log_proof.py",
    "vacuity_targets": ["tampering_undetected"],
    "commands": ["python harnesses/lib/tamper_evident_log_test_harness.py --self-test"],
    "known_limits": (
        "tamper-evidence (detect) only; not tamper-PROOF storage or remote attestation"
    ),
    "related": ["eu_ai_act_logging", "provenance_attestation", "secret_scanning"],
}


def _mac(secret: bytes, data: bytes) -> bytes:
    tag = hmac.HMAC(secret, hashes.SHA256())
    tag.update(data)
    return tag.finalize()


class HashChainedLog:
    """ORACLE: each entry HMACs (prev_mac + data); any edit breaks the chain."""

    def __init__(self) -> None:
        self._secret = secrets.token_bytes(32)
        self._entries: list = []

    def append(self, data: str) -> None:
        prev = self._entries[-1]["mac"] if self._entries else b""
        self._entries.append({"data": data, "mac": _mac(self._secret, prev + data.encode())})

    def verify(self) -> bool:
        prev = b""
        for entry in self._entries:
            if _mac(self._secret, prev + entry["data"].encode()) != entry["mac"]:
                return False
            prev = entry["mac"]
        return True

    def tamper(self, index: int, data: str) -> None:
        self._entries[index]["data"] = data  # rewrite data, leave the stale mac


class PlainLog:
    """BUGGY: store plain rows; verify() never checks integrity."""

    def __init__(self) -> None:
        self._entries: list = []

    def append(self, data: str) -> None:
        self._entries.append({"data": data})

    def verify(self) -> bool:
        return True  # BUG: no integrity

    def tamper(self, index: int, data: str) -> None:
        self._entries[index]["data"] = data


def intact_log_verifies(make_log: Callable[[], object]) -> bool:
    """True == an untampered log verifies (no false positive)."""
    log = make_log()
    for data in ("login ok user=alice", "read /report user=alice", "logout user=alice"):
        log.append(data)
    return log.verify()


def tampering_undetected(make_log: Callable[[], object]) -> bool:
    """True == an edited entry still verifies (the bug)."""
    log = make_log()
    for data in ("login ok user=alice", "grant role=admin user=alice", "logout user=alice"):
        log.append(data)
    log.tamper(1, "login ok user=alice")  # rewrite the incriminating entry
    return log.verify()


def run_self_test() -> int:
    failures = 0
    if not intact_log_verifies(HashChainedLog):
        failures += 1
        print("FAIL: oracle failed to verify an untampered log", file=sys.stderr)
    if tampering_undetected(HashChainedLog):
        failures += 1
        print("FAIL: oracle did not detect a tampered entry", file=sys.stderr)
    if not tampering_undetected(PlainLog):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: plain log tampering was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (hash-chain detects the rewritten entry; plain log does not)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Tamper-evident audit-log harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
