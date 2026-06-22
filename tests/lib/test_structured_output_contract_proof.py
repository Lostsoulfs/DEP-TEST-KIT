"""Proof: JSON Schema validation of model output stops the malformed tool call the trusting
executor acts on. The trusting executor acts on a negative amount / bad account / injected
field; the validating executor rejects it."""

from harnesses.lib import structured_output_contract_test_harness as h


def test_proof_trusting_executor_caught_by_detector() -> None:
    assert h.executes_malformed_output(h.TrustingExecutor) is True


def test_proof_validating_executor_rejects_malformed() -> None:
    assert h.executes_malformed_output(h.ValidatingExecutor) is False


def test_proof_validating_executor_allows_valid() -> None:
    assert h.executes_valid_output(h.ValidatingExecutor) is True


# --- scenario coverage: the trusting executor acts on malformed output ---
def test_proof_trusting_executor_acts_on_sample_malformed() -> None:
    malformed = {"tool": "transfer", "amount": -5, "to": "../etc/passwd", "role": "admin"}
    assert h.TrustingExecutor().execute(malformed)["ok"] is True


import pytest  # noqa: E402

_BASE = {"tool": "transfer", "amount": 100, "to": "acct-123456"}
_MALFORMED_CORPUS = [
    ("negative_amount", {**_BASE, "amount": -5}),
    ("over_max_amount", {**_BASE, "amount": 10 ** 9}),
    ("string_amount", {**_BASE, "amount": "100"}),
    ("path_traversal_to", {**_BASE, "to": "../etc/passwd"}),
    ("sqli_to", {**_BASE, "to": "acct-1; DROP"}),
    ("extra_field", {**_BASE, "role": "admin"}),
    ("bad_tool_enum", {**_BASE, "tool": "exfiltrate"}),
    ("missing_amount", {"tool": "transfer", "to": "acct-123456"}),
]


@pytest.mark.parametrize("name,output", _MALFORMED_CORPUS)
def test_proof_trusting_executor_acts_on_malformed(name, output) -> None:
    assert h.TrustingExecutor().execute(output)["ok"] is True, name
