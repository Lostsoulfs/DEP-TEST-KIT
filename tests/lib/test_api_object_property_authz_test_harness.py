"""Oracle + CLI-contract test for api_object_property_authz (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_api_object_property_authz_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import api_object_property_authz_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.returns_public_fields(h.AllowListSerializer) is True


# --- scenario coverage: the allow-list serializer drops ALL non-public fields ---
_RECORD2 = {"id": 7, "name": "Bob", "password_hash": "x", "ssn": "1",
            "is_admin": True, "api_token": "sk-live-1", "session_id": "sess-9"}
_SECRETS2 = {"password_hash", "ssn", "is_admin", "api_token", "session_id"}


def test_oracle_drops_all_nonpublic_fields() -> None:
    out = h.AllowListSerializer().serialize(_RECORD2)
    assert set(out.keys()) == {"id", "name"}
    assert not any(field in out for field in _SECRETS2)


def test_oracle_preserves_public_values() -> None:
    out = h.AllowListSerializer().serialize(_RECORD2)
    assert out["id"] == 7 and out["name"] == "Bob"


# --- second pass: a public-only record is preserved (no over-drop) ---
def test_oracle_preserves_public_only_record() -> None:
    out = h.AllowListSerializer().serialize({"id": 3, "name": "Cara"})
    assert out == {"id": 3, "name": "Cara"}


# --- third pass: never leaks across varied records ---
def test_oracle_never_leaks_on_varied_records() -> None:
    for record in [{"id": 1, "name": "A", "secret": "s"}, {"id": 2, "name": "B", "token": "t"}]:
        out = h.AllowListSerializer().serialize(record)
        assert set(out.keys()) == {"id", "name"}, record


import pytest  # noqa: E402

_LEAKY_RECORDS = [
    {"id": 1, "name": "A", "password_hash": "x"},
    {"id": 2, "name": "B", "ssn": "123-45-6789"},
    {"id": 3, "name": "C", "is_admin": True},
    {"id": 4, "name": "D", "api_token": "sk-1", "session_id": "s"},
    {"id": 5, "name": "E", "credit_card": "4111111111111111", "cvv": "123"},
    {"id": 6, "name": "F", "internal_notes": "secret", "salary": 99999},
    {"id": 7, "name": "G", "role": "admin", "mfa_secret": "JBSWY3DP"},
]


@pytest.mark.parametrize("record", _LEAKY_RECORDS)
def test_oracle_drops_all_extra_fields(record) -> None:
    out = h.AllowListSerializer().serialize(record)
    assert set(out.keys()) == {"id", "name"}, record
