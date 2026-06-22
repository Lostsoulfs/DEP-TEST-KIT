"""Oracle + CLI-contract test for file_upload_validation (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_file_upload_validation_proof.py asserts the planted bug is caught (the teeth).
"""

import pytest

from harnesses.lib import file_upload_validation_test_harness as h

# The content-typing (magic) checks need native libmagic, which hangs on native Windows
# (like the mutmut lane); they run on Linux/CI and skip here. The extension-trust and
# CLI/self-test checks need no libmagic and run everywhere.
_needs_magic = pytest.mark.skipif(
    not h.magic_available(),
    reason="libmagic unavailable on native Windows; runs on Linux/CI",
)


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


@_needs_magic
def test_oracle_happy_path() -> None:
    assert h.accepts_genuine_image(h.ContentTypeValidator) is True


_DISGUISED = [
    b"<?php system($_GET['c']); ?>",
    b"\x7fELF\x02\x01\x01" + b"\x00" * 8,
    b"#!/bin/sh\nrm -rf /",
    b"<html><script>alert(1)</script></html>",
    b"MZ\x90\x00\x03\x00\x00\x00",
    b"PK\x03\x04\x14\x00",
]


@_needs_magic
@pytest.mark.parametrize("content", _DISGUISED)
def test_oracle_rejects_disguised_upload(content) -> None:
    assert h.ContentTypeValidator().accept("evil.jpg", content) is False


# === our own / batch 5 (original; metamorphic) ===
# Toll (surreal/psych): magic reads the CONTENT, not the name -- a real JPEG keeps any name, a
# PNG (or script) renamed .jpg is refused. The validator's allowlist is JPEG-only by design.
@_needs_magic
def test_oracle_magic_judges_content_not_name() -> None:
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    assert h.ContentTypeValidator().accept("evil.exe", h._JPEG) is True
    assert h.ContentTypeValidator().accept("photo.jpg", png) is False
    assert h.ContentTypeValidator().accept("photo.jpg", h._SCRIPT) is False
