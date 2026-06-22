"""Proof: the allowlist CORS denies the attacker origin the reflecting CORS echoes.
evil.com gets no ACAO vs being reflected back with credentials."""

from harnesses.lib import cors_misconfig_test_harness as h


def test_proof_buggy_is_flagged() -> None:
    assert h.reflects_untrusted_origin(h.ReflectingCors) is True


def test_proof_oracle_not_flagged() -> None:
    assert h.reflects_untrusted_origin(h.AllowlistCors) is False


def test_proof_oracle_happy_path() -> None:
    assert h.allows_trusted_origin(h.AllowlistCors) is True


import pytest  # noqa: E402

_UNTRUSTED_ORIGINS = [
    "null", "https://evil.com", "https://app.example.evil.com", "https://evilapp.example",
    "https://app.example.attacker.com", "https://sub.app.example",
]


@pytest.mark.parametrize("origin", _UNTRUSTED_ORIGINS)
def test_proof_reflecting_cors_echoes_untrusted(origin) -> None:
    assert h.ReflectingCors().headers(origin).get(h._ACAO) == origin, origin
