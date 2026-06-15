from hypothesis import given, settings

from harnesses.lib import rbac_authz_differential_test_harness as h


def test_self_test_passes() -> None:
    assert h.run_self_test() == 0


@settings(max_examples=200)
@given(h._policy, h._roles, h._request)
def test_oracle_matches_reference(policy, roles, request) -> None:
    resource, action = request
    assert h.oracle_allow(policy, roles, resource, action) == h.reference_allow(
        policy, roles, resource, action
    )


def test_reference_requires_exact_action() -> None:
    policy = {"viewer": frozenset({("doc", "read")})}
    roles = frozenset({"viewer"})
    assert h.reference_allow(policy, roles, "doc", "read") is True
    assert h.reference_allow(policy, roles, "doc", "write") is False
