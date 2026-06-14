#!/usr/bin/env python3
"""Vault secret-scoping integration test harness (testcontainers + hvac).

WHY: A mocked secrets client returns exactly what you stub, so a reader that
fetches the WRONG scope — the parent secret instead of the one requested key —
looks correct in tests and over-discloses sibling secrets in production. Only a
real Vault with real KV-v2 paths reveals it (CWE-200 over-broad exposure).

HOW: `SecretReader.read(path, key)` returns the single requested value from a
KV-v2 secret. `BuggySecretReader` returns the ENTIRE secret dict (every sibling
key) for the same call. Against a real Vault the proof shows the buggy reader
hands back more than was asked; the oracle returns exactly one value.

WHERE: integration/ — needs a real ephemeral Vault (Docker dev mode). The `hvac`
client is injected by `tests/integration/conftest.py` (`vault_client`); adds
`hvac` to the integration extra (testcontainers is already declared).

Self-test:
    python harnesses/integration/vault_secrets_test_harness.py --self-test
    (deferred: the real proof runs under `pytest -m integration`, which needs Docker)
"""

from __future__ import annotations

import argparse
import shutil
import sys


class SecretReader:
    """ORACLE: returns only the requested key from a KV-v2 secret."""

    def __init__(self, client, mount_point: str = "secret") -> None:
        self.client = client          # hvac.Client, injected by the fixture
        self.mount_point = mount_point

    def read(self, path: str, key: str):
        resp = self.client.secrets.kv.v2.read_secret_version(
            path=path, mount_point=self.mount_point
        )
        return resp["data"]["data"][key]


class BuggySecretReader(SecretReader):
    """BUGGY: ignores `key` and returns the whole secret dict (over-discloses)."""

    def read(self, path: str, key: str):
        resp = self.client.secrets.kv.v2.read_secret_version(
            path=path, mount_point=self.mount_point
        )
        return resp["data"]["data"]   # BUG: every sibling key, not just `key`


def over_discloses(reader: SecretReader, path: str, key: str) -> bool:
    """True == the reader returned more than the one requested value."""
    result = reader.read(path, key)
    return isinstance(result, dict)


def run_self_test() -> int:
    print(
        "self-test: DEFERRED -- integration harness. "
        "Run `pytest -m integration` (needs Docker). "
        f"docker on PATH: {shutil.which('docker') is not None}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Vault secret-scoping integration harness")
    parser.add_argument("--self-test", action="store_true")
    parser.parse_args(argv)
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
