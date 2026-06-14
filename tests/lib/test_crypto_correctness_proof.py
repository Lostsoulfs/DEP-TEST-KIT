"""Proof: the harness has teeth — a tampered ciphertext is accepted by the buggy
(unauthenticated) box and rejected by the oracle (AEAD). A mock/example test
catches neither."""

from harnesses.lib import crypto_correctness_test_harness as h


def test_proof_buggy_accepts_forgery() -> None:
    assert h.accepts_tampered_ciphertext(h.BuggyBox()) is True


def test_proof_oracle_rejects_forgery() -> None:
    assert h.accepts_tampered_ciphertext(h.AeadBox()) is False


def test_proof_buggy_decrypts_tamper_to_silent_garbage() -> None:
    box = h.BuggyBox()
    nonce, ct = box.encrypt(b"transfer $100 to alice")
    tampered = bytes([ct[0] ^ 0x01]) + ct[1:]
    out = box.decrypt(nonce, tampered)
    assert out != b"transfer $100 to alice"  # silently wrong, no exception raised
