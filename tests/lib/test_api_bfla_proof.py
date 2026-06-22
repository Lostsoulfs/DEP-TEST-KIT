"""Proof: function-level authz blocks the escalation the auth-only policy allows. Hypothesis
falsifies the auth-only policy (a non-admin reaches an admin function) but not the gated one."""

from harnesses.lib import api_bfla_test_harness as h


def test_proof_auth_only_allows_escalation() -> None:
    assert h.find_function_escalation(h.AuthOnlyAuthz()) is True


def test_proof_function_authz_blocks_escalation() -> None:
    assert h.find_function_escalation(h.FunctionAuthz()) is False


def test_proof_admin_can_invoke_admin() -> None:
    assert h.admin_can_invoke_admin(h.FunctionAuthz()) is True


# --- scenario coverage: the auth-only policy lets a user reach every admin function ---
def test_proof_authonly_allows_every_admin_func_for_user() -> None:
    authz = h.AuthOnlyAuthz()
    for function in h.ADMIN_FUNCTIONS:
        assert authz.can_invoke("user", function) is True, function


import pytest  # noqa: E402

_ROLES = ["user", "guest", "", "viewer", "editor", "ADMIN", "root"]
_BFLA_BYPASS = [(r, f) for r in _ROLES for f in sorted(h.ADMIN_FUNCTIONS)]


@pytest.mark.parametrize("role,function", _BFLA_BYPASS)
def test_proof_authonly_authorizes_bfla_corpus(role, function) -> None:
    assert h.AuthOnlyAuthz().can_invoke(role, function) is True, (role, function)
