"""Proof: a real Vault exposes the over-broad read a mock hides. The buggy reader
returns every sibling key; the oracle returns only the requested value."""

import pytest

from harnesses.integration import vault_secrets_test_harness as h

pytestmark = pytest.mark.integration


def test_proof_buggy_over_discloses(vault_client) -> None:
    reader = h.BuggySecretReader(vault_client)
    assert h.over_discloses(reader, "app/db", "password") is True


def test_proof_oracle_is_scoped(vault_client) -> None:
    reader = h.SecretReader(vault_client)
    assert h.over_discloses(reader, "app/db", "password") is False
    assert reader.read("app/db", "password") == "p@ss"
