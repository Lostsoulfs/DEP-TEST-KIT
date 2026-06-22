"""Oracle + CLI-contract test for reset_token_design (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_reset_token_design_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import reset_token_design_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.legit_token_verifies(h.SignedTokenDesign) is True


# --- scenario coverage: A06 token-design properties the signed design must hold ---
def _sign_for(design, payload):
    from cryptography.hazmat.primitives import hashes, hmac
    mac = hmac.HMAC(design._secret, hashes.SHA256())
    mac.update(payload.encode())
    return payload + "|" + mac.finalize().hex()


def test_oracle_rejects_expired_token() -> None:
    import time
    design = h.SignedTokenDesign()
    payload = f"victim@example.com|pwreset|{int(time.time()) - 10}|deadbeef"
    assert design.verify("victim@example.com", _sign_for(design, payload)) is False


def test_oracle_is_single_use() -> None:
    design = h.SignedTokenDesign()
    token = design.issue("u@example.com")
    assert design.verify("u@example.com", token) is True
    assert design.verify("u@example.com", token) is False


def test_oracle_binds_user() -> None:
    design = h.SignedTokenDesign()
    token = design.issue("alice@example.com")
    assert design.verify("bob@example.com", token) is False


def test_oracle_binds_purpose() -> None:
    import time
    design = h.SignedTokenDesign()
    payload = f"u@example.com|login|{int(time.time()) + 1200}|deadbeef"
    assert design.verify("u@example.com", _sign_for(design, payload)) is False


def test_oracle_rejects_tampered_token() -> None:
    design = h.SignedTokenDesign()
    token = design.issue("u@example.com")
    flipped = token[:-1] + ("0" if token[-1] != "0" else "1")
    assert design.verify("u@example.com", flipped) is False


# --- second pass: expiry boundary + per-user independence ---
def test_oracle_accepts_token_just_before_expiry() -> None:
    import time
    design = h.SignedTokenDesign()
    payload = f"u@example.com|pwreset|{int(time.time()) + 5}|boundary"
    assert design.verify("u@example.com", _sign_for(design, payload)) is True


def test_oracle_issues_independent_tokens_per_user() -> None:
    design = h.SignedTokenDesign()
    alice = design.issue("alice@example.com")
    bob = design.issue("bob@example.com")
    assert alice != bob
    assert design.verify("alice@example.com", alice) is True
    assert design.verify("bob@example.com", bob) is True


# --- third pass: garbage tokens never verify ---
def test_oracle_never_verifies_garbage_tokens() -> None:
    design = h.SignedTokenDesign()
    for token in ["", "garbage", "a|b|c|d", "a|b", "x" * 200, "|||"]:
        assert design.verify("u@example.com", token) is False, token


import pytest  # noqa: E402


@pytest.mark.parametrize("token", [
    "", "garbage", "a|b", "a|b|c|d", "|||", "x" * 120, "....", "a|b|c|nothex",
])
def test_oracle_rejects_garbage_token_corpus(token) -> None:
    assert h.SignedTokenDesign().verify("u@example.com", token) is False, token


@pytest.mark.parametrize("kind", ["expired", "expired_long", "wrong_purpose", "wrong_user"])
def test_oracle_rejects_misclaim_token(kind) -> None:
    import time
    design = h.SignedTokenDesign()
    now = int(time.time())
    payloads = {
        "expired": f"u@example.com|pwreset|{now - 10}|n1",
        "expired_long": f"u@example.com|pwreset|{now - 86400}|n2",
        "wrong_purpose": f"u@example.com|login|{now + 1200}|n3",
        "wrong_user": f"attacker@example.com|pwreset|{now + 1200}|n4",
    }
    token = _sign_for(design, payloads[kind])
    verify_as = "victim@example.com" if kind == "wrong_user" else "u@example.com"
    assert design.verify(verify_as, token) is False, kind


# === our own / batch 1 (original) ===
# Knox (absurd/sw): feed the payload its own delimiter -- a '|' in the email must fail closed.
def test_oracle_pipe_email_fails_closed() -> None:
    design = h.SignedTokenDesign()
    pipe_email = "a|pwreset|9999999999|x@evil.com"
    token = design.issue(pipe_email)
    assert design.verify(pipe_email, token) is False   # split() over-segments -> rejected


# Brandt (absurd/psych): expiry is signed -- the clock cannot be pushed forward.
def test_oracle_signed_expiry_cannot_be_extended() -> None:
    design = h.SignedTokenDesign()
    good = design.issue("user@example.com")
    payload, tag = good.rsplit("|", 1)
    who, purpose, exp, nonce = payload.split("|")
    bumped = "%s|%s|%d|%s|%s" % (who, purpose, int(exp) + 100000, nonce, tag)
    assert design.verify("user@example.com", bumped) is False


# Adeyemi (whimsical/psych): each issue mints a fresh nonce -- two tokens, two independent lives.
def test_oracle_nonce_granularity_across_reissues() -> None:
    design = h.SignedTokenDesign()
    first = design.issue("u@x.com")
    second = design.issue("u@x.com")
    assert first != second
    assert design.verify("u@x.com", first) is True
    assert design.verify("u@x.com", first) is False   # consumed
    assert design.verify("u@x.com", second) is True    # independent nonce


def test_oracle_cross_instance_token_rejected() -> None:
    good = h.SignedTokenDesign().issue("user@example.com")
    assert h.SignedTokenDesign().verify("user@example.com", good) is False
