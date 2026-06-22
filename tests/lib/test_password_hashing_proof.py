"""Proof: salted scrypt produces a different hash each time the unsalted digest collides on.
Two hashes of the same password differ under scrypt; md5 returns the identical digest."""

from harnesses.lib import password_hashing_test_harness as h


def test_proof_buggy_is_flagged() -> None:
    assert h.identical_hash_for_same_password(h.WeakHasher) is True


def test_proof_oracle_not_flagged() -> None:
    assert h.identical_hash_for_same_password(h.ScryptHasher) is False


def test_proof_oracle_happy_path() -> None:
    assert h.verifies_correct_password(h.ScryptHasher) is True


import pytest  # noqa: E402

_PASSWORDS = ["", "hunter2", "p@ss w0rd", "uñicöde", "x" * 100]


@pytest.mark.parametrize("password", _PASSWORDS)
def test_proof_weak_hasher_collides(password) -> None:
    hasher = h.WeakHasher()
    assert hasher.hash(password) == hasher.hash(password), password


# === our own / batch 5 (original) ===
# Pip (whimsical/sw): unsalted md5 gives two users with the same password the SAME hash (a
# rainbow-table / equality leak); the salted scrypt oracle yields a different hash every time.
def test_proof_md5_leaks_equal_password_equality() -> None:
    assert h.WeakHasher().hash("pw") == h.WeakHasher().hash("pw")
    assert h.ScryptHasher().hash("pw") != h.ScryptHasher().hash("pw")
