"""Proof: digest binding catches the artifact swap a signature-only check misses. The
sig-only verifier accepts a malicious artifact under a good artifact's valid attestation;
the binding verifier rejects it."""

from harnesses.lib import provenance_attestation_test_harness as h


def test_proof_sig_only_accepts_unbound() -> None:
    assert h.accepts_unbound_artifact(h.SigOnlyVerifier) is True


def test_proof_binding_verifier_rejects_unbound() -> None:
    assert h.accepts_unbound_artifact(h.ProvenanceVerifier) is False


def test_proof_binding_verifier_accepts_bound() -> None:
    assert h.verifies_bound_artifact(h.ProvenanceVerifier) is True


# --- scenario coverage: the signature-only verifier accepts a swapped artifact ---
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey as _Ed  # noqa: E402


def test_proof_sigonly_accepts_swapped_artifact() -> None:
    builder = _Ed.generate()
    attestation, sig = h._attest(b"legit-1.0.0", builder)
    verifier = h.SigOnlyVerifier(builder.public_key())
    assert verifier.verify(b"EVIL-artifact", attestation, sig) is True
