"""Proof: the session-bound HMAC token resists the cross-session replay the static token accepts.
A token minted for the attacker session validates the victim's only under the static scheme."""

from harnesses.lib import csrf_token_test_harness as h


def test_proof_buggy_is_flagged() -> None:
    assert h.accepts_cross_session_token(h.StaticCsrf) is True


def test_proof_oracle_not_flagged() -> None:
    assert h.accepts_cross_session_token(h.SynchronizerCsrf) is False


def test_proof_oracle_happy_path() -> None:
    assert h.legit_token_validates(h.SynchronizerCsrf) is True
