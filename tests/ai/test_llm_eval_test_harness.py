from harnesses.ai import llm_eval_test_harness as h


def test_grounded_answer_is_faithful() -> None:
    assert h.answer_is_faithful(h.GROUNDED_ANSWER) is True


def test_self_test_passes() -> None:
    assert h.run_self_test() == 0
