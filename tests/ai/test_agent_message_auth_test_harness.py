"""Oracle + CLI-contract test for agent_message_auth (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_agent_message_auth_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.ai import agent_message_auth_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.roundtrips(h.AuthChannel) is True


# --- scenario coverage: the authenticated channel rejects every tag/body mutation ---
def _receives(make_channel, key, body, tag):
    try:
        make_channel(key).receive(body, tag)
        return True
    except Exception:
        return False


def test_oracle_rejects_forged_body_and_tags() -> None:
    key = b"shared-secret-key"
    _, tag = h.AuthChannel(key).send(b"pay alice 100")
    cases = {
        "forged_body": (b"pay mallory 100", tag),
        "truncated_tag": (b"pay alice 100", tag[:-1]),
        "zeroed_tag": (b"pay alice 100", b"\x00" * len(tag)),
    }
    for name, (body, t) in cases.items():
        assert _receives(h.AuthChannel, key, body, t) is False, name


# --- second pass: a message authed under another key is rejected ---
def test_oracle_rejects_message_under_wrong_key() -> None:
    body = b"pay alice 100"
    _, tag = h.AuthChannel(b"key-A").send(body)
    assert _receives(h.AuthChannel, b"key-B", body, tag) is False


import pytest  # noqa: E402


def _flip(b, i):
    return b[:i] + bytes([b[i] ^ 1]) + b[i + 1:]


# --- pass 4 (corpus): every forged-body / tag mutation is rejected ---
_MSG_MUTATIONS = [
    ("forged_body", lambda body, tag: (b"pay mallory 9999", tag)),
    ("flip_body", lambda body, tag: (_flip(body, 0), tag)),
    ("flip_tag_start", lambda body, tag: (body, _flip(tag, 0))),
    ("flip_tag_end", lambda body, tag: (body, _flip(tag, len(tag) - 1))),
    ("truncate_tag", lambda body, tag: (body, tag[:-1])),
    ("zero_tag", lambda body, tag: (body, b"\x00" * len(tag))),
    ("empty_tag", lambda body, tag: (body, b"")),
]


@pytest.mark.parametrize("name,mutate", _MSG_MUTATIONS)
def test_oracle_rejects_message_mutation(name, mutate) -> None:
    key = b"shared-secret-key"
    body0 = b"pay alice 100"
    _, tag = h.AuthChannel(key).send(body0)
    bad_body, bad_tag = mutate(body0, tag)
    assert _receives(h.AuthChannel, key, bad_body, bad_tag) is False, name


# === our own / batch 2 (original) ===
# Adeyemi (whimsical/psych): integrity is not freshness -- this channel authenticates WHAT was
# said, not WHEN; the same signed note reads true twice (replay is agent_join_replay's job).
def test_oracle_integrity_is_not_freshness_honest_gap() -> None:
    import os
    ch = h.AuthChannel(os.urandom(32))
    body, tag = ch.send(b"agentA: status ok")
    assert ch.receive(body, tag) == body
    assert ch.receive(body, tag) == body  # stateless: no nonce, so it verifies again


# Toll (surreal/psych): a tag one byte too short, or one byte too long, is a stranger wearing
# the right coat -- the HMAC is not fooled.
@pytest.mark.parametrize("warp", ["short", "long"])
def test_oracle_tag_length_perturbation_rejected(warp) -> None:
    import os
    ch = h.AuthChannel(os.urandom(32))
    body, tag = ch.send(b"agentA: status ok")
    bad = tag[:-1] if warp == "short" else tag + b"\x00"
    try:
        ch.receive(body, bad)
        rejected = False
    except Exception:
        rejected = True
    assert rejected is True, warp


# Knox (absurd/sw): the empty dispatch authenticates itself, but its tag is non-transferable --
# it does not vouch for a different body.
def test_oracle_empty_dispatch_tag_not_transferable() -> None:
    import os
    ch = h.AuthChannel(os.urandom(32))
    body, tag = ch.send(b"")
    assert ch.receive(b"", tag) == b""
    try:
        ch.receive(b"x", tag)
        transferable = True
    except Exception:
        transferable = False
    assert transferable is False
