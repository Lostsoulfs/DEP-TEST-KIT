from harnesses.lib import hallucinated_symbol_test_harness as h


def test_self_test_passes() -> None:
    assert h.run_self_test() == 0


def test_oracle_clean_on_real_source() -> None:
    assert h.hallucinated_attributes(h.REAL_SRC) == []


def test_attribute_exists_matches_live_surface() -> None:
    assert h.attribute_exists("BaseModel") is True          # real pydantic symbol
    assert h.attribute_exists("field_validator") is True    # real pydantic v2 symbol
    assert h.attribute_exists("BaseModelz") is False         # hallucinated
