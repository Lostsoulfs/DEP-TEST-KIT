"""Proof: the faithfulness metric catches the hallucination; the grounded answer passes.

A plain `assert output == expected` cannot test a varying LLM answer; the deepeval
metric scores faithfulness to context and fails the fabricated "Berlin" claim.
"""

from harnesses.ai import llm_eval_test_harness as h


def test_proof_hallucination_is_caught() -> None:
    assert h.answer_is_faithful(h.HALLUCINATED_ANSWER) is False


def test_proof_grounded_answer_passes() -> None:
    assert h.answer_is_faithful(h.GROUNDED_ANSWER) is True
