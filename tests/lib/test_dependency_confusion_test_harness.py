"""Oracle + CLI-contract test for dependency_confusion (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_dependency_confusion_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import dependency_confusion_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.resolves_internal_package(h.PinnedResolver) is True


import pytest  # noqa: E402

_CONFUSION_POOLS = [
    [("1.0.0", "internal"), ("9.9.9", "public")],
    [("1.0.0", "internal"), ("2.0.0", "public"), ("3.0.0", "public")],
    [("0.0.1", "internal"), ("99.0.0", "public")],
    [("1.0.0", "internal"), ("1.0.1", "public")],
]


@pytest.mark.parametrize("candidates", _CONFUSION_POOLS)
def test_oracle_pins_internal_source(candidates) -> None:
    assert h.PinnedResolver().resolve("internal-lib", candidates)[1] == "internal", candidates


@pytest.mark.parametrize("name,candidates,expected_source", [
    ("requests", [("2.0.0", "public"), ("2.1.0", "public")], "public"),
    ("internal-lib", [("1.0.0", "internal")], "internal"),
    ("flask", [("3.0.0", "public")], "public"),
])
def test_oracle_resolves_benign_package(name, candidates, expected_source) -> None:
    assert h.PinnedResolver().resolve(name, candidates)[1] == expected_source


# === our own / batch 5 (original; math: PEP 440 epoch) ===
# Knox (absurd/sw): PEP 440 epochs ("1!0.0.0") sort above every normal version -- the classic
# "highest version wins" dependency-confusion trap. The pinned resolver ignores version and
# stays on the internal source; only the buggy resolver takes the epoch-versioned impostor.
def test_oracle_epoch_version_impostor_still_pinned() -> None:
    from packaging.version import Version
    assert Version("1!0.0.0") > Version("9.9.9")
    cands = [("1.0.0", "internal"), ("1!0.0.0", "public")]
    assert h.PinnedResolver().resolve("internal-lib", cands)[1] == "internal"
