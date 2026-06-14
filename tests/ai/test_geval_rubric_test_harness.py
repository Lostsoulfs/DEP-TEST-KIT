from harnesses.ai import geval_rubric_test_harness as h


def test_oracle_output_passes() -> None:
    assert h.output_satisfies_rubric(h.ORACLE_OUTPUT) is True


def test_rubric_catches_other_violations() -> None:
    # Each violates a different hard-coded step, so none should pass the full rubric.
    assert h.output_satisfies_rubric("not json at all") is False           # step 1
    assert h.output_satisfies_rubric('{"verdict": "pass"}') is False        # step 2 (missing key)
    assert h.output_satisfies_rubric('{"verdict": "maybe", "confidence": 0.5}') is False  # step 3


def test_self_test_passes() -> None:
    assert h.run_self_test() == 0
