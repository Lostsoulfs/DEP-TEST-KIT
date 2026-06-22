"""Oracle + CLI-contract test for subresource_integrity (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_subresource_integrity_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import subresource_integrity_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.loads_intact_resource(h.SriVerifier) is True


import pytest  # noqa: E402

_TAMPERS = [
    lambda d: b"X" + d, lambda d: d + b"X", lambda d: d[:5] + b"X" + d[6:],
    lambda d: b"", lambda d: b"evil",
]


@pytest.mark.parametrize("mutate", _TAMPERS)
def test_oracle_rejects_tampered_resource(mutate) -> None:
    good = b"console.log('ok')"
    expected = h._sri(good)
    try:
        h.SriVerifier().load(mutate(good), expected)
        accepted = True
    except Exception:
        accepted = False
    assert accepted is False


_INTACT_RESOURCES = [b"", b"x", b"console.log(1)", b"\x00\x01\x02\xff", bytes(range(256))]


@pytest.mark.parametrize("data", _INTACT_RESOURCES)
def test_oracle_loads_intact_resource(data) -> None:
    assert h.SriVerifier().load(data, h._sri(data)) == data


@pytest.mark.parametrize("data", _INTACT_RESOURCES)
def test_oracle_rejects_wrong_hash(data) -> None:
    try:
        h.SriVerifier().load(data, "sha256-wronghash")
        rejected = False
    except Exception:
        rejected = True
    assert rejected is True


# === our own / batch 5 (original; no-downgrade) ===
# Brandt (absurd/psych): the verifier always RECOMPUTES SHA-384, so a weaker-algorithm expected
# string ("sha1-...") can never match -- an attacker cannot downgrade the integrity check.
def test_oracle_no_algorithm_downgrade() -> None:
    import base64
    import hashlib
    data = b"console.log('ok')"
    sha1_expected = "sha1-" + base64.b64encode(hashlib.sha1(data).digest()).decode()
    try:
        h.SriVerifier().load(data, sha1_expected)
        downgraded = True
    except Exception:
        downgraded = False
    assert downgraded is False
    assert h.SriVerifier().load(data, h._sri(data)) == data
