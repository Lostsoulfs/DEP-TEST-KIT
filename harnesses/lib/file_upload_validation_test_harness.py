#!/usr/bin/env python3
"""File-upload validation harness (python-magic): validate content bytes, not the extension.

OWASP Top 10:2025 A05 Injection - unrestricted file upload (CWE-434).

WHY: Accepting an upload because its NAME ends in `.jpg` lets an attacker upload a web shell as
`evil.jpg` (or `.php.jpg`) whose bytes are actually a script. The content type must be detected
from the file's magic bytes, not trusted from the client-supplied extension.

HOW: `ContentTypeValidator` is the ORACLE -- it detects the MIME type from the bytes with
`magic` and accepts only real images. `ExtensionValidator` is the planted defect -- it trusts
the `.jpg` suffix. `accepts_disguised_payload` uploads script bytes named `evil.jpg` and reports
whether it was accepted.

WHERE: lib/ -- dependency-backed (`python-magic`). The content-typing path needs native libmagic,
which is upstream-unsupported on native Windows (it hangs), so -- like the mutmut lane -- the
magic checks run on Linux/CI and skip cleanly on Windows.

Self-test:
    python harnesses/lib/file_upload_validation_test_harness.py --self-test
"""

from __future__ import annotations

import argparse
import sys
from typing import Callable

# `magic` (python-magic) is imported lazily inside ContentTypeValidator.accept: a top-level
# import can hang during libmagic init on native Windows. deptry still detects the nested import.

DOSSIER = {
    "name": "file_upload_validation",
    "path": "harnesses/lib/file_upload_validation_test_harness.py",
    "flavor": "lib",
    "dependency": "python-magic",
    "standard": "OWASP Top 10:2025 A05 Injection - unrestricted file upload (CWE-434)",
    "failure_class": "Accepting an upload by its .jpg extension while the bytes are a script",
    "oracle": "ContentTypeValidator.accept - detect MIME from magic bytes, accept real images",
    "buggy": "ExtensionValidator.accept - trust the filename extension",
    "planted_mutant": "script bytes named evil.jpg pass the extension check",
    "proof_file": "tests/lib/test_file_upload_validation_proof.py",
    "vacuity_targets": [],  # libmagic is Windows-unsupported; vacuity-exempt like the mutmut lane
    "commands": ["python harnesses/lib/file_upload_validation_test_harness.py --self-test"],
    "known_limits": "magic-byte content typing; not polyglot/archive inspection; magic checks "
                    "skip on native Windows (libmagic upstream-unsupported)",
    "related": ["html_sanitization", "advanced_injection"],
}

_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"\x00" * 32
_SCRIPT = b"<?php system($_GET['c']); ?>"


def magic_available() -> bool:
    """python-magic needs native libmagic, which hangs / is upstream-unsupported on native
    Windows (like the mutmut lane). Gate on platform: Linux/CI runs it, Windows skips cleanly."""
    return sys.platform != "win32"


class ContentTypeValidator:
    """ORACLE: accept only files whose magic bytes are a real image."""

    def accept(self, filename: str, content: bytes) -> bool:
        import magic  # lazy: a top-level import can hang during libmagic init on Windows
        return magic.from_buffer(content, mime=True) == "image/jpeg"


class ExtensionValidator:
    """BUGGY: trust the filename extension."""

    def accept(self, filename: str, content: bytes) -> bool:
        return filename.lower().endswith(".jpg")  # BUG: extension is attacker-controlled


def accepts_genuine_image(make_validator: Callable[[], object]) -> bool:
    return make_validator().accept("photo.jpg", _JPEG)


def accepts_disguised_payload(make_validator: Callable[[], object]) -> bool:
    """True == script bytes named evil.jpg were accepted as an image (the bug)."""
    return make_validator().accept("evil.jpg", _SCRIPT)


def run_self_test() -> int:
    if not magic_available():
        print("self-test: SKIP (libmagic unavailable on native Windows; runs on Linux/CI)")
        return 0
    failures = 0
    if not accepts_genuine_image(ContentTypeValidator):
        failures += 1
        print("FAIL: oracle rejected a genuine JPEG", file=sys.stderr)
    if accepts_disguised_payload(ContentTypeValidator):
        failures += 1
        print("FAIL: oracle accepted a disguised script payload", file=sys.stderr)
    if not accepts_disguised_payload(ExtensionValidator):
        failures += 1  # the planted bug must be caught -- else vacuous green
        print("FAIL: extension-trusting validator was NOT caught", file=sys.stderr)
    if failures:
        print(f"self-test: {failures} failure(s)", file=sys.stderr)
        return 1
    print("self-test: OK (magic-byte validator rejects the disguised payload; extension trusts it)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="File-upload validation harness")
    parser.add_argument("--self-test", action="store_true", help="run the planted-bug self-test")
    args = parser.parse_args(argv)
    if not args.self_test:
        parser.print_help(sys.stderr)
        return 2
    return run_self_test()


if __name__ == "__main__":
    sys.exit(main())
