"""Proof: a real sandbox refuses the escape probe that eval() evaluates. The unsafe
evaluator executes '().__class__.__bases__'; the simpleeval sandbox refuses it."""

from harnesses.ai import agent_safe_eval_test_harness as h


def test_proof_unsafe_evaluator_executes_payload() -> None:
    assert h.executes_payload(h.UnsafeEvaluator) is True


def test_proof_safe_evaluator_blocks_payload() -> None:
    assert h.executes_payload(h.SafeEvaluator) is False


def test_proof_safe_evaluator_does_math() -> None:
    assert h.evaluates_safe_math(h.SafeEvaluator) is True


# --- scenario coverage: raw eval() runs the attribute-traversal escape probe ---
def test_proof_unsafe_eval_runs_attribute_escape() -> None:
    assert h.executes_payload(h.UnsafeEvaluator) is True


import pytest  # noqa: E402


@pytest.mark.parametrize("expr", ["().__class__", "(1).__class__", "[].__class__", "''.__class__"])
def test_proof_unsafe_eval_runs_attribute_access(expr) -> None:
    h.UnsafeEvaluator().eval(expr)  # no exception == the escape was evaluated
