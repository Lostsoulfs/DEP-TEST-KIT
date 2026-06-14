#!/usr/bin/env python3
"""Secret-scanning coverage test harness (detect-secrets).

WHY: An in-house "secret check" is often a substring grep (e.g. looking for
`password=`). It passes its own example test and is blind in production to the
secrets that actually leak: AWS keys, high-entropy tokens, private-key blocks.
detect-secrets runs a plugin suite (structured detectors + Shannon-entropy)
that catches those formats. The failure class is a scanner that is green while
missing real secrets (CWE-798 hard-coded credentials slipping through review).

HOW: `BLOB` contains an AWS access key, a high-entropy base64 token, and a
private-key header — but NO literal `password=`. The ORACLE
`detect_secrets_count` scans it with detect-secrets' adhoc API and finds > 0.
The BUGGY `naive_secret_count` greps for `password=` and finds 0. `misses_real_secrets`
turns "found nothing" into the boolean the proof asserts: the naive scanner
misses what detect-secrets catches.

WHERE: lib/ — dependency-backed (`detect-secrets`) but fully in-process, no
service. Adds `detect-secrets` to the `lib` extra in pyproject.toml.

NOTE: this uses detect-secrets' adhoc scanning API (scan_line + transient_settings),
an internal API. It is pinned exactly by uv.lock, so CI (`uv sync --locked`) is stable;
a future detect-secrets that breaks the call path surfaces as a loud test failure (the
oracle count drops to 0), never a silent pass. Re-confirm the path when bumping the dep.

Self-test:
    python harnesses/lib/secret_scanning_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys

from detect_secrets.core import scan
from detect_secrets.settings import transient_settings

# A realistic config blob: real secrets, none of them named `password=`. The three
# secret-shaped lines carry the repo's `allowlist secret` marker (see tools/scan_staged.py):
# they are intentional, reviewed test fixtures. The marker is a source comment, NOT part of
# BLOB, so detect-secrets still sees the raw values at runtime and the proof keeps its teeth.
BLOB = "\n".join([
    "aws_access_key_id = AKIAIOSFODNN7EXAMPLE",  # allowlist secret
    "service_token = c2VjcmV0LWhpZ2gtZW50cm9weS10b2tlbi1abE0xMjM0NTY3ODkw",  # allowlist secret
    "-----BEGIN RSA PRIVATE KEY-----",  # allowlist secret
    "MIIEowIBAAKCAQEArandombase64looking...",
    "-----END RSA PRIVATE KEY-----",
])

_PLUGINS = {
    "plugins_used": [
        {"name": "AWSKeyDetector"},
        {"name": "PrivateKeyDetector"},
        {"name": "Base64HighEntropyString", "limit": 4.5},
        {"name": "KeywordDetector"},
    ]
}


def detect_secrets_count(text: str) -> int:
    """ORACLE: count secrets found by detect-secrets across all lines."""
    found = 0
    with transient_settings(_PLUGINS):
        for line in text.splitlines():
            found += sum(1 for _ in scan.scan_line(line))
    return found


def naive_secret_count(text: str) -> int:
    """BUGGY: the in-house grep only knows one shape of secret."""
    return sum(1 for line in text.splitlines() if "password=" in line.lower())


def misses_real_secrets(scanner) -> bool:
    """True == the scanner found nothing in BLOB (the blind-spot bug)."""
    return scanner(BLOB) == 0


def run_self_test() -> int:
    failures = 0
    if misses_real_secrets(detect_secrets_count):
        failures += 1
        print("FAIL: detect-secrets oracle found no secrets in the blob", file=sys.stderr)
    if not misses_real_secrets(naive_secret_count):
        failures += 1  # the planted bug must be caught — else vacuous green
        print("FAIL: naive grep unexpectedly found a secret (bug not demonstrated)", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (detect-secrets catches AWS/entropy/private-key; naive grep misses all)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Secret-scanning coverage harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
