#!/usr/bin/env python3
"""Dependency-confusion harness (packaging): pin internal packages to the private index.

OWASP Top 10:2025 A03 Software Supply Chain Failures (dependency confusion / substitution).

WHY: If an internal package name also exists on a public index with a HIGHER version, a
resolver that just picks the highest version across all indexes pulls the attacker's public
package -- the classic dependency-confusion attack. Internal names must be pinned to the
private source regardless of any higher public version.

HOW: `PinnedResolver` is the ORACLE -- for an allowlisted internal name it only considers
`internal`-source candidates, so a higher `public` version is ignored. `HighestVersionResolver`
is the planted defect -- it picks the highest version across all sources.
`resolves_public_over_internal` offers an internal 1.0.0 and a public 9.9.9 and reports which
source won.

WHERE: lib/ -- dependency-backed (`packaging` version ordering), in-process, no index.

Self-test:
    python harnesses/lib/dependency_confusion_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

from packaging.version import Version

# Symbol the vacuous-green meta-gate (tools/vacuity_gate.py) neuters to confirm teeth.
VACUITY_TARGETS = ["resolves_public_over_internal"]

DOSSIER = {
    "name": "dependency_confusion",
    "path": "harnesses/lib/dependency_confusion_test_harness.py",
    "flavor": "lib",
    "dependency": "packaging",
    "standard": "OWASP Top 10:2025 A03 Software Supply Chain - dependency confusion",
    "failure_class": "Resolving an internal package to a higher-versioned PUBLIC impostor",
    "oracle": "PinnedResolver.resolve - internal names only consider the private source",
    "buggy": "HighestVersionResolver.resolve - pick the highest version from any source",
    "planted_mutant": "internal 1.0.0 vs public 9.9.9 for an internal name; the public wins",
    "proof_file": "tests/lib/test_dependency_confusion_proof.py",
    "vacuity_targets": ["resolves_public_over_internal"],
    "commands": ["python harnesses/lib/dependency_confusion_test_harness.py --self-test"],
    "known_limits": "source pinning by allowlist; not full lockfile-hash or SBOM verification",
    "related": ["provenance_attestation", "secret_scanning"],
}

_INTERNAL_NAMES = {"internal-lib"}


class PinnedResolver:
    """ORACLE: internal names only consider the private source."""

    def resolve(self, name: str, candidates: list) -> tuple:
        pool = candidates
        if name in _INTERNAL_NAMES:
            pool = [c for c in candidates if c[1] == "internal"]
        return max(pool, key=lambda c: Version(c[0]))


class HighestVersionResolver:
    """BUGGY: pick the highest version from any source."""

    def resolve(self, name: str, candidates: list) -> tuple:
        return max(candidates, key=lambda c: Version(c[0]))  # BUG: ignores the source


def resolves_internal_package(make_resolver: Callable[[], object]) -> bool:
    chosen = make_resolver().resolve("internal-lib", [("1.0.0", "internal")])
    return chosen[1] == "internal"


def resolves_public_over_internal(make_resolver: Callable[[], object]) -> bool:
    """True == a higher-versioned public impostor beat the internal package (confusion)."""
    candidates = [("1.0.0", "internal"), ("9.9.9", "public")]
    return make_resolver().resolve("internal-lib", candidates)[1] == "public"


def run_self_test() -> int:
    failures = 0
    if not resolves_internal_package(PinnedResolver):
        failures += 1
        print("FAIL: oracle failed to resolve the internal package", file=sys.stderr)
    if resolves_public_over_internal(PinnedResolver):
        failures += 1
        print("FAIL: oracle resolved a public impostor over the internal package", file=sys.stderr)
    if not resolves_public_over_internal(HighestVersionResolver):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: highest-version resolver dependency confusion was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (pinned resolver keeps the internal source; highest-version picks public)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dependency-confusion harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
