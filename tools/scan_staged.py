#!/usr/bin/env python3
"""Staged secret gate — blocks secret tokens and personal-tier paths.

Usage:
  python tools/scan_staged.py --staged          # scan the staged diff (pre-commit)
  python tools/scan_staged.py --ci --base REF    # scan REF...HEAD (CI)
  python tools/scan_staged.py --self-test        # built-in cases, exit 0/1

Exit: 0 = no blocking findings, 1 = a block (commit/CI should fail), 2 = usage.

Scope: SECRET TOKENS and personal-tier paths only. PII detection lives in
testing-kits/harnesses/security/pii_redaction_test_harness.py and is intentionally
not duplicated here. The scanner is direction-aware: only ADDED ('+') diff lines are
inspected, so removing a secret never trips the gate.

Escape hatch: a line containing the marker  allowlist secret  is skipped. One-off
bypass for an intentional commit:  git commit --no-verify  (use sparingly).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

_SECRET_RES = [
    ("AWS_ACCESS_KEY_ID", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GITHUB_TOKEN", re.compile(r"\bghp_[A-Za-z0-9]{36}\b")),
    ("GITHUB_PAT", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{59,}\b")),
    ("PRIVATE_KEY_BLOCK", re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")),
    ("SLACK_TOKEN", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("GOOGLE_API_KEY", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b")),
    (
        "GENERIC_SECRET_ASSIGNMENT",
        re.compile(
            r"(?i)\b(?:api[_-]?key|secret|token|passwd|password|access[_-]?key)\b"
            r"\s*[:=]\s*['\"]?[A-Za-z0-9_\-/+=]{16,}"
        ),
    ),
]
_ALLOWLIST_MARKER = "allowlist secret"
_PERSONAL_PATH_RE = re.compile(r"(^|/)(PERSONAL_JOURNAL[^/]*$|private/)")


def scan_line(line: str) -> list[str]:
    """Return secret-label hits for one added line of content."""
    if _ALLOWLIST_MARKER in line:
        return []
    return [name for name, rx in _SECRET_RES if rx.search(line)]


def _git(args: list[str]) -> str:
    out = subprocess.run(["git"] + args, capture_output=True, text=True, check=False)
    return out.stdout


def _changed_paths(diff_args: list[str]) -> list[str]:
    return [p for p in _git(["diff", "--name-only"] + diff_args).splitlines() if p]


def _added_lines(diff_args: list[str]):
    """Yield (path, new_lineno, text) for each ADDED line in the diff."""
    diff = _git(["diff", "--unified=0", "--no-color"] + diff_args)
    path = None
    newno = 0
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:]
        elif line.startswith("+++ "):
            path = None
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            newno = int(m.group(1)) if m else 0
        elif line.startswith("+") and not line.startswith("+++"):
            yield path, newno, line[1:]
            newno += 1
        elif not line.startswith("-"):
            newno += 1


def _scan(diff_args: list[str]) -> int:
    blocks = []
    for p in _changed_paths(diff_args):
        if _PERSONAL_PATH_RE.search(p):
            blocks.append((p, 0, "PERSONAL/PRIVATE PATH"))
    for path, no, text in _added_lines(diff_args):
        for hit in scan_line(text):
            blocks.append((path or "?", no, hit))
    if not blocks:
        return 0
    print("BLOCKED: possible secret / personal-tier content in this change.\n")
    for path, no, kind in blocks:
        loc = f"{path}:{no}" if no else path
        print(f"  {kind:<28} {loc}")
    print(
        "\nThe raw value is not printed. Remove it (secrets never belong in git). For an\n"
        "intentional, reviewed line add the marker 'allowlist secret', or bypass once with\n"
        "'git commit --no-verify'."
    )
    return 1


def _run_self_test() -> int:
    # Fixtures assembled from parts so this file does not trip its own gate.
    aws = "AKIA" + "IOSFODNN7EXAMPLE"
    ghp = "ghp_" + ("a" * 36)
    pem = "-----BEGIN " + "RSA PRIVATE KEY-----"
    slack = "xoxb-" + "1234567890-abcdefXYZ"
    gkey = "AIza" + ("b" * 35)
    generic = "api_key" + " = " + "'" + ("A" * 20) + "'"
    must_block = [aws, ghp, pem, slack, gkey, generic]

    must_clean = [
        "this line mentions an api_key in passing",  # keyword, no value
        "uses ${{ secrets.GITHUB_TOKEN }} in CI",  # CI ref, not a literal
        "a normal line of prose about tokens",
        aws + "  " + _ALLOWLIST_MARKER,  # escape hatch
    ]

    fails = 0
    for s in must_block:
        if not scan_line(s):
            fails += 1
            print("  FAIL: expected secret block not detected")
    for s in must_clean:
        if scan_line(s):
            fails += 1
            print("  FAIL: clean fixture produced a false positive")
    if fails:
        print(f"self-test: {fails} failure(s)")
        return 1
    print(f"self-test: OK ({len(must_block)} blocked, {len(must_clean)} clean)")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Secret/personal-tier staged gate.")
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--staged", action="store_true")
    p.add_argument("--ci", action="store_true")
    p.add_argument("--base", default="")
    a = p.parse_args()

    if a.self_test:
        return _run_self_test()
    if a.ci:
        if not a.base:
            print("--ci requires --base REF", file=sys.stderr)
            return 2
        return _scan([f"{a.base}...HEAD"])
    return _scan(["--cached"])


if __name__ == "__main__":
    sys.exit(main())
