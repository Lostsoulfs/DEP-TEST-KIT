import pytest

from harnesses.integration import vault_secrets_test_harness as h

pytestmark = pytest.mark.integration


def test_oracle_reads_single_key(vault_client) -> None:
    reader = h.SecretReader(vault_client)
    assert reader.read("app/db", "username") == "dbuser"
