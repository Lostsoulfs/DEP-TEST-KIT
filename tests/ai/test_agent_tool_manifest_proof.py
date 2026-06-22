"""Proof: real Ed25519 verification exposes the supply-chain swap a mock can't model.
The unverified loader accepts a tampered manifest; the signed loader rejects it."""

from harnesses.ai import agent_tool_manifest_test_harness as h


def test_proof_unverified_loader_accepts_forgery() -> None:
    assert h.accepts_tampered_manifest(h.UnverifiedToolLoader) is True


def test_proof_signed_loader_rejects_forgery() -> None:
    assert h.accepts_tampered_manifest(h.SignedToolLoader) is False


def test_proof_signed_loader_loads_valid() -> None:
    assert h.loads_valid_manifest(h.SignedToolLoader) is True


# --- scenario coverage: the unverified loader accepts a tampered signature ---
def test_proof_unverified_loader_accepts_bad_signature() -> None:
    pub, manifest, sig = h._signed_manifest()
    for bad_sig in (sig[:-1], b"\x00" * len(sig)):
        try:
            h.UnverifiedToolLoader(pub).load(manifest, bad_sig)
            accepted = True
        except Exception:
            accepted = False
        assert accepted is True
