import pytest

from harnesses.integration import keycloak_oidc_test_harness as h

pytestmark = pytest.mark.integration


def test_oracle_accepts_real_token(keycloak_oidc) -> None:
    oracle = h.TokenVerifier(keycloak_oidc["jwks_url"], keycloak_oidc["issuer"],
                             keycloak_oidc["audience"])
    assert h.accepts_token(oracle, keycloak_oidc["valid_token"]) is True
