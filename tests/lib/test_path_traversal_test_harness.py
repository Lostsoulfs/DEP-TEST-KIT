"""Oracle + CLI-contract test for path_traversal (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_path_traversal_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import path_traversal_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.resolves_within_base(h.SafeJoiner) is True


import pytest  # noqa: E402

_TRAVERSALS = [
    "../../etc/passwd", "../../../etc/shadow", "../../../../root/.ssh/id_rsa",
    "foo/../../../etc/passwd", "/etc/passwd", "../",
]


@pytest.mark.parametrize("user_path", _TRAVERSALS)
def test_oracle_rejects_traversal(user_path) -> None:
    with pytest.raises(ValueError):
        h.SafeJoiner().resolve(h._BASE, user_path)


_INBASE_PATHS = ["docs/index.html", "img/logo.png", "a/b/c.txt", "file.txt"]


@pytest.mark.parametrize("user_path", _INBASE_PATHS)
def test_oracle_resolves_inbase_path(user_path) -> None:
    resolved = h.SafeJoiner().resolve(h._BASE, user_path)
    assert resolved.startswith(h._BASE), user_path


# === our own / batch 6 (original; copy-verified vs werkzeug.safe_join) ===
# Knox (absurd/sw) + math: safe_join rejects more than a leading "../" -- an ABSOLUTE path and
# an embedded traversal both return None (raising ValueError), not just the leading-dotdot case.
def test_oracle_safe_join_rejects_absolute_and_embedded_traversal() -> None:
    for bad in ("/etc/passwd", "docs/../../etc/passwd", "a/b/../../../etc"):
        try:
            h.SafeJoiner().resolve(h._BASE, bad)
            rejected = False
        except Exception:
            rejected = True
        assert rejected is True, bad
