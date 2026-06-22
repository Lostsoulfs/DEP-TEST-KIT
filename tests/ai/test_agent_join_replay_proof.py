"""Proof: a stateful replay check exposes what a signature-only check misses. The
no-replay admission accepts an identical, validly-signed token twice; the guarded
admission rejects the second (replay)."""

from harnesses.ai import agent_join_replay_test_harness as h


def test_proof_no_replay_admission_accepts_replay() -> None:
    assert h.admits_replayed_token(h.NoReplayAdmission) is True


def test_proof_guarded_admission_rejects_replay() -> None:
    assert h.admits_replayed_token(h.ReplayGuardedAdmission) is False


def test_proof_guarded_admission_admits_valid_once() -> None:
    assert h.admits_valid_once(h.ReplayGuardedAdmission) is True


# --- scenario coverage: the no-replay admission re-admits the same token ---
def test_proof_noreplay_admits_replay() -> None:
    pub, payload, sig = h._make_token(nonce="n-proof")
    admission = h.NoReplayAdmission(pub)
    assert bool(admission.admit(payload, sig)) is True
    assert bool(admission.admit(payload, sig)) is True
