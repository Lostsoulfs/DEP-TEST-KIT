"""Oracle + CLI-contract test for provenance_attestation (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_provenance_attestation_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import provenance_attestation_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.verifies_bound_artifact(h.ProvenanceVerifier) is True


# --- scenario coverage: the provenance verifier rejects swap / tamper / wrong-key ---
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey as _Ed  # noqa: E402


def _verify_ok(verifier, artifact, attestation, signature):
    try:
        return bool(verifier.verify(artifact, attestation, signature))
    except Exception:
        return False


def test_oracle_rejects_swap_tamper_and_wrong_key() -> None:
    builder = _Ed.generate()
    attestation, sig = h._attest(b"legit-1.0.0", builder)
    good = h.ProvenanceVerifier(builder.public_key())
    other = h.ProvenanceVerifier(_Ed.generate().public_key())
    bad_att = attestation[:-1] + bytes([attestation[-1] ^ 1])
    assert _verify_ok(good, b"EVIL-artifact", attestation, sig) is False
    assert _verify_ok(good, b"legit-1.0.0", bad_att, sig) is False
    assert _verify_ok(other, b"legit-1.0.0", attestation, sig) is False


def test_oracle_accepts_bound_artifact() -> None:
    builder = _Ed.generate()
    attestation, sig = h._attest(b"legit-1.0.0", builder)
    verifier = h.ProvenanceVerifier(builder.public_key())
    assert _verify_ok(verifier, b"legit-1.0.0", attestation, sig) is True


# --- second pass: another correctly-bound artifact verifies ---
def test_oracle_accepts_another_bound_artifact() -> None:
    builder = _Ed.generate()
    attestation, sig = h._attest(b"another-pkg-2.3.1", builder)
    verifier = h.ProvenanceVerifier(builder.public_key())
    assert _verify_ok(verifier, b"another-pkg-2.3.1", attestation, sig) is True


import pytest  # noqa: E402


def _flip(b, i):
    return b[:i] + bytes([b[i] ^ 1]) + b[i + 1:]


@pytest.mark.parametrize("name,artifact", [
    ("swap_evil", b"EVIL-package"),
    ("swap_empty", b""),
    ("swap_prefix", b"legit-1.0.0-with-backdoor"),
])
def test_oracle_rejects_swapped_artifact_corpus(name, artifact) -> None:
    builder = _Ed.generate()
    attestation, sig = h._attest(b"legit-1.0.0", builder)
    verifier = h.ProvenanceVerifier(builder.public_key())
    assert _verify_ok(verifier, artifact, attestation, sig) is False, name


_PROV_MUTATIONS = [
    ("flip_att_start", lambda a, s: (_flip(a, 0), s)),
    ("flip_att_end", lambda a, s: (_flip(a, len(a) - 1), s)),
    ("flip_sig", lambda a, s: (a, _flip(s, 0))),
    ("zero_sig", lambda a, s: (a, b"\x00" * len(s))),
    ("truncate_sig", lambda a, s: (a, s[:-1])),
]


@pytest.mark.parametrize("name,mutate", _PROV_MUTATIONS)
def test_oracle_rejects_provenance_mutation(name, mutate) -> None:
    builder = _Ed.generate()
    attestation, sig = h._attest(b"legit-1.0.0", builder)
    bad_att, bad_sig = mutate(attestation, sig)
    verifier = h.ProvenanceVerifier(builder.public_key())
    assert _verify_ok(verifier, b"legit-1.0.0", bad_att, bad_sig) is False, name


# === our own / batch 2 (original) ===
# Brandt (absurd/psych): you cannot relabel a signed parcel -- subject_sha256 lives INSIDE the
# attestation the builder signed, so editing it to match a malicious artifact breaks the sig.
def test_oracle_cannot_relabel_signed_digest() -> None:
    import json
    import hashlib
    builder = _Ed.generate()
    good = b"legit-package-1.0.0"
    att, sig = h._attest(good, builder)
    mal = b"MALICIOUS-package-with-backdoor"
    relabel = json.loads(att)
    relabel["subject_sha256"] = hashlib.sha256(mal).hexdigest()
    forged_att = json.dumps(relabel, sort_keys=True).encode()
    assert forged_att != att
    try:
        h.ProvenanceVerifier(builder.public_key()).verify(mal, forged_att, sig)
        relabelled = True
    except Exception:
        relabelled = False
    assert relabelled is False


# Adeyemi (whimsical/psych): one flipped byte is a whole new identity -- a single-bit edit of
# the attested artifact no longer matches its digest, even under a valid attestation.
def test_oracle_one_bit_artifact_change_unbinds() -> None:
    builder = _Ed.generate()
    good = b"legit-package-1.0.0"
    att, sig = h._attest(good, builder)
    ver = h.ProvenanceVerifier(builder.public_key())
    nudged = bytes([good[0] ^ 0x01]) + good[1:]
    try:
        ver.verify(nudged, att, sig)
        bound = True
    except Exception:
        bound = False
    assert bound is False
    assert ver.verify(good, att, sig) is True  # the true artifact still binds
