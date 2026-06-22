"""Proof: real HMAC verification exposes the spoofed inter-agent message a mock
can't model. The plain channel accepts a forged body; the authenticated channel rejects it."""

from harnesses.ai import agent_message_auth_test_harness as h


def test_proof_plain_channel_accepts_forgery() -> None:
    assert h.accepts_forged_message(h.PlainChannel) is True


def test_proof_auth_channel_rejects_forgery() -> None:
    assert h.accepts_forged_message(h.AuthChannel) is False


def test_proof_auth_channel_roundtrips() -> None:
    assert h.roundtrips(h.AuthChannel) is True


# --- scenario coverage: the plain channel accepts a forged body / bad tag ---
def test_proof_plain_channel_accepts_forgery_and_bad_tag() -> None:
    key = b"shared-secret-key"
    _, tag = h.AuthChannel(key).send(b"pay alice 100")
    for body, t in ((b"pay mallory 100", tag), (b"pay alice 100", b"\x00" * len(tag))):
        try:
            h.PlainChannel(key).receive(body, t)
            accepted = True
        except Exception:
            accepted = False
        assert accepted is True
