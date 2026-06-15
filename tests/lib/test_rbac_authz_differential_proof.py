"""Proof: the harness has teeth — the action-ignoring authorizer is caught, the oracle clears."""

from harnesses.lib import rbac_authz_differential_test_harness as h


def test_proof_buggy_authorizer_is_caught() -> None:
    # The differential oracle must find a request where buggy disagrees with the reference.
    assert h.divergence_from_reference(h.buggy_allow) is not None


def test_proof_oracle_authorizer_is_not_caught() -> None:
    assert h.divergence_from_reference(h.oracle_allow) is None


def test_proof_buggy_escalates_read_to_write() -> None:
    # Minimal human-visible instance: viewer granted read on doc, buggy also allows write.
    policy = {"viewer": frozenset({("doc", "read")})}
    roles = frozenset({"viewer"})
    assert h.reference_allow(policy, roles, "doc", "write") is False
    assert h.buggy_allow(policy, roles, "doc", "write") is True
