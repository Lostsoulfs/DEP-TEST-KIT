from harnesses.ai import rag_faithfulness_test_harness as h


def test_oracle_retrieval_is_precise() -> None:
    assert h.retrieval_is_precise(h.oracle_retrieve) is True


def test_metric_scores_zero_for_distractors() -> None:
    from deepeval.test_case import LLMTestCase

    metric = h.ContextPrecisionMetric(threshold=1.0)
    case = LLMTestCase(input=h.QUESTION, actual_output="x",
                       retrieval_context=h.buggy_retrieve(h.QUESTION))
    assert metric.measure(case) == 0.0


def test_self_test_passes() -> None:
    assert h.run_self_test() == 0
