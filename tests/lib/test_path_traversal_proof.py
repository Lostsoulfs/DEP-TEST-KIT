"""Proof: safe_join rejects the traversal the naive join lets escape.
../../etc/passwd lands outside the base only under os.path.join."""

from harnesses.lib import path_traversal_test_harness as h


def test_proof_buggy_is_flagged() -> None:
    assert h.escapes_base(h.NaiveJoiner) is True


def test_proof_oracle_not_flagged() -> None:
    assert h.escapes_base(h.SafeJoiner) is False


def test_proof_oracle_happy_path() -> None:
    assert h.resolves_within_base(h.SafeJoiner) is True


import os  # noqa: E402
import pytest  # noqa: E402

_TRAVERSALS = [
    "../../etc/passwd", "../../../etc/shadow", "../../../../root/.ssh/id_rsa",
    "foo/../../../etc/passwd", "/etc/passwd", "../",
]


@pytest.mark.parametrize("user_path", _TRAVERSALS)
def test_proof_naive_join_escapes_base(user_path) -> None:
    resolved = h.NaiveJoiner().resolve(h._BASE, user_path)
    assert not os.path.normpath(resolved).startswith(h._BASE), user_path
