"""Oracle + CLI-contract test for crypto_agility (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_crypto_agility_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import crypto_agility_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.accepts_strong_signature(h.CryptoAgileVerifier) is True


# --- scenario coverage: the agile verifier rejects every deprecated algorithm ---
from cryptography.hazmat.primitives import hashes as _hashes  # noqa: E402


def _verifies(make_verifier, bits, hash_alg):
    pub, sig = h._rsa_signed(bits, hash_alg)
    try:
        return bool(make_verifier().verify(pub, sig, h._MESSAGE, hash_alg))
    except Exception:
        return False


def test_oracle_rejects_deprecated_algorithms() -> None:
    cases = {
        "rsa1024_sha256": (1024, _hashes.SHA256()),
        "rsa2048_sha256": (2048, _hashes.SHA256()),
        "rsa3072_sha1": (3072, _hashes.SHA1()),
    }
    for name, (bits, alg) in cases.items():
        assert _verifies(h.CryptoAgileVerifier, bits, alg) is False, name


def test_oracle_accepts_rsa3072_sha256() -> None:
    assert _verifies(h.CryptoAgileVerifier, 3072, _hashes.SHA256()) is True


# --- second pass: other approved strong hashes are accepted ---
def test_oracle_accepts_other_approved_hashes() -> None:
    assert _verifies(h.CryptoAgileVerifier, 3072, _hashes.SHA384()) is True
    assert _verifies(h.CryptoAgileVerifier, 3072, _hashes.SHA512()) is True


import pytest  # noqa: E402

# --- pass 4 (researched corpus): NIST/CNSA-2.0 weak-algorithm matrix ---
# Reject RSA < 3072 bits and any non-approved hash (SHA-1/SHA-224/MD5); accept 3072+ SHA-2.
_WEAK_ALGS = [
    ("rsa1024_sha256", 1024, "SHA256"),
    ("rsa2048_sha256", 2048, "SHA256"),
    ("rsa1024_sha1", 1024, "SHA1"),
    ("rsa2048_sha1", 2048, "SHA1"),
    ("rsa3072_sha1", 3072, "SHA1"),
    ("rsa3072_sha224", 3072, "SHA224"),
    ("rsa1024_md5", 1024, "MD5"),
    ("rsa3072_md5", 3072, "MD5"),
]
_STRONG_ALGS = [
    ("rsa3072_sha256", 3072, "SHA256"),
    ("rsa3072_sha384", 3072, "SHA384"),
    ("rsa3072_sha512", 3072, "SHA512"),
]


@pytest.mark.parametrize("name,bits,hash_name", _WEAK_ALGS)
def test_oracle_rejects_weak_algorithm(name, bits, hash_name) -> None:
    alg = getattr(_hashes, hash_name)()
    assert _verifies(h.CryptoAgileVerifier, bits, alg) is False, name


@pytest.mark.parametrize("name,bits,hash_name", _STRONG_ALGS)
def test_oracle_accepts_strong_algorithm(name, bits, hash_name) -> None:
    alg = getattr(_hashes, hash_name)()
    assert _verifies(h.CryptoAgileVerifier, bits, alg) is True, name


# === our own / batch 3 (original; web-checked + math-derived) ===
# NIST SP 800-131A grounding (confirmed by web search): RSA-2048 is deprecated after 2030 and
# 3072 = 128-bit security; SHA-1 + 224-bit hashes are disallowed after 2030. The oracle's
# MIN_RSA_BITS=3072 and SHA-2 allowlist track that policy -- these sweep the thresholds.

# Adeyemi (whimsical/psych) + math bench: the key-size fence -- accept iff key_size >= 3072.
@pytest.mark.parametrize(
    "bits,accepted", [(1024, False), (2048, False), (3072, True), (4096, True)])
def test_oracle_rsa_keysize_threshold_sweep(bits, accepted) -> None:
    from cryptography.hazmat.primitives import hashes
    pub, sig = h._rsa_signed(bits, hashes.SHA256())
    try:
        ok = h.CryptoAgileVerifier().verify(pub, sig, h._MESSAGE, hashes.SHA256()) is True
    except Exception:
        ok = False
    assert ok is accepted, bits


# Constantin (surreal/sw) + Adeyemi: the allowlist matches on the hash NAME, so it rejects
# sha1/sha224/md5 (NIST agrees) AND sha3-256 / sha512-256 -- which ARE NIST-approved and
# >=128-bit. Honest forward-risk: a NIST-blessed migration to SHA-3 / SHA-512-256 false-rejects.
@pytest.mark.parametrize("hash_name", ["SHA1", "SHA224", "MD5", "SHA3_256", "SHA512_256"])
def test_oracle_hash_allowlist_is_name_based(hash_name) -> None:
    from cryptography.hazmat.primitives import hashes
    pub, _ = h._rsa_signed(3072, hashes.SHA256())
    alg = getattr(hashes, hash_name)()
    try:
        h.CryptoAgileVerifier().verify(pub, b"x", h._MESSAGE, alg)  # policy gate precedes crypto
        rejected_on_policy = False
    except ValueError:
        rejected_on_policy = True
    except Exception:
        rejected_on_policy = False
    assert rejected_on_policy is True, hash_name


# Brandt (absurd/psych): rejected for the RIGHT reason -- the policy gate fires before the
# signature check, so a weak key is a ValueError (policy) and a strong wrong-key is a crypto miss.
def test_oracle_policy_gate_precedes_crypto() -> None:
    from cryptography.hazmat.primitives import hashes
    from cryptography.exceptions import InvalidSignature
    weak_pub, _ = h._rsa_signed(1024, hashes.SHA256())
    try:
        h.CryptoAgileVerifier().verify(weak_pub, b"garbage", h._MESSAGE, hashes.SHA256())
        weak_reason = "accepted"
    except ValueError:
        weak_reason = "policy"
    except Exception:
        weak_reason = "other"
    strong_pub, _ = h._rsa_signed(3072, hashes.SHA256())
    _, other_sig = h._rsa_signed(3072, hashes.SHA256())  # a 3072 signature from a DIFFERENT key
    try:
        h.CryptoAgileVerifier().verify(strong_pub, other_sig, h._MESSAGE, hashes.SHA256())
        strong_reason = "accepted"
    except InvalidSignature:
        strong_reason = "crypto"
    except Exception:
        strong_reason = "other"
    assert weak_reason == "policy" and strong_reason == "crypto"
