"""Proof: an algorithm policy rejects a valid-but-deprecated signature the legacy verifier
accepts. The legacy verifier accepts RSA-1024 + SHA-1; the agile verifier rejects it on policy."""

from harnesses.lib import crypto_agility_test_harness as h


def test_proof_legacy_accepts_deprecated() -> None:
    assert h.accepts_deprecated_signature(h.LegacyVerifier) is True


def test_proof_agile_rejects_deprecated() -> None:
    assert h.accepts_deprecated_signature(h.CryptoAgileVerifier) is False


def test_proof_agile_accepts_strong() -> None:
    assert h.accepts_strong_signature(h.CryptoAgileVerifier) is True


# --- scenario coverage: the legacy verifier accepts deprecated key sizes too ---
from cryptography.hazmat.primitives import hashes as _hashes  # noqa: E402


def test_proof_legacy_accepts_deprecated_keys() -> None:
    for bits, alg in ((1024, _hashes.SHA1()), (2048, _hashes.SHA256())):
        pub, sig = h._rsa_signed(bits, alg)
        assert h.LegacyVerifier().verify(pub, sig, h._MESSAGE, alg) is True


# === our own / batch 3 (original) ===
# Math/Adeyemi: the legacy verifier trusts key sizes the agile policy (and NIST after 2030) reject.
def test_proof_legacy_accepts_subthreshold_keysizes() -> None:
    from cryptography.hazmat.primitives import hashes
    for bits in (1024, 2048):
        pub, sig = h._rsa_signed(bits, hashes.SHA256())
        assert h.LegacyVerifier().verify(pub, sig, h._MESSAGE, hashes.SHA256()) is True
