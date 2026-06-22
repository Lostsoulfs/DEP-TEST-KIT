"""Proof: magic-byte typing rejects the disguised payload the extension check accepts.
Script bytes named evil.jpg fail content typing vs passing the .jpg suffix."""

import pytest

from harnesses.lib import file_upload_validation_test_harness as h

# Content-typing (magic) checks need native libmagic (Windows-unsupported, hangs); they run on
# Linux/CI and skip here. The extension-trust (buggy-side) teeth need no libmagic and run always.
_needs_magic = pytest.mark.skipif(
    not h.magic_available(),
    reason="libmagic unavailable on native Windows; runs on Linux/CI",
)


def test_proof_buggy_is_flagged() -> None:
    assert h.accepts_disguised_payload(h.ExtensionValidator) is True


@_needs_magic
def test_proof_oracle_not_flagged() -> None:
    assert h.accepts_disguised_payload(h.ContentTypeValidator) is False


@_needs_magic
def test_proof_oracle_happy_path() -> None:
    assert h.accepts_genuine_image(h.ContentTypeValidator) is True


_DISGUISED = [
    b"<?php system($_GET['c']); ?>",
    b"\x7fELF\x02\x01\x01" + b"\x00" * 8,
    b"#!/bin/sh\nrm -rf /",
    b"<html><script>alert(1)</script></html>",
    b"MZ\x90\x00\x03\x00\x00\x00",
    b"PK\x03\x04\x14\x00",
]


@pytest.mark.parametrize("content", _DISGUISED)
def test_proof_extension_validator_accepts_disguised(content) -> None:
    assert h.ExtensionValidator().accept("evil.jpg", content) is True
