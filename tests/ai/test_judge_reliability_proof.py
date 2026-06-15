"""Proof: the harness has teeth on BOTH pillars — a flaky judge and a content-blind judge
are each caught, and the reliable oracle judge clears."""

from harnesses.ai import judge_reliability_test_harness as h


def test_proof_flaky_judge_caught_on_variance_pillar() -> None:
    report = h.reliability_report(h.unstable_judge)
    assert report.is_successful() is False
    assert report.stable is False           # caught specifically by the variance pillar
    assert report.spans_verbatim is True    # its span IS real — only variance fails it


def test_proof_content_blind_judge_caught_on_span_pillar() -> None:
    report = h.reliability_report(h.blind_judge)
    assert report.is_successful() is False
    assert report.spans_verbatim is False   # caught specifically by the span pillar
    assert report.stable is True            # it is perfectly stable — only the span fails it


def test_proof_oracle_judge_is_not_caught() -> None:
    assert h.judge_is_reliable(h.oracle_judge) is True
