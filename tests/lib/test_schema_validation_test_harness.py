from harnesses.lib import schema_validation_test_harness as h


def test_oracle_handles_every_coverage_variant() -> None:
    assert h.mishandles_a_variant(h.area) is False


def test_coverage_set_spans_all_enum_variants() -> None:
    shapes = {fig.shape for fig in h.FigureFactory.coverage()}
    assert shapes == set(h.Shape)


def test_self_test_passes() -> None:
    assert h.run_self_test() == 0
