"""Oracle + CLI-contract test for jwt_audience_binding (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_jwt_audience_binding_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import jwt_audience_binding_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.accepts_correct_audience(h.AudienceBindingVerifier) is True


# --- scenario coverage: audience binding rejects wrong/missing-aud, expiry, and tamper ---
import time as _time  # noqa: E402

import jwt as _jwt  # noqa: E402


def _verify_ok(make_verifier, audience, token):
    try:
        make_verifier(audience).verify(token)
        return True
    except Exception:
        return False


def test_oracle_accepts_matching_audience() -> None:
    assert _verify_ok(h.AudienceBindingVerifier, "service-B", h._token("service-B")) is True


def test_oracle_rejects_wrong_and_missing_audience() -> None:
    assert _verify_ok(h.AudienceBindingVerifier, "service-B", h._token("service-A")) is False
    no_aud = _jwt.encode({"sub": "u1"}, h._SECRET, algorithm="HS256")
    assert _verify_ok(h.AudienceBindingVerifier, "service-B", no_aud) is False


def test_oracle_rejects_expired_and_tampered_tokens() -> None:
    expired = _jwt.encode(
        {"sub": "u1", "aud": "service-B", "exp": int(_time.time()) - 10},
        h._SECRET,
        algorithm="HS256",
    )
    assert _verify_ok(h.AudienceBindingVerifier, "service-B", expired) is False
    token = h._token("service-B")
    tampered = token[:-2] + ("aa" if token[-2:] != "aa" else "bb")
    assert _verify_ok(h.AudienceBindingVerifier, "service-B", tampered) is False


# --- second pass: audience-in-list accepted; wrong-secret signature rejected ---
def test_oracle_accepts_audience_in_list() -> None:
    token = _jwt.encode(
        {"sub": "u1", "aud": ["service-A", "service-B"]}, h._SECRET, algorithm="HS256"
    )
    assert _verify_ok(h.AudienceBindingVerifier, "service-B", token) is True


def test_oracle_rejects_wrong_secret_signature() -> None:
    token = _jwt.encode({"sub": "u1", "aud": "service-B"}, "WRONG-SECRET", algorithm="HS256")
    assert _verify_ok(h.AudienceBindingVerifier, "service-B", token) is False


# --- third pass: garbage tokens never verify ---
def test_oracle_never_verifies_garbage_tokens() -> None:
    for token in ["", "a.b.c", "....", "not.a.jwt", "x" * 100]:
        assert _verify_ok(h.AudienceBindingVerifier, "service-B", token) is False, token


# --- third pass (researched): JWT algorithm-confusion attacks rejected (oracle pins HS256) ---
# Sources: PortSwigger JWT attacks; alg:none + RS256->HS256 confusion (still live in 2026).
def test_oracle_rejects_algorithm_confusion_attacks() -> None:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    none_token = _jwt.encode({"sub": "u1", "aud": "service-B"}, "", algorithm="none")
    assert _verify_ok(h.AudienceBindingVerifier, "service-B", none_token) is False

    rsa_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = rsa_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )
    rs256_token = _jwt.encode({"sub": "u1", "aud": "service-B"}, pem, algorithm="RS256")
    assert _verify_ok(h.AudienceBindingVerifier, "service-B", rs256_token) is False


import time  # noqa: E402

import pytest  # noqa: E402


def _jwt_attack_tokens():
    # Researched JWT attack corpus (PortSwigger; alg confusion + claim validation).
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec, rsa

    base = {"sub": "u1", "aud": "service-B"}
    now = int(time.time())

    def pem(key):
        return key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )

    ec_pem = pem(ec.generate_private_key(ec.SECP256R1()))
    rsa_pem = pem(rsa.generate_private_key(public_exponent=65537, key_size=2048))
    valid = _jwt.encode(base, h._SECRET, algorithm="HS256")
    wrong_aud = {"sub": "u1", "aud": "svc-A"}
    return [
        ("hs384_confusion", _jwt.encode(base, h._SECRET, algorithm="HS384")),
        ("hs512_confusion", _jwt.encode(base, h._SECRET, algorithm="HS512")),
        ("es256_confusion", _jwt.encode(base, ec_pem, algorithm="ES256")),
        ("ps256_confusion", _jwt.encode(base, rsa_pem, algorithm="PS256")),
        ("rs384_confusion", _jwt.encode(base, rsa_pem, algorithm="RS384")),
        ("alg_none", _jwt.encode(base, "", algorithm="none")),
        ("nbf_future", _jwt.encode({**base, "nbf": now + 3600}, h._SECRET, algorithm="HS256")),
        ("empty_signature", valid.rsplit(".", 1)[0] + "."),
        ("wrong_secret", _jwt.encode(base, "WRONG-SECRET", algorithm="HS256")),
        ("wrong_audience", _jwt.encode(wrong_aud, h._SECRET, algorithm="HS256")),
        ("missing_audience", _jwt.encode({"sub": "u1"}, h._SECRET, algorithm="HS256")),
        ("expired", _jwt.encode({**base, "exp": now - 10}, h._SECRET, algorithm="HS256")),
    ]


@pytest.mark.parametrize("name,token", _jwt_attack_tokens())
def test_oracle_rejects_jwt_attack(name, token) -> None:
    assert _verify_ok(h.AudienceBindingVerifier, "service-B", token) is False, name
