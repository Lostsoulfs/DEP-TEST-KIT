"""Proof: an allow-list serializer drops the secrets the full-object serializer leaks. The
full-object serializer returns password_hash/ssn; the allow-list serializer returns only id/name."""

from harnesses.lib import api_object_property_authz_test_harness as h


def test_proof_full_serializer_leaks() -> None:
    assert h.leaks_sensitive_fields(h.FullObjectSerializer) is True


def test_proof_allowlist_serializer_no_leak() -> None:
    assert h.leaks_sensitive_fields(h.AllowListSerializer) is False


def test_proof_allowlist_serializer_keeps_public() -> None:
    assert h.returns_public_fields(h.AllowListSerializer) is True


# --- scenario coverage: the full serializer leaks extra sensitive fields too ---
_RECORD2 = {"id": 7, "name": "Bob", "password_hash": "x", "ssn": "1",
            "is_admin": True, "api_token": "sk-live-1", "session_id": "sess-9"}
_SECRETS2 = {"password_hash", "ssn", "is_admin", "api_token", "session_id"}


def test_proof_full_serializer_leaks_extra_secrets() -> None:
    out = h.FullObjectSerializer().serialize(_RECORD2)
    assert all(field in out for field in _SECRETS2)


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
def test_proof_full_serializer_leaks_all_fields(record) -> None:
    out = h.FullObjectSerializer().serialize(record)
    assert set(out.keys()) == set(record.keys()), record
