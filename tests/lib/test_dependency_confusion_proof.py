"""Proof: the pinned resolver keeps the internal source the highest-version resolver abandons.
internal 1.0.0 wins over public 9.9.9 only when the source is pinned."""

from harnesses.lib import dependency_confusion_test_harness as h


def test_proof_buggy_is_flagged() -> None:
    assert h.resolves_public_over_internal(h.HighestVersionResolver) is True


def test_proof_oracle_not_flagged() -> None:
    assert h.resolves_public_over_internal(h.PinnedResolver) is False


def test_proof_oracle_happy_path() -> None:
    assert h.resolves_internal_package(h.PinnedResolver) is True


import pytest  # noqa: E402

_CONFUSION_POOLS = [
    [("1.0.0", "internal"), ("9.9.9", "public")],
    [("1.0.0", "internal"), ("2.0.0", "public"), ("3.0.0", "public")],
    [("0.0.1", "internal"), ("99.0.0", "public")],
    [("1.0.0", "internal"), ("1.0.1", "public")],
]


@pytest.mark.parametrize("candidates", _CONFUSION_POOLS)
def test_proof_highest_version_picks_public(candidates) -> None:
    chosen = h.HighestVersionResolver().resolve("internal-lib", candidates)
    assert chosen[1] == "public", candidates
