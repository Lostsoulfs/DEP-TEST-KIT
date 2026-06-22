"""Proof: schema validation at the tool boundary rejects hostile args the raw dispatcher
accepts. The raw dispatcher dispatches a negative amount + traversal target + injected field;
the validating dispatcher rejects them."""

from harnesses.lib import tool_arg_validation_test_harness as h


def test_proof_raw_dispatcher_accepts_malicious() -> None:
    assert h.accepts_malicious_args(h.RawDispatcher) is True


def test_proof_validating_dispatcher_rejects_malicious() -> None:
    assert h.accepts_malicious_args(h.ValidatingDispatcher) is False


def test_proof_validating_dispatcher_allows_valid() -> None:
    assert h.dispatches_valid_args(h.ValidatingDispatcher) is True


# --- scenario coverage: the raw dispatcher forwards hostile args unchecked ---
def test_proof_raw_dispatcher_accepts_hostile_args() -> None:
    out = h.RawDispatcher().dispatch({"amount": -999, "to_account": "../../etc/passwd"})
    assert out["amount"] == -999 and out["to"] == "../../etc/passwd"


import pytest  # noqa: E402

_FORWARDED_BAD = [
    {"amount": -5, "to_account": "acct-123456"},
    {"amount": 10 ** 9, "to_account": "acct-123456"},
    {"amount": 100, "to_account": "../../etc/passwd"},
    {"amount": 100, "to_account": "acct-123456; DROP"},
    {"amount": 100, "to_account": "$(whoami)"},
]


@pytest.mark.parametrize("raw", _FORWARDED_BAD)
def test_proof_raw_dispatcher_forwards_bad_value(raw) -> None:
    out = h.RawDispatcher().dispatch(raw)
    assert out["amount"] == raw["amount"] and out["to"] == raw["to_account"], raw
