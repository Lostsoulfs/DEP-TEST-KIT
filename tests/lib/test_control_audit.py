"""Tests for tools/control_audit.py — the machine-checked control policy.

(a) the real repo must satisfy .github/control-policy.json; (b) the auditor must BITE
on a policy violation (a required file that is missing), not pass vacuously.
"""

from __future__ import annotations

import json
from pathlib import Path

from tools import control_audit


def test_real_repo_satisfies_control_policy() -> None:
    assert control_audit.main() == 0


def test_bites_on_missing_required_file(tmp_path, monkeypatch) -> None:
    (tmp_path / ".github").mkdir()
    policy = {
        "scanner_mode": "block",
        "required_files": ["NOPE_MISSING.md"],
        "instruction_sources": [],
        "required_workflows": [],
        "exceptions": [],
    }
    (tmp_path / ".github" / "control-policy.json").write_text(json.dumps(policy), encoding="utf-8")
    monkeypatch.setattr(control_audit, "ROOT", tmp_path)
    monkeypatch.setattr(control_audit, "POLICY_PATH", tmp_path / ".github" / "control-policy.json")
    assert control_audit.main() == 1
