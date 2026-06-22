"""Oracle + CLI-contract test for api_bfla (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_api_bfla_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import api_bfla_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.admin_can_invoke_admin(h.FunctionAuthz()) is True


# --- scenario coverage: every admin function blocked for non-admins, user funcs open ---
def test_oracle_blocks_admin_funcs_for_nonadmins() -> None:
    authz = h.FunctionAuthz()
    for role in ("user", "guest"):
        for function in h.ADMIN_FUNCTIONS:
            assert authz.can_invoke(role, function) is False, (role, function)


def test_oracle_allows_admin_funcs_for_admin() -> None:
    authz = h.FunctionAuthz()
    for function in h.ADMIN_FUNCTIONS:
        assert authz.can_invoke("admin", function) is True, function


def test_oracle_allows_user_funcs_for_any_role() -> None:
    authz = h.FunctionAuthz()
    for role in ("user", "admin", "guest"):
        for function in h.USER_FUNCTIONS:
            assert authz.can_invoke(role, function) is True, (role, function)


# --- second pass: an unknown function is denied for every role ---
def test_oracle_denies_unknown_function_for_all_roles() -> None:
    authz = h.FunctionAuthz()
    for role in ("admin", "user", "guest"):
        assert authz.can_invoke(role, "nonexistent_function") is False, role


# --- third pass: unknown and case-variant roles are denied admin functions ---
def test_oracle_denies_unknown_and_case_variant_roles() -> None:
    authz = h.FunctionAuthz()
    for role in ("", "ADMIN", "root", "superuser"):
        for function in h.ADMIN_FUNCTIONS:
            assert authz.can_invoke(role, function) is False, (role, function)


import pytest  # noqa: E402

_ROLES = ["user", "guest", "", "viewer", "editor", "ADMIN", "root"]
_UNKNOWN_FNS = ["delete_db", "wildcard", "get_secrets", "drop_all"]
_BFLA_DENY = ([(r, f) for r in _ROLES for f in sorted(h.ADMIN_FUNCTIONS)]
              + [(r, f) for r in _ROLES for f in _UNKNOWN_FNS])


@pytest.mark.parametrize("role,function", _BFLA_DENY)
def test_oracle_denies_bfla_corpus(role, function) -> None:
    assert h.FunctionAuthz().can_invoke(role, function) is False, (role, function)


_BFLA_ALLOW_USER = [(r, f) for r in _ROLES + ["admin"] for f in sorted(h.USER_FUNCTIONS)]


@pytest.mark.parametrize("role,function", _BFLA_ALLOW_USER)
def test_oracle_allows_user_functions_for_all(role, function) -> None:
    assert h.FunctionAuthz().can_invoke(role, function) is True, (role, function)


@pytest.mark.parametrize("function", sorted(h.ADMIN_FUNCTIONS))
def test_oracle_allows_admin_functions_for_admin(function) -> None:
    assert h.FunctionAuthz().can_invoke("admin", function) is True, function
