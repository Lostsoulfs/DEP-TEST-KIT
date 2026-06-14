"""Proof: schemathesis catches the contract drift; the conformant app passes."""

from harnesses.lib import openapi_fuzz_test_harness as h


def test_proof_string_typed_count_is_caught() -> None:
    # The contract promises an integer; the buggy app returns a string.
    assert h.conforms_to_contract(h.BUGGY_COUNT) is False


def test_proof_conformant_app_is_not_flagged() -> None:
    assert h.conforms_to_contract(h.ORACLE_COUNT) is True
