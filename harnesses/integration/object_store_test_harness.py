#!/usr/bin/env python3
"""S3/MinIO object-store integration test harness (testcontainers).

WHY:   An object store's contract is "the bytes you put are the bytes you get." A store
       that encodes text with the wrong codec writes corrupt bytes that no in-memory
       mock (which just hands your `str` back) will ever reveal. Only a real round-trip
       through S3 — put bytes, get bytes — exposes the corruption.

HOW:   `BlobStore` writes text as UTF-8 and `load` decodes the stored bytes as UTF-8
       (the canonical contract). `BuggyBlobStore` ships the SAME code but writes Latin-1
       — so a character like "é" is stored as the single byte 0xE9, which is not valid
       UTF-8. The proof: the correct store round-trips "café"; the buggy store's bytes
       raise `UnicodeDecodeError` when read back as UTF-8.

WHERE: integration/ — needs a real ephemeral MinIO (S3) via Docker. Uses `boto3` as the
       application client and `minio` (the client testcontainers' MinioContainer needs);
       both in the `integration` extra. Isolation (research T2): one session-scoped
       container, a unique bucket per test. Client + bucket injected by
       `tests/integration/conftest.py`.

Self-test:
  python harnesses/integration/object_store_test_harness.py --self-test
  (deferred: the real proof runs under `pytest -m integration`, which needs Docker)
"""

from __future__ import annotations

import argparse
import shutil
import sys

TEXT = "café"  # representable in both UTF-8 and Latin-1, but with different bytes


class BlobStore:
    write_encoding = "utf-8"

    def __init__(self, client, bucket: str) -> None:
        # client is a boto3 S3 client, bucket a real bucket name — injected by fixtures.
        self.client = client
        self.bucket = bucket

    def save(self, key: str, text: str) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=text.encode(self.write_encoding))

    def load(self, key: str) -> str:
        # The canonical reader always expects UTF-8 — the store's contract.
        obj = self.client.get_object(Bucket=self.bucket, Key=key)
        return obj["Body"].read().decode("utf-8")


class BuggyBlobStore(BlobStore):
    """Identical store, but it writes Latin-1 — corrupt bytes under the UTF-8 contract."""

    write_encoding = "latin-1"


def run_self_test() -> int:
    print(
        "self-test: DEFERRED -- integration harness. Run `pytest -m integration` "
        f"(needs Docker). docker on PATH: {shutil.which('docker') is not None}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="S3/MinIO object-store integration harness")
    parser.add_argument("--self-test", action="store_true")
    parser.parse_args(argv)
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
