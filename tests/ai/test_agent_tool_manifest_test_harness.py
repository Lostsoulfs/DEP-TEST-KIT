"""Oracle + CLI-contract test for agent_tool_manifest (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_agent_tool_manifest_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.ai import agent_tool_manifest_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.loads_valid_manifest(h.SignedToolLoader) is True


# --- scenario coverage: the signed loader rejects every manifest/signature mutation ---
def _loads(make_loader, pub, manifest, signature):
    try:
        make_loader(pub).load(manifest, signature)
        return True
    except Exception:
        return False


def test_oracle_rejects_manifest_and_signature_mutations() -> None:
    pub, manifest, sig = h._signed_manifest()
    cases = {
        "flipped_manifest": (manifest[:-1] + bytes([manifest[-1] ^ 1]), sig),
        "truncated_signature": (manifest, sig[:-1]),
        "zeroed_signature": (manifest, b"\x00" * len(sig)),
    }
    for name, (m, s) in cases.items():
        assert _loads(h.SignedToolLoader, pub, m, s) is False, name


def test_oracle_loads_untampered_manifest() -> None:
    pub, manifest, sig = h._signed_manifest()
    assert _loads(h.SignedToolLoader, pub, manifest, sig) is True


# --- second pass: a manifest verified under the wrong key is rejected ---
def test_oracle_rejects_manifest_under_wrong_key() -> None:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    pub, manifest, sig = h._signed_manifest()
    other_pub = Ed25519PrivateKey.generate().public_key()
    assert _loads(h.SignedToolLoader, other_pub, manifest, sig) is False


import pytest  # noqa: E402


def _flip(b, i):
    return b[:i] + bytes([b[i] ^ 1]) + b[i + 1:]


# --- pass 4 (corpus): every manifest/signature mutation is rejected ---
_MANIFEST_MUTATIONS = [
    ("flip_manifest_start", lambda m, s: (_flip(m, 0), s)),
    ("flip_manifest_end", lambda m, s: (_flip(m, len(m) - 1), s)),
    ("truncate_manifest", lambda m, s: (m[:-1], s)),
    ("append_manifest", lambda m, s: (m + b" ", s)),
    ("flip_sig_start", lambda m, s: (m, _flip(s, 0))),
    ("flip_sig_end", lambda m, s: (m, _flip(s, len(s) - 1))),
    ("truncate_sig", lambda m, s: (m, s[:-1])),
    ("zero_sig", lambda m, s: (m, b"\x00" * len(s))),
]


@pytest.mark.parametrize("name,mutate", _MANIFEST_MUTATIONS)
def test_oracle_rejects_manifest_mutation(name, mutate) -> None:
    pub, manifest, sig = h._signed_manifest()
    bad_manifest, bad_sig = mutate(manifest, sig)
    assert _loads(h.SignedToolLoader, pub, bad_manifest, bad_sig) is False, name


# === our own / batch 2 (original) ===
# Constantin (surreal/sw): the same manifest in different handwriting -- re-serialised with
# sorted keys, indentation, tight separators, a trailing newline -- means the same, but the
# signature is over BYTES, not meaning, so every re-dressing is refused.
def test_oracle_reserialized_manifest_rejected() -> None:
    import json
    pub, manifest, sig = h._signed_manifest()
    loader = h.SignedToolLoader(pub)
    claims = json.loads(manifest)
    variants = [json.dumps(claims, sort_keys=True).encode(),
                json.dumps(claims, indent=2).encode(),
                json.dumps(claims, separators=(",", ":")).encode(),
                manifest + b"\n"]
    variants = [v for v in variants if v != manifest]
    assert len(variants) >= 3
    for v in variants:
        try:
            loader.load(v, sig)
            rejected = False
        except Exception:
            rejected = True
        assert rejected is True, v


# Knox (absurd/sw): smuggle a new tool in as perfectly valid JSON -- the document still parses,
# but it is a different document, and the signature knows.
def test_oracle_valid_json_insertion_rejected() -> None:
    import json
    pub, manifest, sig = h._signed_manifest()
    tampered = manifest.replace(b"}", b', "shell": "rm -rf /"}')
    assert json.loads(tampered)["shell"] == "rm -rf /"  # still valid JSON
    try:
        h.SignedToolLoader(pub).load(tampered, sig)
        rejected = False
    except Exception:
        rejected = True
    assert rejected is True
