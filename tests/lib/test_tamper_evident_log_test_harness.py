"""Oracle + CLI-contract test for tamper_evident_log (pairs with its proof file).

Two-file convention: this asserts the secure path and the runnable CLI contract;
test_tamper_evident_log_proof.py asserts the planted bug is caught (the teeth).
"""

from harnesses.lib import tamper_evident_log_test_harness as h


def test_self_test_green() -> None:
    assert h.run_self_test() == 0


def test_cli_no_args_returns_2() -> None:
    assert h.main([]) == 2


def test_cli_self_test_returns_0() -> None:
    assert h.main(["--self-test"]) == 0


def test_oracle_happy_path() -> None:
    assert h.intact_log_verifies(h.HashChainedLog) is True


# --- scenario coverage: A09 tampering modes the hash-chain must detect ---
def _chain(entries):
    log = h.HashChainedLog()
    for entry in entries:
        log.append(entry)
    return log


def test_oracle_detects_edit() -> None:
    log = _chain(["a", "b", "c"])
    log.tamper(1, "X")
    assert log.verify() is False


def test_oracle_detects_middle_delete() -> None:
    log = _chain(["a", "b", "c"])
    del log._entries[1]
    assert log.verify() is False


def test_oracle_detects_reorder() -> None:
    log = _chain(["a", "b", "c"])
    log._entries[1], log._entries[2] = log._entries[2], log._entries[1]
    assert log.verify() is False


# --- second pass: first-entry tamper + empty/single-entry robustness ---
def test_oracle_detects_first_entry_edit() -> None:
    log = _chain(["a", "b", "c"])
    log.tamper(0, "X")
    assert log.verify() is False


def test_oracle_verifies_empty_and_single_entry_logs() -> None:
    assert h.HashChainedLog().verify() is True
    assert _chain(["only-entry"]).verify() is True


# --- third pass: verify() is deterministic / idempotent ---
def test_oracle_verify_is_idempotent() -> None:
    log = _chain(["a", "b", "c"])
    assert log.verify() is True
    assert log.verify() is True
    log.tamper(1, "X")
    assert log.verify() is False
    assert log.verify() is False


import pytest  # noqa: E402


@pytest.mark.parametrize("idx", [0, 1, 2])
def test_oracle_detects_edit_at_index(idx) -> None:
    log = _chain(["a", "b", "c", "d"])
    log.tamper(idx, "X")
    assert log.verify() is False, idx


@pytest.mark.parametrize("idx", [0, 1, 2])
def test_oracle_detects_nonlast_delete(idx) -> None:
    log = _chain(["a", "b", "c", "d"])
    del log._entries[idx]
    assert log.verify() is False, idx


# === our own / batch 1 (original) ===
import hashlib  # noqa: E402


# Brandt (absurd/psych): rewriting an entry to its OWN value is not tampering -- no false alarm.
def test_oracle_idempotent_rewrite_not_false_tamper() -> None:
    log = _chain(["login", "grant admin", "logout"])
    log.tamper(1, "grant admin")               # same value back in
    assert log.verify() is True


# Knox (absurd/sw): prev_mac without the secret cannot extend the chain (no length-extension).
def test_oracle_no_secret_append_breaks_chain() -> None:
    log = _chain(["a", "b", "c"])
    prev = log._entries[-1]["mac"]
    forged = {"data": "grant admin", "mac": hashlib.sha256(prev + b"grant admin").digest()}
    log._entries.append(forged)                # SHA256 != HMAC -> caught
    assert log.verify() is False


# Adeyemi (whimsical/psych): a tail EDIT is caught; a tail DROP (truncation) is the documented gap.
def test_oracle_last_entry_edit_detected_but_truncation_not() -> None:
    edited = _chain(["a", "b", "c"])
    edited.tamper(2, "z")
    assert edited.verify() is False            # editing the last entry IS detected
    truncated = _chain(["a", "b", "c"])
    truncated._entries.pop()                    # dropping the last entry is NOT (known limit)
    assert truncated.verify() is True


def test_oracle_cross_instance_macs_differ() -> None:
    log_a = h.HashChainedLog()
    log_a.append("x")
    log_b = h.HashChainedLog()
    log_b.append("x")
    assert log_a._entries[0]["mac"] != log_b._entries[0]["mac"]
