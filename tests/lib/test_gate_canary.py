"""Pytest wrapper for tools/gate_canary.py — and proof the canary isn't vacuous.

The canary is itself a gate, so it needs the same teeth it demands of others. This
asserts (a) every canary passes against the LIVE gates, and (b) the canary FAILS
when a gate is softened — the secret scanner neutered, or the vacuity meta-gate's
detection rigged to pass. Without (b), the canary could silently go green if someone
disabled it.
"""

from __future__ import annotations

from tools import gate_canary, scan_staged, vacuity_gate


def test_all_canaries_pass_on_live_gates() -> None:
    assert gate_canary.run() == 0


def test_canary_bites_when_scanner_softened(monkeypatch) -> None:
    monkeypatch.setattr(scan_staged, "scan_line", lambda line: [])  # neuter the gate
    assert gate_canary.run() == 1


def test_canary_bites_when_vacuity_gate_softened(monkeypatch) -> None:
    # Simulate the vacuity meta-gate's self-test going red (it can no longer prove
    # it detects a vacuous harness) — the canary must surface it.
    monkeypatch.setattr(vacuity_gate, "main", lambda argv=None: 1)
    assert gate_canary.run() == 1
