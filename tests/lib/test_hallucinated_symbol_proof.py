"""Proof: the harness has teeth — the oracle catches hallucinated attributes that the naive
(module-only) checker misses; the oracle stays clean on real code."""

from harnesses.lib import hallucinated_symbol_test_harness as h


def test_proof_oracle_catches_hallucinated_attributes() -> None:
    found = set(h.hallucinated_attributes(h.HALLUCINATED_SRC))
    assert {"BaseModelz", "field_validatorr"} <= found


def test_proof_buggy_checker_misses_hallucinated_attributes() -> None:
    # The naive checker only verifies the module imports, so it flags nothing.
    found = set(h.buggy_hallucinated_attributes(h.HALLUCINATED_SRC))
    assert {"BaseModelz", "field_validatorr"} & found == set()


def test_proof_oracle_clean_on_real_source() -> None:
    assert h.hallucinated_attributes(h.REAL_SRC) == []
