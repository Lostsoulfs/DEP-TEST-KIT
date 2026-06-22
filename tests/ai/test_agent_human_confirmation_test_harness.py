"""Oracle + CLI-contract test for agent_human_confirmation (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_agent_human_confirmation_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.ai import agent_human_confirmation_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.executes_with_valid_stepup(h.StepUpExecutor) is True


# --- scenario coverage: the step-up executor refuses missing/forged consent ---
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey as _Ed  # noqa: E402


def _executes(executor, action, nonce, signature):
    try:
        executor.execute(action, nonce, signature)
        return True
    except Exception:
        return False


def test_oracle_executes_with_valid_stepup() -> None:
    human = _Ed.generate()
    sig = human.sign(b"wire_transfer|n-1")
    assert _executes(h.StepUpExecutor(human.public_key()), "wire_transfer", "n-1", sig) is True


def test_oracle_refuses_missing_or_forged_stepup() -> None:
    human = _Ed.generate()
    valid = human.sign(b"wire_transfer|n-1")
    cases = {
        "no_signature": ("wire_transfer", "n-1", None),
        "random_signature": ("wire_transfer", "n-1", b"\x00" * 64),
        "wrong_action": ("refund_all", "n-1", valid),
        "wrong_nonce": ("wire_transfer", "n-2", valid),
    }
    executor = h.StepUpExecutor(human.public_key())
    for name, (action, nonce, sig) in cases.items():
        assert _executes(executor, action, nonce, sig) is False, name


# --- second pass: wrong-human-key refused; a different valid action runs ---
def test_oracle_rejects_stepup_from_wrong_human_key() -> None:
    real = _Ed.generate()
    attacker = _Ed.generate()
    sig = attacker.sign(b"wire_transfer|n-1")
    assert _executes(h.StepUpExecutor(real.public_key()), "wire_transfer", "n-1", sig) is False


def test_oracle_executes_a_different_valid_action() -> None:
    human = _Ed.generate()
    sig = human.sign(b"delete_export|n-5")
    assert _executes(h.StepUpExecutor(human.public_key()), "delete_export", "n-5", sig) is True


import pytest  # noqa: E402

_STEPUP_BAD_SIGS = [
    ("no_signature", None),
    ("zero_signature", b"\x00" * 64),
    ("short_signature", b"\x00" * 32),
    ("empty_signature", b""),
    ("garbage_signature", b"\xff" * 64),
]


@pytest.mark.parametrize("name,sig", _STEPUP_BAD_SIGS)
def test_oracle_refuses_invalid_stepup_signature(name, sig) -> None:
    executor = h.StepUpExecutor(_Ed.generate().public_key())
    assert _executes(executor, "wire_transfer", "n-1", sig) is False, name


_STEPUP_MISBOUND = [
    ("wrong_action", b"refund_all|n-1", "wire_transfer", "n-1"),
    ("wrong_nonce", b"wire_transfer|n-1", "wire_transfer", "n-2"),
    ("swapped_both", b"refund_all|n-9", "wire_transfer", "n-1"),
]


@pytest.mark.parametrize("name,signed,action,nonce", _STEPUP_MISBOUND)
def test_oracle_refuses_misbound_stepup(name, signed, action, nonce) -> None:
    human = _Ed.generate()
    sig = human.sign(signed)
    executor = h.StepUpExecutor(human.public_key())
    assert _executes(executor, action, nonce, sig) is False, name


# === our own / batch 3 (original; web-checked) ===
# H1 (Knox/absurd/sw -- the Horton principle: "authenticate what is MEANT, not what is SAID").
# The step-up signs a NON-injective "action|nonce" concat, so ("wire_transfer","n-1|sneaky")
# and ("wire_transfer|n-1","sneaky") share the same signed bytes -- one signature authorizes a
# shifted action. Known principle (Horton / canonicalization attacks); no prior writeup found
# applying it to an agentic step-up. Real weakness: bind a CANONICAL encoding, not a raw concat.
def test_oracle_stepup_concat_is_ambiguous_horton() -> None:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    human = Ed25519PrivateKey.generate()
    ex = h.StepUpExecutor(human.public_key())
    approved = human.sign(b"wire_transfer|n-1|sneaky")     # human meant nonce = "n-1|sneaky"
    shifted = ex.execute("wire_transfer|n-1", "sneaky", approved)  # same bytes, different split
    assert shifted == "executed:wire_transfer|n-1"


# H2 (Brandt/absurd/psych + Adeyemi -- honest gap): the executor verifies authenticity but keeps
# no single-use nonce, so a genuine approval REPLAYS. Integrity != freshness; pair with a
# consumed nonce (cf. agent_join_replay) for single-use. No prior art located for replay of an
# agentic human step-up token as of the web check.
def test_oracle_stepup_approval_is_replayable() -> None:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    human = Ed25519PrivateKey.generate()
    ex = h.StepUpExecutor(human.public_key())
    sig = human.sign(b"wire_transfer|n-1")
    assert ex.execute("wire_transfer", "n-1", sig) == "executed:wire_transfer"
    assert ex.execute("wire_transfer", "n-1", sig) == "executed:wire_transfer"  # replay succeeds
