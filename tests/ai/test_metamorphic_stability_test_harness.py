from harnesses.ai import metamorphic_stability_test_harness as h


def test_oracle_answers_consistently() -> None:
    # The oracle gives the same answer across hand-written meaning-preserving phrasings.
    base = h.respond_stable(h.BASE_QUESTION)
    assert base == "Paris"
    assert base == h.respond_stable(h.BASE_QUESTION.upper())
    assert base == h.respond_stable("  " + h.BASE_QUESTION.rstrip("?") + "  ")


def test_self_test_passes() -> None:
    assert h.run_self_test() == 0
