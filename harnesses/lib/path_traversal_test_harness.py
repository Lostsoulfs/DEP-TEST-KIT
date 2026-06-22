#!/usr/bin/env python3
"""Path-traversal harness (werkzeug): keep resolved file paths within the base directory.

OWASP Top 10:2025 A01 Broken Access Control - path traversal (CWE-22).

WHY: Serving a user-named file by `os.path.join(base, user_path)` lets `../../etc/passwd`
escape the base directory and read arbitrary files. A safe join rejects any path that would
resolve outside the base.

HOW: `SafeJoiner` is the ORACLE -- `werkzeug.security.safe_join`, which returns None (rejected)
on traversal. `NaiveJoiner` is the planted defect -- `os.path.join`. `escapes_base` resolves a
`../../` payload and reports whether it landed outside the base directory.

WHERE: lib/ -- dependency-backed (`werkzeug` safe_join), in-process.

Self-test:
    python harnesses/lib/path_traversal_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import os
import posixpath
import sys
from typing import Callable

from werkzeug.security import safe_join

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["escapes_base"]

DOSSIER = {
    "name": "path_traversal",
    "path": "harnesses/lib/path_traversal_test_harness.py",
    "flavor": "lib",
    "dependency": "werkzeug",
    "standard": "OWASP Top 10:2025 A01 Broken Access Control - path traversal (CWE-22)",
    "failure_class": "A '../../' path escapes the base directory and reads arbitrary files",
    "oracle": "SafeJoiner.resolve - werkzeug safe_join returns None on traversal",
    "buggy": "NaiveJoiner.resolve - os.path.join lets ../ escape the base",
    "planted_mutant": "user path '../../etc/passwd' resolves outside the served base directory",
    "proof_file": "tests/lib/test_path_traversal_proof.py",
    "vacuity_targets": ["escapes_base"],
    "commands": ["python harnesses/lib/path_traversal_test_harness.py --self-test"],
    "known_limits": "base-containment check; not symlink-following or absolute-path handling",
    "related": ["ssrf_url_guard", "open_redirect"],
}

_BASE = "/srv/www"


class SafeJoiner:
    """ORACLE: safe_join rejects traversal (returns None)."""

    def resolve(self, base: str, user_path: str) -> str:
        result = safe_join(base, user_path)
        if result is None:
            raise ValueError("path traversal rejected")
        return result


class NaiveJoiner:
    """BUGGY: plain join lets ../ escape the base."""

    def resolve(self, base: str, user_path: str) -> str:
        return os.path.join(base, user_path)  # BUG: traversal escapes the base


def _within_base(resolved: str) -> bool:
    # POSIX-normalize so containment is platform-independent: safe_join returns POSIX
    # paths while os.path.join (the buggy joiner) returns OS-native ones (backslashes on
    # Windows). Compare on the path boundary so "/srv/wwwroot" never matches "/srv/www".
    norm = posixpath.normpath(resolved.replace(chr(92), "/"))
    return norm == _BASE or norm.startswith(_BASE + "/")


def resolves_within_base(make_joiner: Callable[[], object]) -> bool:
    resolved = make_joiner().resolve(_BASE, "docs/index.html")
    return _within_base(resolved)


def escapes_base(make_joiner: Callable[[], object]) -> bool:
    """True == a traversal payload resolved outside the base directory (the bug)."""
    try:
        resolved = make_joiner().resolve(_BASE, "../../etc/passwd")
    except Exception:
        return False
    return not _within_base(resolved)


def run_self_test() -> int:
    failures = 0
    if not resolves_within_base(SafeJoiner):
        failures += 1
        print("FAIL: oracle rejected a legitimate in-base path", file=sys.stderr)
    if escapes_base(SafeJoiner):
        failures += 1
        print("FAIL: oracle allowed a traversal escape", file=sys.stderr)
    if not escapes_base(NaiveJoiner):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: naive join traversal was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (safe_join rejects the traversal; naive join escapes the base -- caught)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Path-traversal harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
