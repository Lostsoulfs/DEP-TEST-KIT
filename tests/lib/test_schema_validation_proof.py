"""Proof: the harness catches the missing-variant bug and clears the oracle."""

from harnesses.lib import schema_validation_test_harness as h


def test_proof_buggy_handler_is_caught() -> None:
    assert h.mishandles_a_variant(h.buggy_area) is True


def test_proof_oracle_is_not_flagged() -> None:
    assert h.mishandles_a_variant(h.area) is False


def test_proof_buggy_triangle_is_concretely_wrong() -> None:
    # The omitted branch yields a degenerate, impossible area for a real triangle.
    assert h.buggy_area(h.Figure(shape=h.Shape.TRIANGLE)) == 0.0
    assert h.area(h.Figure(shape=h.Shape.TRIANGLE)) > 0.0
