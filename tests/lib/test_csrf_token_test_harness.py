"""Oracle + CLI-contract test for csrf_token (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_csrf_token_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import csrf_token_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.legit_token_validates(h.SynchronizerCsrf) is True


import pytest  # noqa: E402


@pytest.mark.parametrize("token", ["", "x" * 10, "deadbeef", "zz", "00" * 32, "nothex!!"])
def test_oracle_rejects_garbage_token(token) -> None:
    assert h.SynchronizerCsrf().validate("victim", token) is False, token


_BENIGN_SESSIONS = ["u1", "alice", "bob-123", "", "ünïcode", "x" * 64]


@pytest.mark.parametrize("session", _BENIGN_SESSIONS)
def test_oracle_accepts_same_session_token(session) -> None:
    csrf = h.SynchronizerCsrf()
    assert csrf.validate(session, csrf.issue(session)) is True, session


# === our own / batch 1 (original) ===
_CS_C = h.SynchronizerCsrf()
_CS_TOK = _CS_C.issue("session-victim")
_CS_SPACED = " ".join(_CS_TOK[i:i + 2] for i in range(0, len(_CS_TOK), 2))
_CS_NEAR = ["session-victim ", "SESSION-VICTIM", "session-victi", " session-victim"]


# Constantin (surreal/sw): metamorphic -- case/whitespace re-rendering of the tag still validates.
@pytest.mark.parametrize("rendering", [_CS_TOK.upper(), _CS_SPACED])
def test_oracle_mr_hex_encoding_invariant(rendering) -> None:
    assert _CS_C.validate("session-victim", rendering) is True


def _cs_flip(tok, i):
    b = bytearray.fromhex(tok)
    b[i] ^= 0x02
    return b.hex()


@pytest.mark.parametrize("pos", [0, 9, 31])
def test_oracle_mr_token_bit_flip_rejected(pos) -> None:
    assert _CS_C.validate("session-victim", _cs_flip(_CS_TOK, pos)) is False


# Toll (surreal/psych): the eye blurs them, the bytes do not -- near-miss sessions get nothing.
@pytest.mark.parametrize("near", _CS_NEAR)
def test_oracle_near_miss_sessions_rejected(near) -> None:
    assert _CS_C.validate(near, _CS_TOK) is False


def test_oracle_cross_instance_token_rejected() -> None:
    assert h.SynchronizerCsrf().validate("session-victim", _CS_TOK) is False


# Pip (whimsical/sw): no two rooms share a key -- 200 sessions, 200 distinct tokens.
def test_oracle_tokens_collision_free() -> None:
    csrf = h.SynchronizerCsrf()
    tokens = {csrf.issue("s%d" % i) for i in range(200)}
    assert len(tokens) == 200
