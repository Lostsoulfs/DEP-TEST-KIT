"""Proof: the context-precision metric catches a retriever that returns off-topic
distractors; the on-topic retriever passes. A check of only the final answer string
would miss that the buggy retrieval never pertained to the question.
"""

from harnesses.ai import rag_faithfulness_test_harness as h


def test_proof_buggy_retrieval_is_caught() -> None:
    assert h.retrieval_is_precise(h.buggy_retrieve) is False


def test_proof_oracle_retrieval_passes() -> None:
    assert h.retrieval_is_precise(h.oracle_retrieve) is True
