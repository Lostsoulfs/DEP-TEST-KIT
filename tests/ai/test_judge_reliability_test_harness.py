from harnesses.ai import judge_reliability_test_harness as h


def test_self_test_passes() -> None:
    assert h.run_self_test() == 0


def test_oracle_judge_passes_both_pillars() -> None:
    report = h.reliability_report(h.oracle_judge)
    assert report.stable is True
    assert report.spans_verbatim is True
    assert report.is_successful() is True


def test_verbatim_span_predicate_rejects_trivial_and_absent_spans() -> None:
    src = h.SOURCE
    assert h.cites_verbatim_span(h.Verdict("supported", "the"), src) is False  # too short
    assert h.cites_verbatim_span(h.Verdict("supported", "not in the source text"), src) is False
    assert h.cites_verbatim_span(h.Verdict("supported", "completed in 1889 and stands"), src) is True
