"""Oracle + CLI-contract test for agent_join_replay (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_agent_join_replay_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.ai import agent_join_replay_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.admits_valid_once(h.ReplayGuardedAdmission) is True


# --- scenario coverage: the replay-guarded admission rejects replay/expiry/tamper ---
def _admit(admission, payload, signature):
    try:
        return bool(admission.admit(payload, signature))
    except Exception:
        return False


def test_oracle_admits_once_then_rejects_replay() -> None:
    pub, payload, sig = h._make_token(nonce="n-replay")
    admission = h.ReplayGuardedAdmission(pub)
    assert _admit(admission, payload, sig) is True
    assert _admit(admission, payload, sig) is False


def test_oracle_rejects_expired_token() -> None:
    pub, payload, sig = h._make_token(exp=h._NOW - 10, nonce="n-exp")
    assert _admit(h.ReplayGuardedAdmission(pub), payload, sig) is False


def test_oracle_rejects_tampered_payload() -> None:
    pub, payload, sig = h._make_token(nonce="n-tamper")
    bad = payload[:-1] + bytes([payload[-1] ^ 1])
    assert _admit(h.ReplayGuardedAdmission(pub), bad, sig) is False


# --- second pass: a fresh valid token (different nonce) is admitted ---
def test_oracle_admits_a_fresh_valid_token() -> None:
    pub, payload, sig = h._make_token(nonce="fresh-77")
    assert _admit(h.ReplayGuardedAdmission(pub), payload, sig) is True


import pytest  # noqa: E402


def _flip(b, i):
    return b[:i] + bytes([b[i] ^ 1]) + b[i + 1:]


_JOIN_MUTATIONS = [
    ("flip_payload_start", lambda p, s: (_flip(p, 0), s)),
    ("flip_payload_end", lambda p, s: (_flip(p, len(p) - 1), s)),
    ("flip_sig", lambda p, s: (p, _flip(s, 0))),
    ("zero_sig", lambda p, s: (p, b"\x00" * len(s))),
    ("truncate_sig", lambda p, s: (p, s[:-1])),
    ("empty_sig", lambda p, s: (p, b"")),
]


@pytest.mark.parametrize("name,mutate", _JOIN_MUTATIONS)
def test_oracle_rejects_join_mutation(name, mutate) -> None:
    pub, payload, sig = h._make_token(nonce="mut-" + name)
    bad_p, bad_s = mutate(payload, sig)
    assert _admit(h.ReplayGuardedAdmission(pub), bad_p, bad_s) is False, name


@pytest.mark.parametrize("offset", [-1, -60, -3600, -86400])
def test_oracle_rejects_expired_offsets(offset) -> None:
    pub, payload, sig = h._make_token(exp=h._NOW + offset, nonce="exp%d" % offset)
    assert _admit(h.ReplayGuardedAdmission(pub), payload, sig) is False


# === our own / batch 2 (original) ===
def _jr_sign(priv, agent, nonce, exp):
    import json
    payload = json.dumps({"agent": agent, "nonce": nonce, "exp": exp}, sort_keys=True).encode()
    return payload, priv.sign(payload)


# Brandt (absurd/psych): the nonce namespace is one shared ledger -- admitting a token burns its
# nonce for EVERYONE, so a squatter can deny an innocent token that reuses the string.
def test_oracle_nonce_squatting_global_namespace() -> None:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    priv = Ed25519PrivateKey.generate()
    pa, sa = _jr_sign(priv, "worker-7", "dup", h._NOW + 60)
    pb, sb = _jr_sign(priv, "worker-9", "dup", h._NOW + 60)
    guard = h.ReplayGuardedAdmission(priv.public_key(), now=h._NOW)
    assert guard.admit(pa, sa) is True
    try:
        guard.admit(pb, sb)
        squatted = False
    except Exception:
        squatted = True
    assert squatted is True  # distinct signed token, same nonce -> rejected as a replay


# Adeyemi (whimsical/psych): poke the expiry fence -- now == exp is still inside, now == exp+1
# has already left.
def test_oracle_expiry_fence_boundary() -> None:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    priv = Ed25519PrivateKey.generate()
    pa, sa = _jr_sign(priv, "w", "fence-a", h._NOW)
    pb, sb = _jr_sign(priv, "w", "fence-b", h._NOW)
    assert h.ReplayGuardedAdmission(priv.public_key(), now=h._NOW).admit(pa, sa) is True
    try:
        h.ReplayGuardedAdmission(priv.public_key(), now=h._NOW + 1).admit(pb, sb)
        admitted = True
    except Exception:
        admitted = False
    assert admitted is False


# Pip (whimsical/sw): every doorman keeps a private ledger -- single-use is scoped to one guard,
# so a fresh guard admits the same token (honest scoping, not a global revocation list).
def test_oracle_single_use_is_per_verifier() -> None:
    pub, payload, sig = h._make_token(nonce="ledger-1")
    assert h.ReplayGuardedAdmission(pub).admit(payload, sig) is True
    assert h.ReplayGuardedAdmission(pub).admit(payload, sig) is True
